"""
Unit tests for app.modules.forensics.face (Task 3.4).

Tests use mock InsightFace objects — they do not require the insightface package
to be installed or the network to be available. The _FaceEmbedder singleton is
patched so tests run in any environment.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from app.core.forensics import EvidenceStatus
from app.modules.forensics.face import (
    _LIVENESS_SUSPECT_BBOX_RATIO,
    _SAME_PERSON_COSINE_THRESHOLD,
    _bbox_area_ratio,
    _cosine_similarity,
    compare_face_embeddings,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_jpeg(width: int = 300, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 100, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _unit_vec(dim: int = 512, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _mock_face(embedding: np.ndarray, bbox: tuple[float, float, float, float]) -> MagicMock:
    face = MagicMock()
    face.embedding = embedding
    face.bbox = bbox
    return face


# ── _cosine_similarity ─────────────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors_return_one(self) -> None:
        v = _unit_vec(seed=1)
        assert _cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors_return_zero(self) -> None:
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector_returns_zero(self) -> None:
        a = np.zeros(512, dtype=np.float32)
        b = _unit_vec(seed=2)
        assert _cosine_similarity(a, b) == 0.0

    def test_similar_but_not_identical(self) -> None:
        a = _unit_vec(seed=3)
        # 0.005 noise per dimension keeps cosine > 0.95 for 512-d unit vectors
        noise = np.random.default_rng(99).standard_normal(512).astype(np.float32) * 0.005
        b = a + noise
        b /= np.linalg.norm(b)
        sim = _cosine_similarity(a, b)
        assert 0.95 < sim < 1.0


# ── _bbox_area_ratio ───────────────────────────────────────────────────────────

class TestBboxAreaRatio:
    def test_full_frame_face(self) -> None:
        face = _mock_face(_unit_vec(), (0.0, 0.0, 300.0, 200.0))
        ratio = _bbox_area_ratio(face, img_h=200, img_w=300)
        assert ratio == pytest.approx(1.0, abs=1e-6)

    def test_small_face(self) -> None:
        # 30×20 face inside 300×200 image → 1%
        face = _mock_face(_unit_vec(), (0.0, 0.0, 30.0, 20.0))
        ratio = _bbox_area_ratio(face, img_h=200, img_w=300)
        assert ratio == pytest.approx(0.01, abs=1e-6)

    def test_zero_image_area_returns_zero(self) -> None:
        face = _mock_face(_unit_vec(), (0.0, 0.0, 10.0, 10.0))
        assert _bbox_area_ratio(face, img_h=0, img_w=0) == 0.0


# ── compare_face_embeddings ────────────────────────────────────────────────────

class TestCompareFaceEmbeddings:
    """Patch _FaceEmbedder to avoid insightface install requirement in unit tests."""

    def _make_embedder_mock(
        self,
        doc_faces: list,
        selfie_faces: list,
    ) -> MagicMock:
        embedder = MagicMock()
        embedder.available = True
        embedder._init_error = None
        # get_faces returns doc faces first call, selfie faces second call
        embedder.get_faces.side_effect = [doc_faces, selfie_faces]
        return embedder

    def test_same_person_returns_present(self) -> None:
        emb = _unit_vec(seed=10)
        doc_face = _mock_face(emb.copy(), (10.0, 10.0, 110.0, 110.0))
        # selfie: same embedding + tiny noise → cosine ≈ 0.999 ≥ 0.40
        noise = np.zeros(512, dtype=np.float32)
        selfie_face = _mock_face(emb.copy() + noise, (5.0, 5.0, 100.0, 150.0))

        embedder = self._make_embedder_mock([doc_face], [selfie_face])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.PRESENT
        assert result.score is not None and result.score >= _SAME_PERSON_COSINE_THRESHOLD
        assert result.details["faces_match"] is True
        assert result.details["embedding_model"] == "buffalo_sc"
        assert result.details["embedding_dim"] == 512

    def test_different_persons_returns_anomalous(self) -> None:
        doc_emb = _unit_vec(seed=20)
        # orthogonal → cosine = 0.0 < 0.40
        selfie_emb = _unit_vec(seed=21)
        # Make them orthogonal by subtracting projection
        selfie_emb -= selfie_emb.dot(doc_emb) * doc_emb
        selfie_emb /= np.linalg.norm(selfie_emb)

        doc_face = _mock_face(doc_emb, (10.0, 10.0, 110.0, 110.0))
        selfie_face = _mock_face(selfie_emb, (5.0, 5.0, 100.0, 150.0))

        embedder = self._make_embedder_mock([doc_face], [selfie_face])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.ANOMALOUS
        assert result.score is not None and result.score < _SAME_PERSON_COSINE_THRESHOLD
        assert result.details["faces_match"] is False

    def test_no_doc_face_returns_unavailable(self) -> None:
        embedder = self._make_embedder_mock([], [])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.UNAVAILABLE
        assert "No face detected in document image" in result.details["reason"]

    def test_no_selfie_face_returns_unavailable(self) -> None:
        doc_face = _mock_face(_unit_vec(seed=30), (10.0, 10.0, 110.0, 110.0))
        embedder = self._make_embedder_mock([doc_face], [])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.UNAVAILABLE
        assert "No face detected in selfie" in result.details["reason"]

    def test_insightface_not_installed_returns_unavailable(self) -> None:
        embedder = MagicMock()
        embedder.available = False
        embedder._init_error = "insightface not installed"
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.UNAVAILABLE
        assert "insightface not installed" in result.details["reason"]

    def test_zero_vector_embedding_returns_unavailable(self) -> None:
        zero_emb = np.zeros(512, dtype=np.float32)
        doc_face = _mock_face(zero_emb, (10.0, 10.0, 110.0, 110.0))
        # embedder.get_faces is called once for doc (returns zero vector face),
        # should return UNAVAILABLE before reaching selfie
        embedder = MagicMock()
        embedder.available = True
        embedder._init_error = None
        embedder.get_faces.return_value = [doc_face]
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.UNAVAILABLE
        assert "zero-vector" in result.details["reason"].lower()

    def test_liveness_suspect_flagged_when_face_fills_frame(self) -> None:
        emb = _unit_vec(seed=40)
        doc_face = _mock_face(emb.copy(), (10.0, 10.0, 110.0, 110.0))
        # selfie: face covers 95% of 300×200 frame → bbox_ratio > 0.85
        large_selfie_face = _mock_face(emb.copy(), (0.0, 0.0, 298.0, 199.0))

        embedder = self._make_embedder_mock([doc_face], [large_selfie_face])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(300, 200), _make_jpeg(300, 200))

        assert result.details["liveness_suspect"] is True
        assert result.details["selfie_face_bbox_ratio"] > _LIVENESS_SUSPECT_BBOX_RATIO

    def test_liveness_not_suspect_when_face_is_normal_size(self) -> None:
        emb = _unit_vec(seed=50)
        doc_face = _mock_face(emb.copy(), (10.0, 10.0, 110.0, 110.0))
        # selfie: face covers ~11% → 100×80 in 300×200
        normal_selfie_face = _mock_face(emb.copy(), (100.0, 60.0, 200.0, 140.0))

        embedder = self._make_embedder_mock([doc_face], [normal_selfie_face])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(300, 200), _make_jpeg(300, 200))

        assert result.details["liveness_suspect"] is False

    def test_cosine_threshold_boundary_exact_match(self) -> None:
        """Exactly at threshold (0.40) → PRESENT."""
        a = np.array([1.0] + [0.0] * 511, dtype=np.float32)
        # Create b with cosine = exactly 0.40 relative to a
        # b = 0.40*a + sqrt(1-0.40²)*orthogonal
        orth = np.array([0.0, 1.0] + [0.0] * 510, dtype=np.float32)
        b = 0.40 * a + np.sqrt(1 - 0.40**2) * orth
        b /= np.linalg.norm(b)

        doc_face = _mock_face(a.copy(), (10.0, 10.0, 110.0, 110.0))
        selfie_face = _mock_face(b.copy(), (5.0, 5.0, 80.0, 100.0))

        embedder = self._make_embedder_mock([doc_face], [selfie_face])
        with patch("app.modules.forensics.face._FaceEmbedder", return_value=embedder):
            result = compare_face_embeddings(_make_jpeg(), _make_jpeg())

        assert result.status == EvidenceStatus.PRESENT
        assert result.score is not None and result.score >= _SAME_PERSON_COSINE_THRESHOLD
