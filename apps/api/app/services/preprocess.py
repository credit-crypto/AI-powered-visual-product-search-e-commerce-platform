"""Image validation and preprocessing shared by indexing and query paths."""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings


class InvalidImageError(ValueError):
    """Raised when uploaded bytes are not a usable image."""


def load_and_validate_image(image_bytes: bytes) -> Image.Image:
    settings = get_settings()
    if not image_bytes:
        raise InvalidImageError("empty image")
    if len(image_bytes) > settings.max_upload_bytes:
        raise InvalidImageError(
            f"image exceeds max size of {settings.max_upload_bytes} bytes"
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except UnidentifiedImageError as exc:
        raise InvalidImageError("file is not a recognized image") from exc
    except OSError as exc:
        raise InvalidImageError("corrupt or unreadable image") from exc

    image = ImageOps.exif_transpose(image)
    width, height = image.size
    if min(width, height) < settings.min_image_side:
        raise InvalidImageError(
            f"image too small ({width}x{height}); min side {settings.min_image_side}"
        )
    if max(width, height) > settings.max_image_side:
        raise InvalidImageError(
            f"image too large ({width}x{height}); max side {settings.max_image_side}"
        )
    return image.convert("RGB")


def preprocess_for_encoder(image_bytes: bytes, size: int = 224) -> Image.Image:
    """EXIF-orient, RGB convert, center-crop / resize to square for the encoder."""
    image = load_and_validate_image(image_bytes)
    return ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS)
