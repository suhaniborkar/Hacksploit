"""
Unit tests for app.modules.forensics.contradiction (Task 3.6).
"""

from __future__ import annotations

import pytest

from app.core.forensics import ExtractedDocument, FaceMatch
from app.modules.forensics.contradiction import CrossSourceContradictionDetector


@pytest.fixture
def detector() -> CrossSourceContradictionDetector:
    return CrossSourceContradictionDetector()


class TestCrossSourceContradictionDetector:
    def test_clean_matching_application(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {
            "applicant_id": "app_clean_1",
            "full_name": "Vikram Mehta",
            "date_of_birth": "1992-05-15",
            "document_type": "pan",
            "document_number": "ABCPM1234F",  # 4th P=Person, 5th M=Mehta
            "state": "Maharashtra",
            "ip_country": "IN",
        }
        report = detector.detect_contradictions(
            application_data=app_data,
            face_matches=[],
        )
        assert report.has_rejection is False
        assert report.has_review is False
        assert report.rejection_count == 0
        assert report.review_count == 0
        assert report.rule_score == 0.0

    def test_name_contradiction_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"full_name": "Vikram Mehta"}
        doc = ExtractedDocument(
            raw_text="Identity Card",
            fields={"name": "Suresh Sharma"},
        )
        report = detector.detect_contradictions(application_data=app_data, extracted_doc=doc)
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "R3_NAME_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REJECT"

    def test_name_partial_match_review(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"full_name": "Vikramaditya Mehta"}
        doc = ExtractedDocument(
            raw_text="Card",
            fields={"name": "Vikram Mehta"},
        )
        report = detector.detect_contradictions(application_data=app_data, extracted_doc=doc)
        check = next(c for c in report.checks if c.check_id == "R3_NAME_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REVIEW"

    def test_dob_contradiction_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"date_of_birth": "1992-05-15"}
        doc = ExtractedDocument(
            raw_text="Card",
            fields={"dob": "1985-11-20"},
        )
        report = detector.detect_contradictions(application_data=app_data, extracted_doc=doc)
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "R4_DOB_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REJECT"

    def test_dob_partial_match_review(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"date_of_birth": "1992-05-15"}
        doc = ExtractedDocument(
            raw_text="Card",
            fields={"dob": "1992-12-01"},
        )
        report = detector.detect_contradictions(application_data=app_data, extracted_doc=doc)
        check = next(c for c in report.checks if c.check_id == "R4_DOB_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REVIEW"

    def test_dob_future_date_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"date_of_birth": "2050-01-01"}
        report = detector.detect_contradictions(application_data=app_data)
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "DOB_TIMELINE_VALIDITY")
        assert check.passed is False
        assert check.severity == "REJECT"

    def test_dob_underage_review(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"date_of_birth": "2015-06-10"}
        report = detector.detect_contradictions(application_data=app_data)
        check = next(c for c in report.checks if c.check_id == "DOB_TIMELINE_VALIDITY")
        assert check.passed is False
        assert check.severity == "REVIEW"

    def test_pan_company_entity_for_individual_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {
            "full_name": "Ramesh Kumar",
            "document_type": "pan",
            "document_number": "ABC C K 1234 F",  # 4th char is C (Company)
            "entity_type": "individual",
        }
        report = detector.detect_contradictions(application_data=app_data)
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "PAN_STATUTORY_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REJECT"
        assert "contradicts individual personal KYC" in check.details["reason"]

    def test_pan_surname_mismatch_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {
            "full_name": "Ramesh Kumar Sharma",
            "document_type": "pan",
            "document_number": "ABCPK1234F",  # 5th char is K, but surname is Sharma (S)
            "entity_type": "individual",
        }
        report = detector.detect_contradictions(application_data=app_data)
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "PAN_STATUTORY_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REJECT"
        assert "PAN surname mismatch" in check.details["reason"]

    def test_dl_state_mismatch_review(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {
            "document_type": "driving_licence",
            "document_number": "MH1420110062821",  # MH = Maharashtra
            "state": "Karnataka",  # KA
        }
        report = detector.detect_contradictions(application_data=app_data)
        check = next(c for c in report.checks if c.check_id == "DL_STATE_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REVIEW"

    def test_dl_invalid_prefix_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {
            "document_type": "driving_licence",
            "document_number": "ZZ1420110062821",  # Invalid state prefix
            "state": "Maharashtra",
        }
        report = detector.detect_contradictions(application_data=app_data)
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "DL_STATE_CONTRADICTION")
        assert check.passed is False
        assert check.severity == "REJECT"

    def test_biometric_face_reuse_reject(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"applicant_id": "app_new_99"}
        matches = [
            FaceMatch(
                applicant_id="app_existing_42",
                distance=0.08,
                similarity=0.92,
            )
        ]
        report = detector.detect_contradictions(
            application_data=app_data,
            face_matches=matches,
        )
        assert report.has_rejection is True
        check = next(c for c in report.checks if c.check_id == "BIOMETRIC_FACE_REUSE")
        assert check.passed is False
        assert check.severity == "REJECT"
        assert "app_existing_42" in check.details["reason"]

    def test_foreign_ip_anomaly_review(self, detector: CrossSourceContradictionDetector) -> None:
        app_data = {"ip_country": "RU"}
        report = detector.detect_contradictions(application_data=app_data)
        check = next(c for c in report.checks if c.check_id == "GEOLOCATION_ANOMALY")
        assert check.passed is False
        assert check.severity == "REVIEW"

    def test_missing_data_safe(self, detector: CrossSourceContradictionDetector) -> None:
        report = detector.detect_contradictions(application_data={})
        assert report.has_rejection is False
        assert report.rejection_count == 0
        assert report.rule_score == 0.0
        assert len(report.checks) >= 5
