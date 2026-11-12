"""Image embedding encoders.

Backends (set EMBEDDING_BACKEND):
- perceptual (default, offline): CPU-friendly content-aware 768-d vector for local
  demos / CI. Colour histograms + spatial luminance grid — no HuggingFace download.
- siglip2 (online opt-in): real `google/siglip2-base-patch16-224` via transformers +
  torch. Install `requirements-ml.txt`, set EMBEDDING_BACKEND=siglip2 on api+worker,
  then re-seed or reindex. Both backends emit L2-normalized 768-d floats for MongoDB
  cosine search.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.services.preprocess import preprocess_for_encoder

logger = logging.getLogger(__name__)

MODEL_NAME_PERCEPTUAL = "visual-shop/perceptual-v1"
MODEL_NAME_SIGLIP2 = "google/siglip2-base-patch16-224"


class ImageEncoder(ABC):
    """Converts image bytes into a dense embedding vector."""

    model_name: str
    embedding_dim: int = 768

    @abstractmethod
    def encode_image_sync(self, image_bytes: bytes) -> list[float]:
        """Return an L2-normalized embedding (dim must match stored Mongo vectors)."""

    async def encode_image(self, image_bytes: bytes) -> list[float]:
        return self.encode_image_sync(image_bytes)


def _l2_normalize(vec: np.ndarray) -> list[float]:
    norm = float(np.linalg.norm(vec))
    if norm < 1e-12:
        return vec.astype(np.float32).tolist()
    return (vec / norm).astype(np.float32).tolist()


class PerceptualImageEncoder(ImageEncoder):
    """Deterministic perceptual embedding for demos without GPU/model downloads."""

    model_name = MODEL_NAME_PERCEPTUAL

    def encode_image_sync(self, image_bytes: bytes) -> list[float]:
        image = preprocess_for_encoder(image_bytes, size=64)
        arr = np.asarray(image, dtype=np.float32) / 255.0

        # 3×32-bin colour histograms (96 dims)
        hist_parts: list[np.ndarray] = []
        for channel in range(3):
            hist, _ = np.histogram(arr[:, :, channel], bins=32, range=(0.0, 1.0), density=True)
            hist_parts.append(hist.astype(np.float32))

        # 16×16 spatial luminance grid (256 dims)
        gray = arr.mean(axis=2)
        # block-average to 16x16
        h, w = gray.shape
        block_h, block_w = h // 16, w // 16
        grid = gray[: block_h * 16, : block_w * 16].reshape(16, block_h, 16, block_w).mean(axis=(1, 3))
        spatial = grid.reshape(-1).astype(np.float32)

        # Edge energy via simple gradients (16×16 → 256 dims)
        gy, gx = np.gradient(gray)
        edge = np.sqrt(gx * gx + gy * gy)
        edge_grid = edge[: block_h * 16, : block_w * 16].reshape(16, block_h, 16, block_w).mean(axis=(1, 3))
        edges = edge_grid.reshape(-1).astype(np.float32)

        features = np.concatenate([*hist_parts, spatial, edges])  # 96 + 256 + 256 = 608
        # Pad / project into 768 dims with a fixed random orthonormal-ish expansion
        rng = np.random.default_rng(42)
        projection = rng.standard_normal((self.embedding_dim, features.shape[0])).astype(np.float32)
        projected = projection @ features
        return _l2_normalize(projected)


class SigLIP2ImageEncoder(ImageEncoder):
    """SigLIP2 vision tower — load once per process."""

    model_name = MODEL_NAME_SIGLIP2

    def __init__(self) -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModel
        except ImportError as exc:
            raise RuntimeError(
                "SigLIP2 backend requires torch + transformers. "
                "Install apps/api/requirements-ml.txt or set EMBEDDING_BACKEND=perceptual."
            ) from exc

        settings = get_settings()
        self._torch = torch
        model_id = settings.embedding_model_name or MODEL_NAME_SIGLIP2
        logger.info("Loading SigLIP2 model %s", model_id)
        self._processor = AutoImageProcessor.from_pretrained(model_id)
        self._model = AutoModel.from_pretrained(model_id)
        self._model.eval()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

    def encode_image_sync(self, image_bytes: bytes) -> list[float]:
        image = preprocess_for_encoder(image_bytes, size=224)
        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with self._torch.no_grad():
            outputs = self._model.get_image_features(**inputs)
            # Some SigLIP variants expose pooler_output via vision model
            if outputs is None:
                vision = self._model.vision_model(**inputs)
                outputs = vision.pooler_output
            vec = outputs[0].detach().cpu().float().numpy()
        if vec.shape[-1] != self.embedding_dim:
            # Pad or truncate to schema dimension if a variant differs
            fixed = np.zeros(self.embedding_dim, dtype=np.float32)
            n = min(self.embedding_dim, int(vec.shape[-1]))
            fixed[:n] = vec[:n]
            vec = fixed
        return _l2_normalize(np.asarray(vec, dtype=np.float32))


_encoder: ImageEncoder | None = None


def get_encoder() -> ImageEncoder:
    global _encoder
    if _encoder is None:
        settings = get_settings()
        backend = (settings.embedding_backend or "perceptual").strip().lower()
        if backend == "siglip2":
            _encoder = SigLIP2ImageEncoder()
        elif backend in {"perceptual", "stub", "cpu"}:
            _encoder = PerceptualImageEncoder()
        else:
            raise ValueError(f"Unknown EMBEDDING_BACKEND={backend!r}")
        logger.info(
            "Encoder ready: backend=%s model=%s dim=%s",
            backend,
            _encoder.model_name,
            _encoder.embedding_dim,
        )
    return _encoder


def reset_encoder() -> None:
    """Test helper to clear the process-wide encoder singleton."""
    global _encoder
    _encoder = None
