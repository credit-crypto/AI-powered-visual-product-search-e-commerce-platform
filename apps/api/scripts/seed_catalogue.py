#!/usr/bin/env python3
"""Seed a small sample catalogue with synthetic product images and embeddings.

Usage (from apps/api, with infra up):

    PYTHONPATH=. python -m scripts.seed_catalogue

By default embeddings are computed inline (same encoder as the worker) so the
demo is searchable immediately. Set SEED_USE_CELERY=1 to enqueue Celery jobs
instead and wait for product_images.status=ready.
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

# Ensure app imports work when invoked as a module
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.repositories import catalogue as catalogue_repo  # noqa: E402
from app.services.encoder import get_encoder  # noqa: E402
from app.services.indexing import index_product_image_sync  # noqa: E402
from app.services.storage import build_product_image_key, get_storage  # noqa: E402

SAMPLES = [
    {
        "name": "Crimson Ceramic Mug",
        "slug": "crimson-ceramic-mug",
        "description": "Matte red mug for morning coffee.",
        "price_cents": 1800,
        "color": (180, 40, 40),
        "shape": "circle",
    },
    {
        "name": "Ocean Blue Tote",
        "slug": "ocean-blue-tote",
        "description": "Canvas tote in deep ocean blue.",
        "price_cents": 3200,
        "color": (30, 90, 180),
        "shape": "rect",
    },
    {
        "name": "Forest Green Sneaker",
        "slug": "forest-green-sneaker",
        "description": "Everyday sneaker with forest green upper.",
        "price_cents": 7900,
        "color": (34, 120, 70),
        "shape": "ellipse",
    },
    {
        "name": "Sunflower Yellow Lamp",
        "slug": "sunflower-yellow-lamp",
        "description": "Desk lamp with a warm yellow shade.",
        "price_cents": 5400,
        "color": (230, 190, 40),
        "shape": "triangle",
    },
    {
        "name": "Slate Grey Backpack",
        "slug": "slate-grey-backpack",
        "description": "Minimal backpack in slate grey.",
        "price_cents": 8900,
        "color": (90, 95, 105),
        "shape": "rect",
    },
    {
        "name": "Blush Pink Scarf",
        "slug": "blush-pink-scarf",
        "description": "Soft scarf in blush pink.",
        "price_cents": 2700,
        "color": (220, 140, 160),
        "shape": "circle",
    },
    {
        "name": "Ivory Linen Shirt",
        "slug": "ivory-linen-shirt",
        "description": "Breathable linen shirt in ivory.",
        "price_cents": 6100,
        "color": (235, 228, 210),
        "shape": "rect",
    },
    {
        "name": "Midnight Black Watch",
        "slug": "midnight-black-watch",
        "description": "Matte black watch with minimal dial.",
        "price_cents": 12900,
        "color": (20, 20, 24),
        "shape": "circle",
    },
]


def _render_sample(color: tuple[int, int, int], shape: str, size: int = 384) -> bytes:
    bg = tuple(min(255, c + 40) for c in color)
    image = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(image)
    margin = size // 6
    box = [margin, margin, size - margin, size - margin]
    if shape == "circle":
        draw.ellipse(box, fill=color)
    elif shape == "ellipse":
        draw.ellipse([margin, margin + 40, size - margin, size - margin - 40], fill=color)
    elif shape == "triangle":
        draw.polygon(
            [
                (size // 2, margin),
                (size - margin, size - margin),
                (margin, size - margin),
            ],
            fill=color,
        )
    else:
        draw.rectangle(box, fill=color)
    # Accent stripe for extra texture
    draw.rectangle([0, size - 28, size, size], fill=(255, 255, 255))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _index_via_celery(product_image_id) -> None:
    from worker.tasks import generate_embedding_for_image

    generate_embedding_for_image.delay(str(product_image_id))
    deadline = time.time() + 60
    while time.time() < deadline:
        row = catalogue_repo.get_product_image(product_image_id)
        if row and row["status"] == "ready":
            return
        if row and row["status"] == "failed":
            raise RuntimeError(f"Indexing failed for {product_image_id}")
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for embedding of {product_image_id}")


def main() -> None:
    settings = get_settings()
    use_celery = os.getenv("SEED_USE_CELERY", "0") == "1"
    print(f"Seeding catalogue (backend={settings.embedding_backend}, celery={use_celery})")

    category_id = catalogue_repo.ensure_category("Sample", "sample")
    encoder = get_encoder()
    print(f"Encoder: {encoder.model_name}")

    created = 0
    for sample in SAMPLES:
        existing = None
        # Skip if slug already exists
        products = catalogue_repo.list_products(limit=100)
        for p in products:
            if p["slug"] == sample["slug"]:
                existing = p
                break
        if existing:
            print(f"  skip existing {sample['slug']}")
            continue

        product = catalogue_repo.create_product(
            name=sample["name"],
            slug=sample["slug"],
            description=sample["description"],
            category_id=category_id,
            price_cents=sample["price_cents"],
            status="active",
        )
        image_bytes = _render_sample(sample["color"], sample["shape"])
        key = build_product_image_key(str(product["id"]), f"{sample['slug']}.jpg")
        url = get_storage().put_bytes(key, image_bytes, "image/jpeg")
        img = catalogue_repo.insert_product_image(
            product_id=product["id"],
            storage_key=key,
            url=url,
            width=384,
            height=384,
            is_primary=True,
        )
        if use_celery:
            _index_via_celery(img["id"])
        else:
            index_product_image_sync(img["id"])
        created += 1
        print(f"  + {sample['slug']} → {url}")

    print(f"Done. Created {created} products. Search via POST /api/v1/search/image")


if __name__ == "__main__":
    main()
