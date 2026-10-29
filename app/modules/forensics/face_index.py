"""
Local Face Deduplication Index using ChromaDB.

Stores ArcFace 512-d embeddings keyed by pseudonymized applicant_id.
Enables fast nearest-neighbor lookups with cosine distance metric to detect
identity duplication across multiple KYC submissions under different Aadhaar/PAN cards.

Cosine distance in ChromaDB:
    distance = 1.0 - cosine_similarity
    distance <= 0.35 <=> cosine_similarity >= 0.65 (indicates face reuse)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

try:
    import chromadb
    from chromadb.api import ClientAPI
    CHROMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore[assignment]
    ClientAPI = Any  # type: ignore[assignment,misc]
    CHROMA_AVAILABLE = False

from app.core.config import settings
from app.core.forensics import FaceMatch
from app.modules.graph.models import ApplicantEdge, EdgeType, NodeType, check_no_raw_pii

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_NAME: str = "face_dedup_index"
DEFAULT_DISTANCE_THRESHOLD: float = 0.35  # Cosine distance <= 0.35 <=> similarity >= 0.65
DEFAULT_TOP_K: int = 5
EMBEDDING_DIM: int = 512


class FaceDeduplicationIndex:
    """
    Local vector index for facial embeddings to detect cross-identity biometric reuse.
    Supports dependency injection of custom ChromaDB clients (e.g. EphemeralClient for unit tests).
    """

    def __init__(
        self,
        client: ClientAPI | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_dir: str | Path | None = None,
        in_memory: bool = False,
    ) -> None:
        if not CHROMA_AVAILABLE:
            raise RuntimeError("chromadb is not installed. Install with: pip install chromadb")

        self.collection_name = collection_name

        if client is not None:
            self._client = client
        elif in_memory:
            self._client = chromadb.EphemeralClient()
        else:
            p_dir = Path(persist_dir or settings.chroma_persist_dir)
            p_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(p_dir))

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Returns total number of face embeddings indexed."""
        return self._collection.count()

    def upsert_face_embedding(
        self,
        applicant_id: str,
        embedding: np.ndarray | list[float],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Stores or updates a 512-d ArcFace embedding for an applicant.
        Returns True on success, False if embedding or applicant_id is invalid.
        """
        if not applicant_id or not isinstance(applicant_id, str):
            logger.warning("Rejected face embedding upsert: invalid applicant_id.")
            return False

        # Guard against raw PII in identifier
        try:
            check_no_raw_pii(applicant_id, "applicant_id")
        except ValueError as exc:
            logger.warning("Rejected face embedding upsert: %s", exc)
            return False

        emb_list = self._sanitize_embedding(embedding)
        if emb_list is None:
            logger.warning("Rejected face embedding upsert for %s: invalid vector.", applicant_id)
            return False

        meta = dict(metadata or {})
        # ChromaDB requires primitive metadata values
        cleaned_meta = {
            k: str(v) if isinstance(v, (dict, list)) else v
            for k, v in meta.items()
            if v is not None
        }

        self._collection.upsert(
            ids=[applicant_id],
            embeddings=[emb_list],
            metadatas=[cleaned_meta] if cleaned_meta else None,
        )
        return True

    def find_matching_faces(
        self,
        embedding: np.ndarray | list[float],
        top_k: int = DEFAULT_TOP_K,
        distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
        exclude_applicant_id: str | None = None,
    ) -> list[FaceMatch]:
        """
        Finds faces in the index within distance_threshold of the query embedding.
        Returns matches ordered by distance ascending.
        """
        total = self.count()
        if total == 0:
            return []

        emb_list = self._sanitize_embedding(embedding)
        if emb_list is None:
            return []

        n_query = min(total, top_k + (1 if exclude_applicant_id else 0))
        results = self._collection.query(
            query_embeddings=[emb_list],
            n_results=n_query,
            include=["metadatas", "distances"],
        )

        matches: list[FaceMatch] = []
        ids_list = results.get("ids", [[]])[0]
        distances_list = results.get("distances", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0] if results.get("metadatas") else [{}] * len(ids_list)

        for match_id, dist, meta in zip(ids_list, distances_list, metas_list):
            if exclude_applicant_id and match_id == exclude_applicant_id:
                continue

            dist_f = float(dist)
            if dist_f > distance_threshold:
                continue

            similarity = max(-1.0, min(1.0, 1.0 - dist_f))
            matches.append(
                FaceMatch(
                    applicant_id=match_id,
                    distance=dist_f,
                    similarity=similarity,
                    metadata=meta if isinstance(meta, dict) else {},
                )
            )

        matches.sort(key=lambda m: m.distance)
        return matches[:top_k]

    def search(
        self,
        embedding: np.ndarray | list[float],
        applicant_id: str | None = None,
        top_k: int = DEFAULT_TOP_K,
        distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
    ) -> list[FaceMatch]:
        """Convenience alias for find_matching_faces."""
        return self.find_matching_faces(
            embedding=embedding,
            top_k=top_k,
            distance_threshold=distance_threshold,
            exclude_applicant_id=applicant_id,
        )

    def index_face(
        self,
        applicant_id: str,
        embedding: np.ndarray | list[float],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Convenience alias for upsert_face_embedding."""
        return self.upsert_face_embedding(
            applicant_id=applicant_id,
            embedding=embedding,
            metadata=metadata,
        )

    def find_matches_for_applicant(
        self,
        applicant_id: str,
        top_k: int = DEFAULT_TOP_K,
        distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
    ) -> list[FaceMatch]:
        """Looks up the stored embedding for applicant_id and searches for duplicates."""
        got = self._collection.get(ids=[applicant_id], include=["embeddings"])
        embeddings = got.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return []

        return self.find_matching_faces(
            embedding=embeddings[0],
            top_k=top_k,
            distance_threshold=distance_threshold,
            exclude_applicant_id=applicant_id,
        )

    def delete_face_embedding(self, applicant_id: str) -> bool:
        """Removes an applicant's face embedding from the index."""
        try:
            self._collection.delete(ids=[applicant_id])
            return True
        except Exception as exc:
            logger.warning("Failed to delete face embedding for %s: %s", applicant_id, exc)
            return False

    def reset(self) -> None:
        """Clears all records in the collection."""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _sanitize_embedding(embedding: np.ndarray | list[float]) -> list[float] | None:
        """Validates and converts embedding vector to list of float values."""
        if embedding is None:
            return None

        if isinstance(embedding, (list, tuple)):
            if len(embedding) == 0:
                return None
            arr = np.array(embedding, dtype=np.float32)
        elif isinstance(embedding, np.ndarray):
            if embedding.size == 0:
                return None
            arr = embedding.flatten().astype(np.float32)
        else:
            return None

        norm = float(np.linalg.norm(arr))
        if norm == 0.0 or np.isnan(norm) or np.isinf(norm):
            return None

        return arr.tolist()


def create_face_reuse_edges(
    applicant_id: str,
    matches: list[FaceMatch],
) -> list[ApplicantEdge]:
    """
    Constructs ApplicantEdge instances linking applicant_id to matching identities
    with EdgeType.FACE_REUSE_DETECTED.
    """
    edges: list[ApplicantEdge] = []
    for match in matches:
        if match.applicant_id == applicant_id:
            continue
        edge = ApplicantEdge(
            source_hash=applicant_id,
            target_hash=match.applicant_id,
            edge_type=EdgeType.FACE_REUSE_DETECTED.value,
            source_type=NodeType.APPLICANT.value,
            target_type=NodeType.APPLICANT.value,
            weight=round(match.similarity, 4),
            properties_json={
                "cosine_distance": round(match.distance, 4),
                "cosine_similarity": round(match.similarity, 4),
                "matched_applicant_id": match.applicant_id,
                **match.metadata,
            },
        )
        edges.append(edge)
    return edges
