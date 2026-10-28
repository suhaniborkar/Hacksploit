import re
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    JSON,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.infrastructure.database import Base
from app.modules.identity.models import ensure_utc, utcnow


class NodeType(StrEnum):
    APPLICANT = "applicant"
    PHONE = "phone"
    EMAIL = "email"
    IDENTITY = "identity"  # National ID, Aadhaar, SSN
    DEVICE = "device"
    BANK_ACCOUNT = "bank_account"
    IP_ADDRESS = "ip_address"


class EdgeType(StrEnum):
    HAS_PHONE = "HAS_PHONE"
    HAS_EMAIL = "HAS_EMAIL"
    HAS_SSN = "HAS_SSN"
    HAS_IDENTITY = "HAS_IDENTITY"
    HAS_DEVICE = "HAS_DEVICE"
    HAS_BANK_ACCOUNT = "HAS_BANK_ACCOUNT"
    HAS_IP = "HAS_IP"
    SHARED_PHONE = "SHARED_PHONE"
    SHARED_EMAIL = "SHARED_EMAIL"
    SHARED_IDENTITY = "SHARED_IDENTITY"
    SHARED_DEVICE = "SHARED_DEVICE"
    SHARED_IDENTIFIER = "SHARED_IDENTIFIER"
    SIMILAR_TO = "SIMILAR_TO"
    FACE_REUSE_DETECTED = "FACE_REUSE_DETECTED"


HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_pseudonymized_hash(value: str | None, field_name: str) -> str | None:
    """
    Validates that identifier columns contain salted HMAC-SHA256 digests (64 hex characters)
    and strictly forbids raw PII from being stored in the relational identity graph.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not HEX_64_PATTERN.match(value):
        raise ValueError(
            f"Field '{field_name}' must be a 64-character hexadecimal HMAC-SHA256 digest; "
            f"storing raw PII is strictly prohibited."
        )
    return value.lower()


def check_no_raw_pii(value: str, field_name: str) -> str:
    """
    Ensures edge nodes and identifiers do not contain obvious raw PII strings
    such as plain emails, phone numbers with formatting, or spaces.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Field '{field_name}' must be a non-empty string.")
    cleaned = value.strip()
    if "@" in cleaned or "+" in cleaned or " " in cleaned:
        raise ValueError(
            f"Field '{field_name}' appears to contain raw unhashed PII ('{cleaned}'). "
            f"Values must be pseudonymized (salted HMAC-SHA256 digest or system ID) before persisting."
        )
    return cleaned


class ApplicantNode(Base):
    """
    Relational representation of an applicant identity profile in the identity graph.
    All identifier columns store cryptographic HMAC-SHA256 hex digests; raw PII is never stored.
    """
    __tablename__ = "applicant_nodes"
    __table_args__ = (
        Index("ix_applicant_nodes_applicant_id", "applicant_id", unique=True),
        Index("ix_applicant_nodes_identity_hash", "identity_hash"),
        Index("ix_applicant_nodes_phone_hash", "phone_hash"),
        Index("ix_applicant_nodes_email_hash", "email_hash"),
        Index("ix_applicant_nodes_device_hash", "device_fingerprint_hash"),
        Index("ix_applicant_nodes_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    applicant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NodeType.APPLICANT.value
    )

    # Pseudonymized Identifier Hashes (HMAC-SHA256 hex digests only)
    identity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_fingerprint_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Screening Status & Prior Risk Signals
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_fraud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # General Non-PII Attributes & Metadata (e.g., session metadata, demographic ratios)
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    @validates("identity_hash", "phone_hash", "email_hash", "device_fingerprint_hash", "ip_address_hash")
    def _validate_hashes(self, key: str, value: str | None) -> str | None:
        return validate_pseudonymized_hash(value, key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "applicant_id": self.applicant_id,
            "node_type": self.node_type,
            "identity_hash": self.identity_hash,
            "phone_hash": self.phone_hash,
            "email_hash": self.email_hash,
            "device_fingerprint_hash": self.device_fingerprint_hash,
            "ip_address_hash": self.ip_address_hash,
            "status": self.status,
            "risk_score": self.risk_score,
            "is_fraud": self.is_fraud,
            "properties": dict(self.properties_json) if self.properties_json else {},
            "created_at": ensure_utc(self.created_at).isoformat() if self.created_at else None,
            "updated_at": ensure_utc(self.updated_at).isoformat() if self.updated_at else None,
        }


class ApplicantEdge(Base):
    """
    Indexed directional identity relationship in PostgreSQL.
    Composite indices on (source_hash, edge_type) and (target_hash, edge_type) provide O(log n)
    fast-path 1-hop rule evaluations and bounded 2-hop ego-network traversals.
    """
    __tablename__ = "applicant_edges"
    __table_args__ = (
        Index("ix_applicant_edges_source_edge_type", "source_hash", "edge_type"),
        Index("ix_applicant_edges_target_edge_type", "target_hash", "edge_type"),
        Index("ix_applicant_edges_source_target", "source_hash", "target_hash"),
        UniqueConstraint("source_hash", "target_hash", "edge_type", name="uq_applicant_edges_source_target_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    target_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(32), nullable=False)

    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NodeType.APPLICANT.value
    )
    target_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="identifier"
    )

    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    @validates("source_hash", "target_hash")
    def _validate_endpoints(self, key: str, value: str) -> str:
        return check_no_raw_pii(value, key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "source_hash": self.source_hash,
            "target_hash": self.target_hash,
            "edge_type": self.edge_type,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "weight": self.weight,
            "properties": dict(self.properties_json) if self.properties_json else {},
            "created_at": ensure_utc(self.created_at).isoformat() if self.created_at else None,
        }
