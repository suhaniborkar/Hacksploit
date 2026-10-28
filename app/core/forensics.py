from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class EvidenceStatus(StrEnum):
    """
    Standard evidence indicator states per ARCHITECTURE.md §3 Invariant Rule 4.
    Missing signals are explicitly tracked as UNAVAILABLE, never silently defaulted to clean/passed.
    """
    PRESENT = "PRESENT"
    ANOMALOUS = "ANOMALOUS"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class ExtractedDocument:
    """Document fields and textual evidence extracted via OCR or Secure QR code."""
    raw_text: str
    fields: dict[str, str] = field(default_factory=dict)
    extraction_method: str = "ocr"  # "ocr", "secure_qr", "hybrid"
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "fields": self.fields,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class TamperingSignal:
    """Independent tampering and integrity signal produced by forensic adapters."""
    signal_name: str
    status: EvidenceStatus
    score: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "status": self.status.value,
            "score": self.score,
            "details": self.details,
        }


class ForensicExtractor(Protocol):
    """
    Protocol for document forensic extraction and forgery assessment.
    Core KYC flows consume this contract without importing concrete vision models.
    """

    def extract_fields(self, document_bytes: bytes, mime_type: str) -> ExtractedDocument:
        """Extracts demographic text fields (name, DOB, ID number) from document bytes."""
        ...

    def assess_tampering(self, document_bytes: bytes, mime_type: str) -> TamperingSignal:
        """Assesses document integrity, tampering artifacts, or digital signature status."""
        ...


@dataclass
class FaceMatch:
    """Represents a matched face embedding from the deduplication index."""
    applicant_id: str
    distance: float
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applicant_id": self.applicant_id,
            "distance": round(self.distance, 4),
            "similarity": round(self.similarity, 4),
            "metadata": self.metadata,
        }

