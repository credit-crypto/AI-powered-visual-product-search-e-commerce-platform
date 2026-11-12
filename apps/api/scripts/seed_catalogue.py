#!/usr/bin/env python3
"""Seed a demo catalogue with synthetic product images and embeddings.

Usage (from apps/api, with infra up):

    PYTHONPATH=. python -m scripts.seed_catalogue

By default creates ~100 products. Override with SEED_COUNT=N.
Embeddings are computed inline (same encoder as the worker) so search works
immediately. Set SEED_USE_CELERY=1 to enqueue Celery jobs instead.
"""

from __future__ import annotations

import colorsys
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Ensure app imports work when invoked as a module
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.repositories import catalogue as catalogue_repo  # noqa: E402
from app.services.encoder import get_encoder  # noqa: E402
from app.services.indexing import index_product_image_sync  # noqa: E402
from app.services.storage import build_product_image_key, get_storage  # noqa: E402

CATEGORIES = [
    ("Home", "home"),
    ("Fashion", "fashion"),
    ("Accessories", "accessories"),
    ("Sports", "sports"),
    ("Electronics", "electronics"),
]

PRODUCT_KINDS = [
    ("Mug", "ceramic mug", "circle", 1800, 3200),
    ("Tote", "canvas tote bag", "rect", 2800, 4500),
    ("Sneaker", "everyday sneaker", "ellipse", 6500, 12000),
    ("Lamp", "desk lamp", "triangle", 4200, 8900),
    ("Backpack", "daypack backpack", "rect", 7000, 14000),
    ("Scarf", "soft knit scarf", "circle", 2200, 4800),
    ("Shirt", "linen shirt", "rect", 4500, 8500),
    ("Watch", "minimal watch", "circle", 9000, 18000),
    ("Bottle", "insulated bottle", "ellipse", 2500, 5500),
    ("Cap", "structured cap", "circle", 2000, 4000),
    ("Chair", "accent chair", "rect", 12000, 28000),
    ("Speaker", "bluetooth speaker", "ellipse", 5000, 15000),
    ("Vase", "ceramic vase", "triangle", 3000, 7000),
    ("Jacket", "light jacket", "rect", 8000, 16000),
    ("Mat", "yoga mat", "rect", 3500, 6500),
    ("Bowl", "serving bowl", "circle", 1500, 3500),
    ("Headphones", "over-ear headphones", "ellipse", 7000, 20000),
    ("Pillow", "throw pillow", "rect", 2000, 4500),
    ("Belt", "leather belt", "rect", 2500, 5500),
    ("Plant pot", "terracotta planter", "circle", 1800, 4000),
]

COLOR_NAMES = [
    ("Crimson", 0.00),
    ("Coral", 0.05),
    ("Amber", 0.10),
    ("Sunflower", 0.14),
    ("Lime", 0.22),
    ("Forest", 0.33),
    ("Teal", 0.48),
    ("Ocean", 0.58),
    ("Indigo", 0.68),
    ("Violet", 0.76),
    ("Blush", 0.92),
    ("Slate", None),  # special grey
    ("Ivory", None),  # special cream
    ("Midnight", None),  # special near-black
]


def _named_color(name: str, hue: float | None, index: int) -> tuple[int, int, int]:
    if name == "Slate":
        g = 70 + (index % 5) * 12
        return (g, g + 4, g + 10)
    if name == "Ivory":
        return (235 - (index % 4) * 4, 228 - (index % 4) * 3, 210 - (index % 4) * 2)
    if name == "Midnight":
        v = 12 + (index % 4) * 6
        return (v, v, v + 4)
    assert hue is not None
    sat = 0.55 + (index % 4) * 0.08
    val = 0.55 + (index % 5) * 0.07
    r, g, b = colorsys.hsv_to_rgb(hue, min(sat, 0.9), min(val, 0.95))
    return (int(r * 255), int(g * 255), int(b * 255))


def build_samples(count: int = 100) -> list[dict]:
    samples: list[dict] = []
    i = 0
    while len(samples) < count:
        kind_name, kind_desc, shape, price_lo, price_hi = PRODUCT_KINDS[i % len(PRODUCT_KINDS)]
        color_name, hue = COLOR_NAMES[i % len(COLOR_NAMES)]
        cat_name, cat_slug = CATEGORIES[i % len(CATEGORIES)]
        edition = (i // (len(PRODUCT_KINDS) * len(COLOR_NAMES))) + 1
        slug_base = f"{color_name.lower()}-{kind_name.lower().replace(' ', '-')}"
        slug = slug_base if edition == 1 else f"{slug_base}-{edition}"
        # Keep first 8 classic names close to the original demo set
        name = f"{color_name} {kind_name}"
        if edition > 1:
            name = f"{name} {edition}"
        price = price_lo + ((i * 137) % (price_hi - price_lo + 1))
        color = _named_color(color_name, hue, i)
        samples.append(
            {
                "name": name,
                "slug": slug,
                "description": f"{color_name} {kind_desc} from the {cat_name} collection.",
                "price_cents": price,
                "color": color,
                "shape": shape,
                "category_name": cat_name,
                "category_slug": cat_slug,
                "label": f"{i + 1:03d}",
            }
        )
        i += 1
    return samples


def _render_sample(
    color: tuple[int, int, int],
    shape: str,
    label: str = "",
    size: int = 384,
) -> bytes:
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
    if label:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((12, 12), label, fill=(255, 255, 255), font=font)
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


def _existing_slugs() -> set[str]:
    slugs: set[str] = set()
    offset = 0
    while True:
        batch = catalogue_repo.list_products(limit=100, offset=offset)
        if not batch:
            break
        for p in batch:
            slugs.add(p["slug"])
        offset += len(batch)
        if len(batch) < 100:
            break
    return slugs


def main() -> None:
    settings = get_settings()
    use_celery = os.getenv("SEED_USE_CELERY", "0") == "1"
    count = int(os.getenv("SEED_COUNT", "100"))
    samples = build_samples(count)
    print(
        f"Seeding catalogue (target={count}, backend={settings.embedding_backend}, celery={use_celery})"
    )

    category_ids: dict[str, object] = {}
    for name, slug in CATEGORIES:
        category_ids[slug] = catalogue_repo.ensure_category(name, slug)
    # Keep legacy "sample" category for older seeds
    catalogue_repo.ensure_category("Sample", "sample")

    encoder = get_encoder()
    print(f"Encoder: {encoder.model_name}")

    existing = _existing_slugs()
    created = 0
    skipped = 0
    for sample in samples:
        if sample["slug"] in existing:
            skipped += 1
            continue

        product = catalogue_repo.create_product(
            name=sample["name"],
            slug=sample["slug"],
            description=sample["description"],
            category_id=category_ids[sample["category_slug"]],
            price_cents=sample["price_cents"],
            status="active",
        )
        image_bytes = _render_sample(
            sample["color"], sample["shape"], label=sample.get("label", "")
        )
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
        existing.add(sample["slug"])
        created += 1
        if created == 1 or created % 10 == 0:
            print(f"  + [{created}] {sample['slug']}")

    print(
        f"Done. Created {created} products (skipped {skipped} existing). "
        "Browse /products or POST /api/v1/search/image"
    )


if __name__ == "__main__":
    main()
