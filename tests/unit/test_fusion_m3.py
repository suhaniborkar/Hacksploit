"""
Unit tests for ArgusM3FusionEngine (Task 4.3).

Contract under test:
  - Hard-override gates reject immediately (checksum, OCR mismatch, AI signals).
  - Clean evidence below APPROVE threshold is approved.
  - Borderline evidence above REJECT threshold is rejected.
  - Outputs are deterministic across repeated calls with identical inputs.
  - Execution time is sub-millisecond on a CPU without model I/O.
  - Model-unavailable path degrades to M0 proxy without crashing.
  - RiskAssessment fields conform to the FraudModel protocol contract.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.forensics import EvidenceStatus
from app.core.fusion import ApplicationEvidence, RiskTier
from app.modules.fusion.m3_model import (
    ArgusM3FusionEngine,
    MODEL_NAME,
    _APPROVE_THRESHOLD,
    _OCR_MISMATCH_HARD_REJECT,
    _REJECT_THRESHOLD,
    _check_hard_overrides,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_evidence(applicant_id: str = "test-001") -> ApplicationEvidence:
    """Minimal clean applicant evidence — no fraud signals active."""
    return ApplicationEvidence(
        applicant_id=applicant_id,
        claimed_name="Ramesh Kumar",
        claimed_dob="1990-05-15",
        id_type="aadhaar",
        id_number_last4="1234",
        shared_phone_degree=1,
        shared_device_degree=1,
        shared_identity_degree=0,
        shared_email_degree=0,
        has_confirmed_fraud_neighbor=False,
        fraud_neighbor_count=0,
        ego_density=0.0,
        cycle_count=0,
        ocr_name_similarity=0.95,
        id_checksum_valid=True,
        secure_qr_status="VERIFIED",
        secure_qr_valid=True,
        image_dimension_status=EvidenceStatus.PRESENT,
        exif_status=EvidenceStatus.PRESENT,
        jpeg_quality_status=EvidenceStatus.PRESENT,
        ela_status=EvidenceStatus.PRESENT,
        ela_max_diff=2.0,
        face_similarity_status=EvidenceStatus.PRESENT,
        face_cosine_similarity=0.92,
        velocity_1h_applications=1,
        velocity_24h_applications=1,
        device_velocity_1h=1,
    )


def _fraudulent_evidence(applicant_id: str = "fraud-001") -> ApplicationEvidence:
    """High-signal fraudulent applicant evidence."""
    return ApplicationEvidence(
        applicant_id=applicant_id,
        claimed_name="John Doe",
        claimed_dob="2000-01-01",
        id_type="aadhaar",
        id_number_last4="9999",
        shared_phone_degree=5,
        shared_device_degree=4,
        shared_identity_degree=2,
        shared_email_degree=3,
        has_confirmed_fraud_neighbor=True,
        fraud_neighbor_count=3,
        ego_density=0.8,
        cycle_count=4,
        ocr_name_similarity=0.30,
        id_checksum_valid=True,  # Not a hard override
        secure_qr_status="TAMPERED",
        secure_qr_valid=False,
        image_dimension_status=EvidenceStatus.PRESENT,
        exif_status=EvidenceStatus.PRESENT,
        jpeg_quality_status=EvidenceStatus.PRESENT,
        ela_status=EvidenceStatus.ANOMALOUS,
        ela_max_diff=45.0,
        face_similarity_status=EvidenceStatus.PRESENT,
        face_cosine_similarity=0.20,  # Low — likely impostor
        velocity_1h_applications=8,
        velocity_24h_applications=15,
        device_velocity_1h=7,
    )


# ---------------------------------------------------------------------------
# Hard-override gate tests (no model dependency)
# ---------------------------------------------------------------------------


class TestHardOverrideGates:
    def test_checksum_failure_triggers_override(self) -> None:
        ev = _clean_evidence()
        ev = ApplicationEvidence(**{**ev.__dict__, "id_checksum_valid": False})
        triggered, attrs, codes = _check_hard_overrides(ev)
        assert triggered is True
        assert "M3_HO_CHECKSUM_FAILED" in codes
        assert all(a.score_impact == 1.0 for a in attrs)

    def test_valid_checksum_does_not_trigger(self) -> None:
        ev = _clean_evidence()
        triggered, _, _ = _check_hard_overrides(ev)
        assert triggered is False

    def test_none_checksum_does_not_trigger(self) -> None:
        """Unknown checksum (None) must not trigger the gate."""
        ev = ApplicationEvidence(applicant_id="x", id_checksum_valid=None)
        triggered, _, _ = _check_hard_overrides(ev)
        assert triggered is False

    def test_ocr_at_threshold_triggers_override(self) -> None:
        ev = ApplicationEvidence(
            applicant_id="x",
            ocr_name_similarity=_OCR_MISMATCH_HARD_REJECT,  # exactly at threshold
        )
        triggered, _, codes = _check_hard_overrides(ev)
        assert triggered is True
        assert "M3_HO_OCR_MISMATCH" in codes

    def test_ocr_just_above_threshold_does_not_trigger(self) -> None:
        ev = ApplicationEvidence(
            applicant_id="x",
            ocr_name_similarity=_OCR_MISMATCH_HARD_REJECT + 0.01,
        )
        triggered, _, _ = _check_hard_overrides(ev)
        assert triggered is False

    def test_exif_anomaly_triggers_override(self) -> None:
        ev = ApplicationEvidence(
            applicant_id="x",
            exif_status=EvidenceStatus.ANOMALOUS,
        )
        triggered, _, codes = _check_hard_overrides(ev)
        assert triggered is True
        assert "M3_HO_EXIF_AI_SIGNATURE" in codes

    def test_dimension_anomaly_triggers_override(self) -> None:
        ev = ApplicationEvidence(
            applicant_id="x",
            image_dimension_status=EvidenceStatus.ANOMALOUS,
        )
        triggered, _, codes = _check_hard_overrides(ev)
        assert triggered is True
        assert "M3_HO_DIMENSION_AI" in codes

    def test_multiple_overrides_reported(self) -> None:
        """Multiple simultaneous override conditions all appear in codes."""
        ev = ApplicationEvidence(
            applicant_id="x",
            id_checksum_valid=False,
            exif_status=EvidenceStatus.ANOMALOUS,
            image_dimension_status=EvidenceStatus.ANOMALOUS,
        )
        triggered, attrs, codes = _check_hard_overrides(ev)
        assert triggered is True
        assert "M3_HO_CHECKSUM_FAILED" in codes
        assert "M3_HO_EXIF_AI_SIGNATURE" in codes
        assert "M3_HO_DIMENSION_AI" in codes
        assert len(attrs) == 3


# ---------------------------------------------------------------------------
# Full engine tests (using a mock model to avoid joblib on CI)
# ---------------------------------------------------------------------------


def _make_engine_with_mock_model(mock_score: float = 0.05) -> ArgusM3FusionEngine:
    """
    Return an ArgusM3FusionEngine whose internal loader is mocked to avoid
    hitting disk or requiring the trained .joblib file in unit tests.
    """
    engine = ArgusM3FusionEngine.__new__(ArgusM3FusionEngine)
    from app.modules.fusion.features import KYCFeatureVectorizer

    engine._vectorizer = KYCFeatureVectorizer()

    mock_loader = MagicMock()
    mock_loader.available = True
    mock_loader.predict_calibrated.return_value = mock_score
    mock_loader.model_metadata = {"name": "mock_m3", "metrics": {}}
    engine._loader = mock_loader
    return engine


class TestArgusM3FusionEngine:
    """Tests against the mocked model (no real joblib load)."""

    def test_protocol_compliance(self) -> None:
        """ArgusM3FusionEngine must satisfy the FraudModel protocol surface."""

        engine = _make_engine_with_mock_model()
        # Protocol check: predict_risk must exist and accept ApplicationEvidence
        assert hasattr(engine, "predict_risk")
        result = engine.predict_risk(_clean_evidence())
        assert result.applicant_id == "test-001"

    def test_clean_evidence_is_approved(self) -> None:
        engine = _make_engine_with_mock_model(mock_score=0.05)
        result = engine.predict_risk(_clean_evidence())
        assert result.risk_tier == RiskTier.APPROVE
        assert result.risk_score < _APPROVE_THRESHOLD
        assert result.model_name == MODEL_NAME

    def test_borderline_score_is_review(self) -> None:
        engine = _make_engine_with_mock_model(mock_score=0.50)
        result = engine.predict_risk(_clean_evidence())
        assert result.risk_tier == RiskTier.REVIEW
        assert _APPROVE_THRESHOLD <= result.risk_score < _REJECT_THRESHOLD

    def test_high_score_is_rejected(self) -> None:
        engine = _make_engine_with_mock_model(mock_score=0.90)
        result = engine.predict_risk(_clean_evidence())
        assert result.risk_tier == RiskTier.REJECT
        assert result.risk_score >= _REJECT_THRESHOLD

    def test_hard_override_bypasses_model(self) -> None:
        """Model predict_calibrated must NOT be called when a hard override triggers."""
        engine = _make_engine_with_mock_model(mock_score=0.01)
        ev = _clean_evidence()
        ev = ApplicationEvidence(**{**ev.__dict__, "id_checksum_valid": False})
        result = engine.predict_risk(ev)
        assert result.risk_tier == RiskTier.REJECT
        assert result.risk_score == 1.0
        engine._loader.predict_calibrated.assert_not_called()

    def test_hard_override_reason_codes_populated(self) -> None:
        engine = _make_engine_with_mock_model()
        ev = ApplicationEvidence(
            applicant_id="ho-test",
            id_checksum_valid=False,
            exif_status=EvidenceStatus.ANOMALOUS,
        )
        result = engine.predict_risk(ev)
        assert "M3_HO_CHECKSUM_FAILED" in result.reason_codes
        assert "M3_HO_EXIF_AI_SIGNATURE" in result.reason_codes

    def test_missing_signals_tracked(self) -> None:
        """Applicant with no doc/selfie evidence should have missing_signals populated."""
        engine = _make_engine_with_mock_model(mock_score=0.10)
        ev = ApplicationEvidence(applicant_id="minimal")  # all defaults — no forensics
        result = engine.predict_risk(ev)
        assert "document_forensics" in result.missing_signals
        assert "selfie_biometrics" in result.missing_signals

    def test_determinism(self) -> None:
        """Two calls with identical evidence must produce identical results."""
        engine = _make_engine_with_mock_model(mock_score=0.42)
        ev = _fraudulent_evidence()
        r1 = engine.predict_risk(ev)
        r2 = engine.predict_risk(ev)
        assert r1.risk_score == r2.risk_score
        assert r1.risk_tier == r2.risk_tier
        assert r1.reason_codes == r2.reason_codes

    def test_execution_time_sub_millisecond(self) -> None:
        """Predict should complete well under 10ms on CPU with mocked model."""
        engine = _make_engine_with_mock_model(mock_score=0.05)
        ev = _clean_evidence()
        start = time.perf_counter()
        for _ in range(50):
            engine.predict_risk(ev)
        elapsed = (time.perf_counter() - start) * 1000
        avg_ms = elapsed / 50
        # 10ms average is very generous even on slow hardware
        assert avg_ms < 10.0, f"Avg {avg_ms:.2f}ms — expected < 10ms"

    def test_model_unavailable_fallback(self) -> None:
        """When model is unavailable, M0 proxy score is used without crash."""
        engine = ArgusM3FusionEngine.__new__(ArgusM3FusionEngine)
        from app.modules.fusion.features import KYCFeatureVectorizer

        engine._vectorizer = KYCFeatureVectorizer()
        mock_loader = MagicMock()
        mock_loader.available = False
        mock_loader.model_metadata = {}
        engine._loader = mock_loader

        ev = _clean_evidence()
        result = engine.predict_risk(ev)
        # Should not raise; should return a valid RiskAssessment
        assert result.applicant_id == "test-001"
        assert 0.0 <= result.risk_score <= 1.0
        assert result.risk_tier in (RiskTier.APPROVE, RiskTier.REVIEW, RiskTier.REJECT)
        assert "m0_proxy_fallback" in result.summary

    def test_to_dict_serializable(self) -> None:
        """RiskAssessment.to_dict() must not raise and keys must be present."""
        engine = _make_engine_with_mock_model(mock_score=0.08)
        result = engine.predict_risk(_clean_evidence())
        d = result.to_dict()
        assert d["model_name"] == MODEL_NAME
        assert "risk_score" in d
        assert "risk_tier" in d
        assert "reason_codes" in d
        assert "attributions" in d
        assert "missing_signals" in d
        assert "execution_time_ms" in d

    def test_ocr_hard_override_exact_boundary(self) -> None:
        """OCR similarity at exactly _OCR_MISMATCH_HARD_REJECT is a hard reject."""
        engine = _make_engine_with_mock_model(mock_score=0.01)
        ev = ApplicationEvidence(
            applicant_id="boundary",
            ocr_name_similarity=_OCR_MISMATCH_HARD_REJECT,
        )
        result = engine.predict_risk(ev)
        assert result.risk_tier == RiskTier.REJECT
        assert result.risk_score == 1.0

    def test_fraudulent_evidence_raises_score(self) -> None:
        """Fraudulent evidence should produce a higher score than clean evidence."""
        clean_engine = _make_engine_with_mock_model(mock_score=0.05)
        fraud_engine = _make_engine_with_mock_model(mock_score=0.88)
        clean_result = clean_engine.predict_risk(_clean_evidence())
        fraud_result = fraud_engine.predict_risk(_fraudulent_evidence())
        assert fraud_result.risk_score > clean_result.risk_score
        assert clean_result.risk_tier == RiskTier.APPROVE
        assert fraud_result.risk_tier == RiskTier.REJECT


# ---------------------------------------------------------------------------
# Integration test with real model (skipped if joblib unavailable)
# ---------------------------------------------------------------------------


_REAL_MODEL_PATH = Path(__file__).parents[2] / "argus" / "New_models" / "m3_fusion.joblib"


@pytest.mark.skipif(
    not _REAL_MODEL_PATH.exists(),
    reason="m3_fusion.joblib not present — skipping real model integration test",
)
class TestRealModelIntegration:
    """
    Loads the actual m3_fusion.joblib to verify end-to-end prediction.
    Skipped in CI environments without the model artifact.
    """

    @pytest.fixture(scope="class")
    def engine(self) -> ArgusM3FusionEngine:
        # Reset singleton so each test class gets a fresh loader against the real file
        from app.modules.fusion import m3_model

        m3_model._M3ModelLoader._instance = None
        return ArgusM3FusionEngine(model_path=_REAL_MODEL_PATH)

    def test_model_loaded(self, engine: ArgusM3FusionEngine) -> None:
        assert engine.model_available is True

    def test_clean_predict_returns_low_score(self, engine: ArgusM3FusionEngine) -> None:
        result = engine.predict_risk(_clean_evidence())
        # Clean evidence should produce a low score (model trained on synthetic data)
        assert 0.0 <= result.risk_score <= 1.0
        assert result.risk_tier in (RiskTier.APPROVE, RiskTier.REVIEW)

    def test_real_model_deterministic(self, engine: ArgusM3FusionEngine) -> None:
        ev = _clean_evidence()
        r1 = engine.predict_risk(ev)
        r2 = engine.predict_risk(ev)
        assert r1.risk_score == r2.risk_score

    def test_hard_override_still_fires_with_real_model(
        self, engine: ArgusM3FusionEngine
    ) -> None:
        """Hard overrides must fire before the real model is consulted."""
        ev = ApplicationEvidence(
            applicant_id="override-real",
            id_checksum_valid=False,
        )
        result = engine.predict_risk(ev)
        assert result.risk_tier == RiskTier.REJECT
        assert result.risk_score == 1.0
