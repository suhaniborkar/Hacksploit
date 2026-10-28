"""
Real face embedding adapter — ArcFace via InsightFace buffalo_sc ONNX model.

Replaces the broken 64×64 grayscale pixel cosine similarity path in image.py.
All public surfaces return TamperingSignal so they conform to the existing
forensic adapter contract (ARCHITECTURE.md §2, ForensicExtractor protocol).

Design decisions:
- Lazy singleton: FaceEmbedder is instantiated on first call, not at import time.
  InsightFace model download (~150 MB) must not block the ingestion path.
- Graceful degradation: any failure (import error, no face detected, zero-vector)
  returns EvidenceStatus.UNAVAILABLE, never crashes the forensics pipeline.
- Passive liveness proxy: if the detected face bounding box covers > 85% of the
  image area, we flag LIVENESS_SUSPECT. This catches printed-photo attacks where
  the fraudster holds a photo up to the webcam. It is not a replacement for active
  liveness challenge-response.
- Cosine threshold ≥ 0.40 for same-person match. InsightFace ArcFace embeddings
  are calibrated such that genuine pairs score > 0.40 and impostor pairs score < 0.40
  on LFW/IJB-C benchmarks. This is not the same as raw pixel cosine.

Run location: async slow-plane worker only. Never call from the synchronous ingestion path.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np

from app.core.forensics import EvidenceStatus, TamperingSignal

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# ArcFace cosine threshold: genuine pairs typically score ≥ 0.40 on buffalo_sc.
_SAME_PERSON_COSINE_THRESHOLD: float = 0.40

# Liveness proxy: face bounding box area as fraction of total image area.
# Printed-photo attacks fill the frame. Real selfies have face ≤ 60% typically.
_LIVENESS_SUSPECT_BBOX_RATIO: float = 0.85

# buffalo_sc is the lightweight (50 MB ONNX) model — CPU feasible.
# buffalo_l is more accurate but larger. We use sc for demo/CPU deployments.
_MODEL_PACK: str = "buffalo_sc"


# ── Singleton loader ───────────────────────────────────────────────────────────

class _FaceEmbedder:
    """
    Lazy-loaded InsightFace ArcFace embedding model.
    Thread-safe singleton so the model is downloaded and initialized once only.
    """

    _instance: "_FaceEmbedder | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "_FaceEmbedder":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._app = None  # type: ignore[attr-defined]
                obj._available = False  # type: ignore[attr-defined]
                obj._init_error: str | None = None  # type: ignore[attr-defined]
                try:
                    from insightface.app import FaceAnalysis
                    app = FaceAnalysis(
                        name=_MODEL_PACK,
                        providers=["CPUExecutionProvider"],
                    )
                    # det_size controls the detection input resolution.
                    # 640x640 provides robust detection for small/tilted ID document photos.
                    app.prepare(ctx_id=-1, det_size=(640, 640))
                    obj._app = app
                    obj._available = True
                    logger.info("InsightFace %s loaded successfully.", _MODEL_PACK)
                except ImportError:
                    obj._init_error = "insightface not installed"
                    logger.warning(
                        "insightface not installed — face embedding UNAVAILABLE. "
                        "Install with: pip install insightface"
                    )
                except Exception as exc:
                    obj._init_error = str(exc)
                    logger.exception("InsightFace init failed: %s", exc)
                cls._instance = obj
            return cls._instance  # type: ignore[return-value]

    @property
    def available(self) -> bool:
        return self._available

    def get_faces(self, img_rgb: "np.ndarray") -> list:
        """Returns InsightFace face objects detected in the given RGB array."""
        if not self._available:
            return []
        return self._app.get(img_rgb)  # type: ignore[attr-defined]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_rgb(image_bytes: bytes) -> "np.ndarray | None":
    """Decodes image bytes to an RGB numpy array suitable for InsightFace."""
    try:
        import cv2
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        # Fallback via Pillow if OpenCV decode fails.
        try:
            import io as _io
            from PIL import Image
            img = Image.open(_io.BytesIO(image_bytes)).convert("RGB")
            return np.array(img, dtype=np.uint8)
        except Exception:
            return None


def _cosine_similarity(a: "np.ndarray", b: "np.ndarray") -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _bbox_area_ratio(face, img_h: int, img_w: int) -> float:
    """Returns the fraction of image area covered by the face bounding box."""
    bbox = face.bbox  # [x1, y1, x2, y2]
    fw = max(0.0, float(bbox[2] - bbox[0]))
    fh = max(0.0, float(bbox[3] - bbox[1]))
    img_area = img_h * img_w
    if img_area == 0:
        return 0.0
    return (fw * fh) / img_area


# ── Public API ─────────────────────────────────────────────────────────────────

def compute_face_embedding(image_bytes: bytes) -> "np.ndarray | None":
    """
    Detects the largest face in image_bytes and returns its ArcFace 512-d embedding.
    Returns None if no face is detected or if insightface is unavailable.
    """
    embedder = _FaceEmbedder()
    if not embedder.available:
        return None

    img_rgb = _load_rgb(image_bytes)
    if img_rgb is None:
        return None

    faces = embedder.get_faces(img_rgb)
    if not faces:
        return None

    # Use the largest detected face (highest bounding-box area).
    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    emb = largest.embedding
    if emb is None or np.linalg.norm(emb) == 0.0:
        return None
    return emb.astype(np.float32)


def compare_face_embeddings(
    doc_bytes: bytes,
    selfie_bytes: bytes,
) -> TamperingSignal:
    """
    Computes ArcFace cosine similarity between the face in a document image and
    a live selfie. Returns a TamperingSignal:
      - PRESENT   → cosine ≥ 0.40 (same person, match)
      - ANOMALOUS → cosine < 0.40 (different person, mismatch)
      - UNAVAILABLE → no face detected or insightface not installed

    Also checks the selfie for the passive liveness proxy: if the face bounding
    box covers > 85% of the selfie frame, adds liveness_suspect=True to details.
    """
    embedder = _FaceEmbedder()
    if not embedder.available:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": embedder._init_error or "insightface not installed"},
        )

    # Document face
    doc_rgb = _load_rgb(doc_bytes)
    if doc_rgb is None:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "Could not decode document image."},
        )

    doc_faces = embedder.get_faces(doc_rgb)
    if not doc_faces:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "No face detected in document image."},
        )

    doc_face = max(doc_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    doc_emb = doc_face.embedding
    if doc_emb is None or np.linalg.norm(doc_emb) == 0.0:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "Document face embedding is zero-vector."},
        )

    # Selfie face
    selfie_rgb = _load_rgb(selfie_bytes)
    if selfie_rgb is None:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "Could not decode selfie image."},
        )

    selfie_faces = embedder.get_faces(selfie_rgb)
    if not selfie_faces:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "No face detected in selfie image."},
        )

    selfie_face = max(selfie_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    selfie_emb = selfie_face.embedding
    if selfie_emb is None or np.linalg.norm(selfie_emb) == 0.0:
        return TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "Selfie face embedding is zero-vector."},
        )

    # Cosine similarity
    cosine = _cosine_similarity(doc_emb.astype(np.float32), selfie_emb.astype(np.float32))
    is_match = cosine >= _SAME_PERSON_COSINE_THRESHOLD

    # Passive liveness proxy on the selfie
    img_h, img_w = selfie_rgb.shape[:2]
    bbox_ratio = _bbox_area_ratio(selfie_face, img_h, img_w)
    liveness_suspect = bbox_ratio > _LIVENESS_SUSPECT_BBOX_RATIO

    status = EvidenceStatus.PRESENT if is_match else EvidenceStatus.ANOMALOUS

    return TamperingSignal(
        signal_name="face_consistency",
        status=status,
        score=round(cosine, 4),
        details={
            "cosine_similarity": round(cosine, 4),
            "threshold": _SAME_PERSON_COSINE_THRESHOLD,
            "faces_match": is_match,
            "embedding_model": _MODEL_PACK,
            "embedding_dim": 512,
            "liveness_suspect": liveness_suspect,
            "selfie_face_bbox_ratio": round(bbox_ratio, 3),
        },
    )


def extract_face_crop(
    image_bytes: bytes,
    margin_ratio: float = 0.20,
) -> tuple[bytes, list[float]] | None:
    """
    Detects the largest face in image_bytes, crops it with an optional margin,
    and returns (cropped_jpeg_bytes, [x1, y1, x2, y2]).
    Returns None if no face is detected or insightface is unavailable.
    """
    embedder = _FaceEmbedder()
    if not embedder.available:
        return None

    img_rgb = _load_rgb(image_bytes)
    if img_rgb is None:
        return None

    faces = embedder.get_faces(img_rgb)
    if not faces:
        return None

    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    bbox = [float(v) for v in largest.bbox]
    x1, y1, x2, y2 = bbox

    # Add margin
    h, w = img_rgb.shape[:2]
    bw = x2 - x1
    bh = y2 - y1
    mx = bw * margin_ratio
    my = bh * margin_ratio

    crop_x1 = max(0, int(x1 - mx))
    crop_y1 = max(0, int(y1 - my))
    crop_x2 = min(w, int(x2 + mx))
    crop_y2 = min(h, int(y2 + my))

    crop_rgb = img_rgb[crop_y1:crop_y2, crop_x1:crop_x2]
    if crop_rgb.size == 0:
        return None

    try:
        import io as _io
        from PIL import Image as _Image
        pil_crop = _Image.fromarray(crop_rgb)
        buf = _io.BytesIO()
        pil_crop.save(buf, format="JPEG", quality=90)
        return buf.getvalue(), bbox
    except Exception as exc:
        logger.warning("Failed to encode cropped face to JPEG: %s", exc)
        return None


def extract_face_crop_data_url(
    image_bytes: bytes,
    margin_ratio: float = 0.20,
) -> str | None:
    """Convenience helper returning the cropped face as a base64 DataURL."""
    import base64 as _base64
    res = extract_face_crop(image_bytes, margin_ratio=margin_ratio)
    if not res:
        return None
    crop_bytes, _ = res
    b64 = _base64.b64encode(crop_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"

