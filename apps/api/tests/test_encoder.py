"""Unit tests for the CPU perceptual encoder (no DB / GPU required)."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw

from app.services.encoder import PerceptualImageEncoder, reset_encoder


def _jpeg(color: tuple[int, int, int], shape: str = "circle") -> bytes:
    image = Image.new("RGB", (256, 256), (240, 240, 240))
    draw = ImageDraw.Draw(image)
    box = [40, 40, 216, 216]
    if shape == "circle":
        draw.ellipse(box, fill=color)
    else:
        draw.rectangle(box, fill=color)
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def test_perceptual_dim_and_norm() -> None:
    reset_encoder()
    encoder = PerceptualImageEncoder()
    vec = encoder.encode_image_sync(_jpeg((200, 30, 30)))
    assert len(vec) == 768
    norm = float(np.linalg.norm(vec))
    assert 0.99 < norm < 1.01


def test_similar_colours_rank_higher() -> None:
    encoder = PerceptualImageEncoder()
    red_a = np.asarray(encoder.encode_image_sync(_jpeg((200, 30, 30))), dtype=np.float32)
    red_b = np.asarray(encoder.encode_image_sync(_jpeg((190, 40, 35))), dtype=np.float32)
    blue = np.asarray(encoder.encode_image_sync(_jpeg((30, 60, 200))), dtype=np.float32)

    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))

    assert cosine(red_a, red_b) > cosine(red_a, blue)
