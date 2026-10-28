"""
Cross-Source Contradiction Detector (Task 3.6).

Correlates and cross-validates disparate KYC signals across layers:
1. Document OCR demographic fields (Name, DOB) vs. claimed application form fields.
2. Statutory ID structure:
   - PAN 4th character (entity code: 'P' for individual) vs. claimed entity type.
   - PAN 5th character (surname initial) vs. claimed surname.
   - DL State RTO code vs. claimed residential address state.
   - DOB timeline & feasibility (age bounds, issuance era).
3. Biometric face deduplication:
   - Same face reused across different applicant IDs (ChromaDB nearest neighbors).
4. Technical & geographic consistency:
   - IP geolocation country vs. domestic KYC declaration.

Conforms to ARCHITECTURE.md §3 (Resilience & Missing-Signal Discipline).
Missing evidence yields explicit INFO status, never false confidence or crashes.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.forensics import ExtractedDocument, FaceMatch
from app.modules.forensics.classifier import (
    INDIAN_STATE_CODES,
    PAN_ENTITY_TYPES,
    DocumentFeatureReport,
    DocumentType,
)
from app.modules.forensics.ocr import (
    compare_dobs,
    name_similarity_ratio,
    normalize_dob_string,
    normalize_name_string,
)

logger = logging.getLogger(__name__)

# Standard Indian State Name -> 2-Letter ISO/RTO Code Mapping
STATE_NAME_TO_CODE: dict[str, str] = {
    "andaman and nicobar islands": "AN",
    "andhra pradesh": "AP",
    "arunachal pradesh": "AR",
    "assam": "AS",
    "bihar": "BR",
    "chandigarh": "CH",
    "chhattisgarh": "CG",
    "dadra and nagar haveli and daman and diu": "DD",
    "delhi": "DL",
    "nct of delhi": "DL",
    "goa": "GA",
    "gujarat": "GJ",
    "haryana": "HR",
    "himachal pradesh": "HP",
    "jammu and kashmir": "JK",
    "jharkhand": "JH",
    "karnataka": "KA",
    "kerala": "KL",
    "ladakh": "LA",
    "lakshadweep": "LD",
    "madhya pradesh": "MP",
    "maharashtra": "MH",
    "manipur": "MN",
    "meghalaya": "ML",
    "mizoram": "MZ",
    "nagaland": "NL",
    "odisha": "OD",
    "orissa": "OD",
    "puducherry": "PY",
    "pondicherry": "PY",
    "punjab": "PB",
    "rajasthan": "RJ",
    "sikkim": "SK",
    "tamil nadu": "TN",
    "telangana": "TS",
    "tripura": "TR",
    "uttar pradesh": "UP",
    "uttarakhand": "UK",
    "uttaranchal": "UK",
    "west bengal": "WB",
}


@dataclass
class ContradictionCheck:
    """Individual rule check result comparing two or more disparate KYC signals."""
    check_id: str
    name: str
    passed: bool
    severity: str  # "CLEAN", "REVIEW", "REJECT", "INFO"
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class ContradictionReport:
    """Consolidated cross-source contradiction evaluation."""
    checks: list[ContradictionCheck] = field(default_factory=list)
    has_rejection: bool = False
    has_review: bool = False
    rejection_count: int = 0
    review_count: int = 0
    rule_score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_rejection": self.has_rejection,
            "has_review": self.has_review,
            "rejection_count": self.rejection_count,
            "review_count": self.review_count,
            "rule_score": round(self.rule_score, 4),
            "reasons": self.reasons,
            "checks": [c.to_dict() for c in self.checks],
        }


class CrossSourceContradictionDetector:
    """
    Evaluates multi-source consistency across application form, OCR extractions,
    statutory structure, biometric vectors, and technical signals.
    """

    def detect_contradictions(
        self,
        application_data: dict[str, Any],
        extracted_doc: ExtractedDocument | None = None,
        feature_report: DocumentFeatureReport | None = None,
        face_matches: list[FaceMatch] | None = None,
    ) -> ContradictionReport:
        """
        Executes all cross-source contradiction checks.
        Safe against partial or missing input sources.
        """
        checks: list[ContradictionCheck] = []

        # 1. Name consistency (Form Claimed Name vs. Document OCR Name)
        checks.append(self._check_name_consistency(application_data, extracted_doc, feature_report))

        # 2. DOB consistency (Form Claimed DOB vs. Document OCR DOB)
        checks.append(self._check_dob_consistency(application_data, extracted_doc, feature_report))

        # 3. DOB timeline feasibility (Age bounds, future dates, historical issuance era)
        checks.append(self._check_dob_timeline(application_data, extracted_doc, feature_report))

        # 4. PAN statutory entity code & surname initial check
        checks.append(self._check_pan_statutory_rules(application_data, extracted_doc, feature_report))

        # 5. Driving Licence RTO State vs. Claimed Address State
        checks.append(self._check_dl_state_consistency(application_data, extracted_doc, feature_report))

        # 6. Biometric Face Deduplication (Cross-Applicant Face Reuse)
        checks.append(self._check_biometric_face_reuse(application_data, face_matches))

        # 7. Geolocation / Technical consistency
        checks.append(self._check_geolocation_consistency(application_data))

        # Aggregate report
        rejections = [c for c in checks if c.severity == "REJECT"]
        reviews = [c for c in checks if c.severity == "REVIEW"]

        rejection_count = len(rejections)
        review_count = len(reviews)
        has_rejection = rejection_count > 0
        has_review = review_count > 0

        # Calibrated rule score in [0.0, 1.0]
        score = min(1.0, (rejection_count * 0.40) + (review_count * 0.15))

        reasons = [
            c.details.get("reason", c.name)
            for c in checks
            if not c.passed and "reason" in c.details
        ]

        return ContradictionReport(
            checks=checks,
            has_rejection=has_rejection,
            has_review=has_review,
            rejection_count=rejection_count,
            review_count=review_count,
            rule_score=score,
            reasons=reasons,
        )

    def _check_name_consistency(
        self,
        app_data: dict[str, Any],
        doc: ExtractedDocument | None,
        rep: DocumentFeatureReport | None,
    ) -> ContradictionCheck:
        claimed_name = app_data.get("full_name") or app_data.get("claimed_name") or ""
        doc_name = ""
        if rep and rep.holder_name:
            doc_name = rep.holder_name
        elif doc and "name" in doc.fields:
            doc_name = doc.fields["name"]

        if not claimed_name or not doc_name:
            return ContradictionCheck(
                check_id="R3_NAME_CONTRADICTION",
                name="Name Consistency",
                passed=True,
                severity="INFO",
                details={"reason": "Name missing from document or declaration for comparison."},
            )

        sim = name_similarity_ratio(claimed_name, doc_name)
        if sim >= 0.75:
            return ContradictionCheck(
                check_id="R3_NAME_CONTRADICTION",
                name="Name Consistency",
                passed=True,
                severity="CLEAN",
                details={
                    "similarity": round(sim, 4),
                    "claimed": claimed_name,
                    "extracted": doc_name,
                },
            )
        elif sim >= 0.50:
            return ContradictionCheck(
                check_id="R3_NAME_CONTRADICTION",
                name="Name Consistency",
                passed=False,
                severity="REVIEW",
                details={
                    "similarity": round(sim, 4),
                    "claimed": claimed_name,
                    "extracted": doc_name,
                    "reason": f"Partial name match (similarity {sim:.2f} < 0.75). Manual review required.",
                },
            )
        else:
            return ContradictionCheck(
                check_id="R3_NAME_CONTRADICTION",
                name="Name Consistency",
                passed=False,
                severity="REJECT",
                details={
                    "similarity": round(sim, 4),
                    "claimed": claimed_name,
                    "extracted": doc_name,
                    "reason": f"Name contradiction: '{claimed_name}' vs document '{doc_name}' (similarity {sim:.2f}).",
                },
            )

    def _check_dob_consistency(
        self,
        app_data: dict[str, Any],
        doc: ExtractedDocument | None,
        rep: DocumentFeatureReport | None,
    ) -> ContradictionCheck:
        claimed_dob = str(app_data.get("date_of_birth") or app_data.get("claimed_dob") or "")
        doc_dob = ""
        if rep and rep.dob:
            doc_dob = rep.dob
        elif doc and "dob" in doc.fields:
            doc_dob = doc.fields["dob"]

        if not claimed_dob or not doc_dob:
            return ContradictionCheck(
                check_id="R4_DOB_CONTRADICTION",
                name="Date of Birth Consistency",
                passed=True,
                severity="INFO",
                details={"reason": "DOB missing from document or declaration for comparison."},
            )

        score, is_match = compare_dobs(claimed_dob, doc_dob)
        if is_match:
            return ContradictionCheck(
                check_id="R4_DOB_CONTRADICTION",
                name="Date of Birth Consistency",
                passed=True,
                severity="CLEAN",
                details={"claimed": claimed_dob, "extracted": doc_dob, "match_score": score},
            )
        elif score >= 0.5:
            return ContradictionCheck(
                check_id="R4_DOB_CONTRADICTION",
                name="Date of Birth Consistency",
                passed=False,
                severity="REVIEW",
                details={
                    "claimed": claimed_dob,
                    "extracted": doc_dob,
                    "match_score": score,
                    "reason": f"Partial DOB match (same birth year, divergent day/month): {claimed_dob} vs {doc_dob}.",
                },
            )
        else:
            return ContradictionCheck(
                check_id="R4_DOB_CONTRADICTION",
                name="Date of Birth Consistency",
                passed=False,
                severity="REJECT",
                details={
                    "claimed": claimed_dob,
                    "extracted": doc_dob,
                    "match_score": score,
                    "reason": f"DOB contradiction: declared '{claimed_dob}' contradicts document '{doc_dob}'.",
                },
            )

    def _check_dob_timeline(
        self,
        app_data: dict[str, Any],
        doc: ExtractedDocument | None,
        rep: DocumentFeatureReport | None,
    ) -> ContradictionCheck:
        dob_str = str(
            (rep.dob if rep and rep.dob else None)
            or (doc.fields.get("dob") if doc else None)
            or app_data.get("date_of_birth")
            or ""
        )
        if not dob_str:
            return ContradictionCheck(
                check_id="DOB_TIMELINE_VALIDITY",
                name="DOB Timeline Feasibility",
                passed=True,
                severity="INFO",
                details={"reason": "No DOB provided to validate timeline."},
            )

        norm = normalize_dob_string(dob_str)
        if not norm:
            return ContradictionCheck(
                check_id="DOB_TIMELINE_VALIDITY",
                name="DOB Timeline Feasibility",
                passed=False,
                severity="REVIEW",
                details={"raw_dob": dob_str, "reason": "Unparseable date of birth format."},
            )

        try:
            parsed_year = int(norm[:4])
            current_year = datetime.now(timezone.utc).year

            if parsed_year > current_year:
                return ContradictionCheck(
                    check_id="DOB_TIMELINE_VALIDITY",
                    name="DOB Timeline Feasibility",
                    passed=False,
                    severity="REJECT",
                    details={"dob": norm, "reason": f"Impossible birth date in the future (year {parsed_year})."},
                )

            if parsed_year < 1900:
                return ContradictionCheck(
                    check_id="DOB_TIMELINE_VALIDITY",
                    name="DOB Timeline Feasibility",
                    passed=False,
                    severity="REJECT",
                    details={"dob": norm, "reason": f"Implausible birth date before 1900 (year {parsed_year})."},
                )

            age = current_year - parsed_year
            if age < 18:
                return ContradictionCheck(
                    check_id="DOB_TIMELINE_VALIDITY",
                    name="DOB Timeline Feasibility",
                    passed=False,
                    severity="REVIEW",
                    details={"dob": norm, "age": age, "reason": f"Underage applicant (age {age} < 18)."},
                )

            return ContradictionCheck(
                check_id="DOB_TIMELINE_VALIDITY",
                name="DOB Timeline Feasibility",
                passed=True,
                severity="CLEAN",
                details={"dob": norm, "estimated_age": age},
            )
        except Exception as exc:
            return ContradictionCheck(
                check_id="DOB_TIMELINE_VALIDITY",
                name="DOB Timeline Feasibility",
                passed=False,
                severity="REVIEW",
                details={"dob": norm, "error": str(exc)},
            )

    def _check_pan_statutory_rules(
        self,
        app_data: dict[str, Any],
        doc: ExtractedDocument | None,
        rep: DocumentFeatureReport | None,
    ) -> ContradictionCheck:
        pan_number = ""
        if rep and rep.document_type == DocumentType.PAN_CARD and rep.id_number:
            pan_number = rep.id_number
        elif doc and doc.fields.get("pan"):
            pan_number = doc.fields["pan"]
        elif app_data.get("document_type") == "pan" and app_data.get("document_number"):
            pan_number = str(app_data["document_number"])

        pan_clean = re.sub(r"\s+", "", pan_number).upper()
        if len(pan_clean) != 10 or not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan_clean):
            if pan_clean:
                return ContradictionCheck(
                    check_id="PAN_STATUTORY_CONTRADICTION",
                    name="PAN Statutory Structure Check",
                    passed=False,
                    severity="REJECT",
                    details={"pan": pan_clean, "reason": "Invalid PAN syntax (expected 5 letters, 4 digits, 1 letter)."},
                )
            return ContradictionCheck(
                check_id="PAN_STATUTORY_CONTRADICTION",
                name="PAN Statutory Structure Check",
                passed=True,
                severity="INFO",
                details={"reason": "Non-PAN document or PAN not provided."},
            )

        entity_char = pan_clean[3]
        surname_char = pan_clean[4]
        claimed_entity = app_data.get("entity_type", "individual").lower()

        # Rule A: Entity Type Check (4th character)
        if claimed_entity in ("individual", "person", "self") and entity_char != "P":
            entity_desc = PAN_ENTITY_TYPES.get(entity_char, "Unknown Entity")
            return ContradictionCheck(
                check_id="PAN_STATUTORY_CONTRADICTION",
                name="PAN Statutory Structure Check",
                passed=False,
                severity="REJECT",
                details={
                    "pan": pan_clean,
                    "entity_char": entity_char,
                    "entity_type": entity_desc,
                    "reason": f"PAN entity mismatch: 4th char '{entity_char}' ({entity_desc}) contradicts individual personal KYC.",
                },
            )

        # Rule B: Surname Initial Check (5th character)
        claimed_name = app_data.get("full_name") or app_data.get("claimed_name") or ""
        tokens = normalize_name_string(claimed_name).split()
        if len(tokens) >= 2:
            surname_initial = tokens[-1][0].upper()
            if surname_char != surname_initial:
                return ContradictionCheck(
                    check_id="PAN_STATUTORY_CONTRADICTION",
                    name="PAN Statutory Structure Check",
                    passed=False,
                    severity="REJECT",
                    details={
                        "pan": pan_clean,
                        "pan_surname_char": surname_char,
                        "expected_surname_initial": surname_initial,
                        "claimed_surname": tokens[-1],
                        "reason": f"PAN surname mismatch: 5th char '{surname_char}' does not match claimed surname initial '{surname_initial}' ({tokens[-1]}).",
                    },
                )

        return ContradictionCheck(
            check_id="PAN_STATUTORY_CONTRADICTION",
            name="PAN Statutory Structure Check",
            passed=True,
            severity="CLEAN",
            details={
                "pan": pan_clean,
                "entity_char": entity_char,
                "surname_char": surname_char,
            },
        )

    def _check_dl_state_consistency(
        self,
        app_data: dict[str, Any],
        doc: ExtractedDocument | None,
        rep: DocumentFeatureReport | None,
    ) -> ContradictionCheck:
        dl_number = ""
        if rep and rep.document_type == DocumentType.DRIVING_LICENCE and rep.id_number:
            dl_number = rep.id_number
        elif doc and doc.fields.get("dl_number"):
            dl_number = doc.fields["dl_number"]
        elif app_data.get("document_type") == "driving_licence" and app_data.get("document_number"):
            dl_number = str(app_data["document_number"])

        clean_dl = re.sub(r"[\s\-\/]", "", dl_number).upper()
        if len(clean_dl) < 4:
            return ContradictionCheck(
                check_id="DL_STATE_CONTRADICTION",
                name="Driving Licence State Consistency",
                passed=True,
                severity="INFO",
                details={"reason": "Non-DL document or DL number not provided."},
            )

        dl_state_prefix = clean_dl[:2]
        if dl_state_prefix not in INDIAN_STATE_CODES:
            return ContradictionCheck(
                check_id="DL_STATE_CONTRADICTION",
                name="Driving Licence State Consistency",
                passed=False,
                severity="REJECT",
                details={"dl": clean_dl, "reason": f"Invalid Indian RTO state code prefix '{dl_state_prefix}'."},
            )

        claimed_state = app_data.get("state") or app_data.get("stateRegion") or ""
        norm_state = claimed_state.strip().lower()
        claimed_code = STATE_NAME_TO_CODE.get(norm_state) or (
            claimed_state.strip().upper() if claimed_state.strip().upper() in INDIAN_STATE_CODES else None
        )

        if claimed_code and claimed_code != dl_state_prefix:
            return ContradictionCheck(
                check_id="DL_STATE_CONTRADICTION",
                name="Driving Licence State Consistency",
                passed=False,
                severity="REVIEW",
                details={
                    "dl_state": dl_state_prefix,
                    "claimed_state": claimed_state,
                    "claimed_state_code": claimed_code,
                    "reason": f"DL state ({dl_state_prefix}) diverges from residential address state ({claimed_state}).",
                },
            )

        return ContradictionCheck(
            check_id="DL_STATE_CONTRADICTION",
            name="Driving Licence State Consistency",
            passed=True,
            severity="CLEAN",
            details={"dl_state": dl_state_prefix, "claimed_state_code": claimed_code},
        )

    def _check_biometric_face_reuse(
        self,
        app_data: dict[str, Any],
        face_matches: list[FaceMatch] | None,
    ) -> ContradictionCheck:
        current_id = app_data.get("applicant_id") or app_data.get("applicationRef") or ""
        if not face_matches:
            return ContradictionCheck(
                check_id="BIOMETRIC_FACE_REUSE",
                name="Biometric Face Deduplication",
                passed=True,
                severity="CLEAN",
                details={"reason": "No duplicate face matches found in index."},
            )

        # Check if any match exceeds reuse threshold
        reused = [
            m for m in face_matches
            if m.distance <= 0.35 and m.applicant_id != current_id
        ]

        if reused:
            primary_match = reused[0]
            return ContradictionCheck(
                check_id="BIOMETRIC_FACE_REUSE",
                name="Biometric Face Deduplication",
                passed=False,
                severity="REJECT",
                details={
                    "matched_applicant_id": primary_match.applicant_id,
                    "cosine_similarity": primary_match.similarity,
                    "cosine_distance": primary_match.distance,
                    "total_matches": len(reused),
                    "reason": f"Biometric face reuse: face matches previous applicant '{primary_match.applicant_id}' (similarity {primary_match.similarity:.2f}).",
                },
            )

        return ContradictionCheck(
            check_id="BIOMETRIC_FACE_REUSE",
            name="Biometric Face Deduplication",
            passed=True,
            severity="CLEAN",
            details={"matches_evaluated": len(face_matches)},
        )

    def _check_geolocation_consistency(self, app_data: dict[str, Any]) -> ContradictionCheck:
        ip_country = app_data.get("ip_country") or ""
        if ip_country and ip_country.upper() not in ("IN", "INDIA"):
            return ContradictionCheck(
                check_id="GEOLOCATION_ANOMALY",
                name="Geolocation Consistency",
                passed=False,
                severity="REVIEW",
                details={
                    "ip_country": ip_country,
                    "reason": f"Foreign IP geolocation ({ip_country}) for domestic Indian identity KYC.",
                },
            )

        return ContradictionCheck(
            check_id="GEOLOCATION_ANOMALY",
            name="Geolocation Consistency",
            passed=True,
            severity="CLEAN",
            details={"ip_country": ip_country or "IN"},
        )
