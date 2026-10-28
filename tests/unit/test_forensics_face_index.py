"""
Unit tests for app.modules.forensics.face_index (Task 3.5).

Uses ChromaDB EphemeralClient (in-memory) for test isolation.
Requires no disk writes, external databases, or network calls.
"""

from __future__ import annotations

import numpy as np
import pytest
import chromadb

from app.core.forensics import FaceMatch
from app.modules.forensics.face_index import (
    FaceDeduplicationIndex,
    create_face_reuse_edges,
    DEFAULT_DISTANCE_THRESHOLD,
)
from app.modules.graph.models import EdgeType, NodeType


def _unit_vec(seed: int, dim: int = 512) -> np.ndarray:
    """Deterministic random unit vector in float32."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def in_memory_index() -> FaceDeduplicationIndex:
    """Provides an isolated in-memory FaceDeduplicationIndex."""
    import uuid
    client = chromadb.EphemeralClient()
    col_name = f"test_{uuid.uuid4().hex}"
    idx = FaceDeduplicationIndex(client=client, collection_name=col_name)
    yield idx
    idx.reset()


class TestFaceDeduplicationIndex:
    def test_empty_index_query_returns_empty(self, in_memory_index: FaceDeduplicationIndex) -> None:
        assert in_memory_index.count() == 0
        emb = _unit_vec(1)
        matches = in_memory_index.find_matching_faces(emb)
        assert matches == []

    def test_upsert_and_exact_match(self, in_memory_index: FaceDeduplicationIndex) -> None:
        emb = _unit_vec(42)
        ok = in_memory_index.upsert_face_embedding(
            applicant_id="app_001",
            embedding=emb,
            metadata={"doc_type": "aadhaar"},
        )
        assert ok is True
        assert in_memory_index.count() == 1

        matches = in_memory_index.find_matching_faces(emb, top_k=5)
        assert len(matches) == 1
        m = matches[0]
        assert m.applicant_id == "app_001"
        assert m.distance < 1e-4  # practically 0
        assert m.similarity > 0.999
        assert m.metadata.get("doc_type") == "aadhaar"

    def test_similar_face_matches_within_threshold(self, in_memory_index: FaceDeduplicationIndex) -> None:
        base = _unit_vec(100)
        # Small perturbation (same person across submissions)
        noise = np.random.default_rng(7).standard_normal(512).astype(np.float32) * 0.005
        variant = base + noise
        variant /= np.linalg.norm(variant)

        in_memory_index.upsert_face_embedding("applicant_alpha", base)
        matches = in_memory_index.find_matching_faces(variant, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)

        assert len(matches) == 1
        assert matches[0].applicant_id == "applicant_alpha"
        assert matches[0].distance < DEFAULT_DISTANCE_THRESHOLD
        assert matches[0].similarity > 0.65

    def test_distinct_face_rejected_by_threshold(self, in_memory_index: FaceDeduplicationIndex) -> None:
        emb_a = _unit_vec(101)
        emb_b = _unit_vec(102)  # Independent random 512-d vector is near orthogonal (dist ~ 1.0)

        in_memory_index.upsert_face_embedding("applicant_a", emb_a)
        matches = in_memory_index.find_matching_faces(emb_b, distance_threshold=DEFAULT_DISTANCE_THRESHOLD)

        assert len(matches) == 0

    def test_nearest_neighbor_ordering(self, in_memory_index: FaceDeduplicationIndex) -> None:
        base = _unit_vec(200)

        # 3 variations with increasing noise
        noise1 = np.random.default_rng(1).standard_normal(512).astype(np.float32) * 0.001
        v1 = (base + noise1) / np.linalg.norm(base + noise1)

        noise2 = np.random.default_rng(2).standard_normal(512).astype(np.float32) * 0.005
        v2 = (base + noise2) / np.linalg.norm(base + noise2)

        noise3 = np.random.default_rng(3).standard_normal(512).astype(np.float32) * 0.015
        v3 = (base + noise3) / np.linalg.norm(base + noise3)

        in_memory_index.upsert_face_embedding("app_v3", v3)
        in_memory_index.upsert_face_embedding("app_v1", v1)
        in_memory_index.upsert_face_embedding("app_v2", v2)

        matches = in_memory_index.find_matching_faces(base, top_k=5, distance_threshold=0.5)
        matched_ids = [m.applicant_id for m in matches]
        assert matched_ids == ["app_v1", "app_v2", "app_v3"]
        assert matches[0].distance < matches[1].distance < matches[2].distance

    def test_exclude_applicant_id(self, in_memory_index: FaceDeduplicationIndex) -> None:
        emb = _unit_vec(300)
        in_memory_index.upsert_face_embedding("app_self", emb)

        # Without exclusion, matches itself
        matches = in_memory_index.find_matching_faces(emb)
        assert len(matches) == 1
        assert matches[0].applicant_id == "app_self"

        # With exclusion, ignores itself
        matches_excluded = in_memory_index.find_matching_faces(emb, exclude_applicant_id="app_self")
        assert len(matches_excluded) == 0

    def test_find_matches_for_applicant(self, in_memory_index: FaceDeduplicationIndex) -> None:
        base = _unit_vec(400)
        noise = np.random.default_rng(4).standard_normal(512).astype(np.float32) * 0.003
        variant = (base + noise) / np.linalg.norm(base + noise)

        in_memory_index.upsert_face_embedding("first_applicant", base)
        in_memory_index.upsert_face_embedding("second_applicant", variant)

        matches = in_memory_index.find_matches_for_applicant("second_applicant")
        assert len(matches) == 1
        assert matches[0].applicant_id == "first_applicant"

    def test_find_matches_for_nonexistent_applicant(self, in_memory_index: FaceDeduplicationIndex) -> None:
        matches = in_memory_index.find_matches_for_applicant("nonexistent_id")
        assert matches == []

    def test_delete_and_reset(self, in_memory_index: FaceDeduplicationIndex) -> None:
        emb = _unit_vec(500)
        in_memory_index.upsert_face_embedding("app_to_del", emb)
        assert in_memory_index.count() == 1

        ok = in_memory_index.delete_face_embedding("app_to_del")
        assert ok is True
        assert in_memory_index.count() == 0

        # Reset clears everything
        in_memory_index.upsert_face_embedding("app_1", emb)
        in_memory_index.reset()
        assert in_memory_index.count() == 0

    def test_invalid_and_raw_pii_rejected(self, in_memory_index: FaceDeduplicationIndex) -> None:
        emb = _unit_vec(600)

        # Raw phone number with +
        assert in_memory_index.upsert_face_embedding("+919876543210", emb) is False
        # Raw email with @
        assert in_memory_index.upsert_face_embedding("user@test.com", emb) is False
        # Empty string
        assert in_memory_index.upsert_face_embedding("", emb) is False
        # Zero vector
        zero_v = np.zeros(512, dtype=np.float32)
        assert in_memory_index.upsert_face_embedding("valid_hash_123", zero_v) is False
        # Empty vector
        assert in_memory_index.upsert_face_embedding("valid_hash_123", []) is False
        # Query with invalid vector
        assert in_memory_index.find_matching_faces([]) == []
        assert in_memory_index.count() == 0


class TestFaceReuseEdges:
    def test_create_face_reuse_edges(self) -> None:
        matches = [
            FaceMatch(
                applicant_id="existing_applicant_hash",
                distance=0.08,
                similarity=0.92,
                metadata={"doc_type": "aadhaar"},
            )
        ]
        edges = create_face_reuse_edges("new_applicant_hash", matches)
        assert len(edges) == 1
        edge = edges[0]
        assert edge.source_hash == "new_applicant_hash"
        assert edge.target_hash == "existing_applicant_hash"
        assert edge.edge_type == EdgeType.FACE_REUSE_DETECTED.value
        assert edge.source_type == NodeType.APPLICANT.value
        assert edge.target_type == NodeType.APPLICANT.value
        assert edge.weight == 0.92
        assert edge.properties_json["cosine_distance"] == 0.08
        assert edge.properties_json["cosine_similarity"] == 0.92
        assert edge.properties_json["doc_type"] == "aadhaar"

    def test_create_face_reuse_edges_skips_self(self) -> None:
        matches = [
            FaceMatch(applicant_id="same_id", distance=0.0, similarity=1.0)
        ]
        edges = create_face_reuse_edges("same_id", matches)
        assert edges == []
