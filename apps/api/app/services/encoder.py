"""Image embedding encoder interface.

Next milestone: load SigLIP2 (`google/siglip2-base-patch16-224`) once per
process and encode images to VECTOR(768) floats.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ImageEncoder(ABC):
    """Converts image bytes into a dense embedding vector."""

    @abstractmethod
    async def encode_image(self, image_bytes: bytes) -> list[float]:
        """Return an L2-ready embedding (dimension must match pgvector schema)."""


class StubImageEncoder(ImageEncoder):
    """Placeholder encoder used until SigLIP2 inference is wired."""

    embedding_dim: int = 768

    async def encode_image(self, image_bytes: bytes) -> list[float]:
        # TODO: Preprocess (EXIF orient, resize/crop) then run SigLIP2.
        if not image_bytes:
            raise ValueError("empty image bytes")
        # Deterministic zero vector keeps the contract usable in stubs.
        return [0.0] * self.embedding_dim


_encoder: ImageEncoder | None = None


def get_encoder() -> ImageEncoder:
    global _encoder
    if _encoder is None:
        _encoder = StubImageEncoder()
    return _encoder
