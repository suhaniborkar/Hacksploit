"""
Argus M3 Calibrated Multi-Source Fusion Engine (Task 4.3).

Architecture constraints (ARCHITECTURE.md §2):
- Conforms to the ``FraudModel`` protocol: ``predict_risk(features) -> RiskAssessment``.
- Core logic depends on the ``FraudModel`` protocol abstraction, never on LightGBM
  directly; the concrete import lives inside the lazy singleton loader.
- Hard-override gates execute before any statistical model path.

Statutory hard-override rules (deterministic, not probabilistic):
  1. Failed Aadhaar Verhoeff / PAN format checksum  → REJECT, risk = 1.0
  2. Severe OCR name mismatch (similarity <= 0.20)  → REJECT, risk = 1.0
  3. Synthetic AI document flags (EXIF / dimension) → REJECT, risk = 1.0

If no override triggers, the 10-dimensional ``M3FeatureVector`` is passed through
the LightGBM booster followed by isotonic regression calibration.

Calibrated operational thresholds (plan spec):
  APPROVE : calibrated score < 0.25
  REVIEW  : calibrated score 0.25 <= score < 0.75
  REJECT  : calibrated score >= 0.75

Lazy singleton: the model is loaded on the first call, not at import time.
Any load failure degrades gracefully to the M0 rule-based fallback score.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.core.forensics import EvidenceStatus
from app.core.fusion import (
    ApplicationEvidence,
    EvidenceAttribution,
    FraudModel,
    RiskAssessment,
    RiskTier,
)
from app.modules.fusion.features import KYCFeatureVectorizer, M3FeatureVector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operational thresholds (plan specification)
# ---------------------------------------------------------------------------

_APPROVE_THRESHOLD: float = 0.25
_REJECT_THRESHOLD: float = 0.75

# Hard-override thresholds
_OCR_MISMATCH_HARD_REJECT: float = 0.20  # similarity <= this -> REJECT

# Default model path relative to repository root
_DEFAULT_MODEL_PATH: Path = (
    Path(__file__).parents[3] / "argus" / "New_models" / "m3_fusion.joblib"
)

MODEL_NAME: str = "ArgusM3FusionEngine"


# ---------------------------------------------------------------------------
# Lazy singleton model loader
# ---------------------------------------------------------------------------


class _M3ModelLoader:
    """
    Thread-safe lazy loader for the LightGBM booster + isotonic calibrator.

    Load failures are logged and exposed via ``available``; callers fall back
    to rule-based scoring rather than crashing.
    """

    _instance: "_M3ModelLoader | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, model_path: Path = _DEFAULT_MODEL_PATH) -> "_M3ModelLoader":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._booster = None  # type: ignore[attr-defined]
                obj._calibrator = None  # type: ignore[attr-defined]
                obj._features: list[str] = []  # type: ignore[attr-defined]
                obj._model_thresholds: dict[str, float] = {}  # type: ignore[attr-defined]
                obj._available: bool = False  # type: ignore[attr-defined]
                obj._load_error: str | None = None  # type: ignore[attr-defined]
                obj._model_metadata: dict[str, Any] = {}  # type: ignore[attr-defined]
                obj._load(model_path)
                cls._instance = obj
            return cls._instance  # type: ignore[return-value]

    def _load(self, model_path: Path) -> None:
        if not model_path.exists():
            self._load_error = f"Model file not found: {model_path}"
            logger.warning(
                "%s — M3 fusion engine will degrade to rule-based scoring.",
                self._load_error,
            )
            return
        try:
            import warnings

            import joblib

            with warnings.catch_warnings():
                # IsotonicRegression may warn about sklearn version drift; safe to ignore.
                warnings.filterwarnings("ignore", category=UserWarning)
                data = joblib.load(model_path)

            self._booster = data["model"]
            self._calibrator = data["calibrator"]
            self._features = data.get("features", [])
            self._model_thresholds = data.get("thresholds", {})
            self._model_metadata = {
                "name": data.get("name", "m3_fusion"),
                "calibration": data.get("calibration", "unknown"),
                "metrics": data.get("metrics", {}),
                "timestamp": data.get("timestamp", ""),
            }
            self._available = True
            logger.info(
                "M3 fusion model loaded from %s (features=%d, calibration=%s).",
                model_path,
                len(self._features),
                self._model_metadata["calibration"],
            )
        except Exception as exc:
            self._load_error = str(exc)
            logger.exception(
                "M3 model load failed: %s — degrading to rule-based scoring.", exc
            )

    @property
    def available(self) -> bool:
        return self._available

    def predict_calibrated(self, fv: M3FeatureVector) -> float:
        """
        Pass *fv* through booster -> isotonic calibrator.
        Returns a probability in [0.0, 1.0].

        Raises ``RuntimeError`` if model is not loaded.
        """
        if not self._available:
            raise RuntimeError("M3 model not loaded")
        arr = fv.to_numpy().reshape(1, -1)
        raw: np.ndarray = self._booster.predict(arr)
        calibrated: np.ndarray = self._calibrator.predict(raw.reshape(-1, 1))
        return float(np.clip(calibrated[0], 0.0, 1.0))

    @property
    def model_metadata(self) -> dict[str, Any]:
        return self._model_metadata


# ---------------------------------------------------------------------------
# Hard-override gate
# ---------------------------------------------------------------------------


def _check_hard_overrides(
    evidence: ApplicationEvidence,
) -> tuple[bool, list[EvidenceAttribution], list[str]]:
    """
    Evaluate statutory hard-override gates.

    Returns:
        (triggered, attributions, reason_codes)

    When ``triggered`` is True the caller must immediately return
    ``RiskTier.REJECT`` with ``risk_score = 1.0``; the model is not consulted.
    """
    attributions: list[EvidenceAttribution] = []
    reason_codes: list[str] = []

    # Gate 1 — statutory checksum failure (Verhoeff / PAN format)
    if evidence.id_checksum_valid is False:
        attributions.append(
            EvidenceAttribution(
                rule_id="M3_HO_CHECKSUM_FAILED",
                signal_name="statutory_checksum",
                severity="REJECT",
                score_impact=1.0,
                description=(
                    "Statutory identity number checksum failed "
                    "(Verhoeff D5 or PAN format)."
                ),
                evidence_status=EvidenceStatus.ANOMALOUS,
            )
        )
        reason_codes.append("M3_HO_CHECKSUM_FAILED")

    # Gate 2 — severe OCR name mismatch
    if (
        evidence.ocr_name_similarity is not None
        and evidence.ocr_name_similarity <= _OCR_MISMATCH_HARD_REJECT
    ):
        attributions.append(
            EvidenceAttribution(
                rule_id="M3_HO_OCR_MISMATCH",
                signal_name="ocr_name_contradiction",
                severity="REJECT",
                score_impact=1.0,
                description=(
                    f"OCR name similarity {evidence.ocr_name_similarity:.2f} "
                    f"<= {_OCR_MISMATCH_HARD_REJECT} hard-override threshold."
                ),
                evidence_status=EvidenceStatus.ANOMALOUS,
            )
        )
        reason_codes.append("M3_HO_OCR_MISMATCH")

    # Gate 3 — synthetic AI-generated document signals
    ai_signal_checks = [
        (evidence.exif_status, "EXIF metadata AI signature", "M3_HO_EXIF_AI_SIGNATURE"),
        (evidence.image_dimension_status, "image dimension anomaly", "M3_HO_DIMENSION_AI"),
    ]
    for status, label, code in ai_signal_checks:
        if status == EvidenceStatus.ANOMALOUS:
            attributions.append(
                EvidenceAttribution(
                    rule_id=code,
                    signal_name="ai_generation_signal",
                    severity="REJECT",
                    score_impact=1.0,
                    description=f"Synthetic AI generation detected via {label}.",
                    evidence_status=EvidenceStatus.ANOMALOUS,
                )
            )
            reason_codes.append(code)

    return bool(attributions), attributions, reason_codes


# ---------------------------------------------------------------------------
# Component score attributions (model path)
# ---------------------------------------------------------------------------


def _build_model_attributions(
    fv: M3FeatureVector,
    calibrated_score: float,
    missing_signals: list[str],
) -> list[EvidenceAttribution]:
    """Build informational attributions for model-path predictions."""
    attributions: list[EvidenceAttribution] = []

    def _attr(
        rule_id: str,
        signal: str,
        severity: str,
        impact: float,
        desc: str,
    ) -> None:
        attributions.append(
            EvidenceAttribution(
                rule_id=rule_id,
                signal_name=signal,
                severity=severity,
                score_impact=round(impact, 4),
                description=desc,
            )
        )

    if fv.m1_prob >= 0.6:
        _attr(
            "M3_M1_VELOCITY",
            "behavioral_velocity",
            "REVIEW",
            fv.m1_prob,
            f"High behavioral velocity proxy: {fv.m1_prob:.2f}.",
        )

    if fv.m2_prob >= 0.5:
        _attr(
            "M3_M2_GRAPH",
            "graph_risk",
            "REVIEW" if fv.m2_prob < 0.75 else "REJECT",
            fv.m2_prob,
            f"Elevated ego-network graph risk: {fv.m2_prob:.2f}.",
        )

    if fv.m0_rule_score >= 0.5:
        _attr(
            "M3_M0_RULE",
            "m0_rule_score",
            "REVIEW" if fv.m0_rule_score < 0.75 else "REJECT",
            fv.m0_rule_score,
            f"M0 deterministic rules raised score to {fv.m0_rule_score:.2f}.",
        )

    if fv.ocr_contradiction >= 0.5:
        _attr(
            "M3_OCR",
            "ocr_contradiction",
            "REVIEW",
            fv.ocr_contradiction,
            f"OCR name contradiction score: {fv.ocr_contradiction:.2f}.",
        )

    if fv.face_cosine_dist >= 0.6 and "selfie_biometrics" not in missing_signals:
        _attr(
            "M3_FACE_DIST",
            "face_cosine_distance",
            "REVIEW",
            fv.face_cosine_dist,
            f"Document-selfie face distance: {fv.face_cosine_dist:.2f}.",
        )

    if fv.tampering_ela_score >= 0.5:
        _attr(
            "M3_ELA",
            "ela_tampering",
            "REVIEW",
            fv.tampering_ela_score,
            f"ELA tampering score: {fv.tampering_ela_score:.2f}.",
        )

    # Fusion summary entry (always present)
    if calibrated_score >= _REJECT_THRESHOLD:
        fusion_severity = "REJECT"
    elif calibrated_score >= _APPROVE_THRESHOLD:
        fusion_severity = "REVIEW"
    else:
        fusion_severity = "INFO"

    _attr(
        "M3_FUSION_SCORE",
        "m3_calibrated_fusion",
        fusion_severity,
        calibrated_score,
        f"M3 isotonic-calibrated fusion score: {calibrated_score:.4f}.",
    )

    return attributions


# ---------------------------------------------------------------------------
# Public model class
# ---------------------------------------------------------------------------


class ArgusM3FusionEngine:
    """
    Calibrated multi-source fusion engine.

    Implements the ``FraudModel`` protocol.  Consumes a populated
    ``ApplicationEvidence`` instance, applies deterministic hard-override
    gates, then (if no override triggers) passes the extracted
    ``M3FeatureVector`` through the LightGBM booster and isotonic calibrator.

    The class is thread-safe; the internal model loader is a singleton.
    """

    def __init__(self, model_path: Path = _DEFAULT_MODEL_PATH) -> None:
        self._loader = _M3ModelLoader(model_path)
        self._vectorizer = KYCFeatureVectorizer()

    @property
    def model_available(self) -> bool:
        """True when the trained model loaded successfully."""
        return self._loader.available

    @property
    def model_metadata(self) -> dict[str, Any]:
        return self._loader.model_metadata

    def predict_risk(self, features: ApplicationEvidence) -> RiskAssessment:
        """
        Evaluate evidence and return a calibrated ``RiskAssessment``.

        Hard-override gates are evaluated first.  If any trigger, the result
        is an immediate REJECT at risk_score = 1.0 without model invocation.

        If no override triggers and the model is loaded, the 10-d feature
        vector is passed through the LightGBM booster + isotonic calibrator.

        If the model is unavailable, the M0 proxy score from the feature
        vector is used as a degraded fallback (documented in the summary).
        """
        t_start = time.perf_counter()

        # Step 1: statutory hard overrides
        override_triggered, override_attrs, override_codes = _check_hard_overrides(features)

        if override_triggered:
            return RiskAssessment(
                applicant_id=features.applicant_id,
                model_name=MODEL_NAME,
                risk_score=1.0,
                risk_tier=RiskTier.REJECT,
                reason_codes=override_codes,
                attributions=override_attrs,
                missing_signals=[],
                execution_time_ms=(time.perf_counter() - t_start) * 1000,
                summary=(
                    "Hard-override rejection: "
                    + "; ".join(
                        c.replace("M3_HO_", "").replace("_", " ") for c in override_codes
                    )
                    + "."
                ),
            )

        # Step 2: feature extraction
        fv = self._vectorizer.extract(features)

        missing_signals: list[str] = []
        if fv.is_doc_missing:
            missing_signals.append("document_forensics")
        if fv.is_selfie_missing:
            missing_signals.append("selfie_biometrics")
        if fv.is_graph_isolated:
            missing_signals.append("graph_neighbours")

        # Step 3: model prediction or fallback
        if self._loader.available:
            try:
                calibrated_score = self._loader.predict_calibrated(fv)
                model_path_used = "lgbm+isotonic"
            except Exception as exc:
                logger.warning("M3 prediction failed (%s); degrading to M0 proxy.", exc)
                calibrated_score = fv.m0_rule_score
                model_path_used = "m0_proxy_fallback"
        else:
            calibrated_score = fv.m0_rule_score
            model_path_used = "m0_proxy_fallback"

        # Step 4: tier assignment
        if calibrated_score >= _REJECT_THRESHOLD:
            tier = RiskTier.REJECT
        elif calibrated_score >= _APPROVE_THRESHOLD:
            tier = RiskTier.REVIEW
        else:
            tier = RiskTier.APPROVE

        # Step 5: attributions
        attributions = _build_model_attributions(fv, calibrated_score, missing_signals)
        reason_codes = [
            a.rule_id for a in attributions if a.severity in ("REJECT", "REVIEW")
        ]
        if not reason_codes:
            reason_codes = ["M3_APPROVE_CLEAN"]

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return RiskAssessment(
            applicant_id=features.applicant_id,
            model_name=MODEL_NAME,
            risk_score=calibrated_score,
            risk_tier=tier,
            reason_codes=reason_codes,
            attributions=attributions,
            missing_signals=missing_signals,
            execution_time_ms=elapsed_ms,
            summary=(
                f"M3 fusion [{model_path_used}] score={calibrated_score:.4f}"
                f" -> {tier.value}."
                + (
                    f" Missing: {', '.join(missing_signals)}."
                    if missing_signals
                    else ""
                )
            ),
        )


# Satisfy static type checkers that ArgusM3FusionEngine implements FraudModel.
def _check_protocol(engine: ArgusM3FusionEngine) -> FraudModel:
    return engine


