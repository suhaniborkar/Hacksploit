"""
Unit & Integration tests for Complete Full KYC Application Ingestion & Dynamic Verification Results.
Verifies that all form fields (demographic, address, document upload, biometrics, declarations)
are ingested, stored, screened, and analyzed by the backend.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database import Base, get_db
from app.infrastructure.storage.artifact_store import ArtifactStore, LocalDiskArtifactStore
from app.main import app
from app.modules.kyc.router import get_artifact_store, get_kyc_service
from app.modules.kyc.service import KYCApplicationService


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db, tmp_path):
    artifact_store = LocalDiskArtifactStore(base_dir=str(tmp_path / "artifacts"))

    def override_get_db():
        yield test_db

    def override_get_artifact_store() -> ArtifactStore:
        return artifact_store

    def override_get_kyc_service():
        return KYCApplicationService(db=test_db, artifact_store=artifact_store)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_artifact_store] = override_get_artifact_store
    app.dependency_overrides[get_kyc_service] = override_get_kyc_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_full_kyc_application_clean_submission(client):
    """Verifies that all frontend form fields are ingested and produce verified outcome."""
    payload = {
        "personal": {
            "fullName": "Suhani Sharma",
            "dateOfBirth": "1998-05-14",
            "nationality": "IN",
            "residencyStatus": "citizen",
            "gender": "female",
            "maritalStatus": "single",
        },
        "contact": {
            "mobile": "+919876543210",
            "email": "suhani.sharma@example.com",
        },
        "address": {
            "residential": {
                "line1": "Flat 402, Lotus Towers",
                "locality": "Koramangala",
                "city": "Bengaluru",
                "stateRegion": "Karnataka",
                "postalCode": "560034",
                "country": "IN",
            },
            "permanentSameAsResidential": True,
        },
        "document": {
            "documentType": "pan",
            "documentNumber": "ABCPS1234F",  # 'P' individual, 'S' Sharma
            "issuingCountry": "IN",
        },
        "biometric": {
            "livenessMode": "simulated",
            "livenessStatus": "simulated_passed",
        },
        "declarations": {
            "occupation": "salaried",
            "pepDeclaration": "no",
            "accuracyConsent": True,
            "privacyConsent": True,
            "verificationConsent": True,
        },
    }

    response = client.post("/api/kyc/applications", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["applicationRef"].startswith("KYC-2026-")
    assert "submittedAt" in data
    assert data["result"] is not None
    assert data["result"]["outcome"] == "verified"
    assert len(data["result"]["checks"]) == 6

    # Verify GET /result endpoint
    res_get = client.get(f"/api/kyc/applications/{data['applicationRef']}/result")
    assert res_get.status_code == 200
    res_data = res_get.json()
    assert res_data["applicationRef"] == data["applicationRef"]
    assert res_data["outcome"] == "verified"
    check_names = [c["name"] for c in res_data["checks"]]
    assert "Document Verification" in check_names
    assert "Extracted Field Consistency" in check_names
    assert "Face Comparison" in check_names
    assert "Cross-Application Identity Correlation" in check_names


def test_full_kyc_application_pan_contradiction(client):
    """Verifies that statutory contradiction in PAN triggers review or failure."""
    payload = {
        "personal": {
            "fullName": "Suhani Sharma",
            "dateOfBirth": "1998-05-14",
        },
        "contact": {
            "mobile": "+919876543211",
            "email": "suhani2@example.com",
        },
        "address": {
            "residential": {
                "line1": "Flat 101",
                "city": "Mumbai",
                "stateRegion": "Maharashtra",
                "postalCode": "400001",
            },
            "permanentSameAsResidential": True,
        },
        "document": {
            "documentType": "pan",
            "documentNumber": "ABCCS1234F",  # 'C' Company code instead of 'P' Individual
        },
        "biometric": {
            "livenessMode": "simulated",
        },
        "declarations": {
            "pepDeclaration": "no",
            "accuracyConsent": True,
            "privacyConsent": True,
            "verificationConsent": True,
        },
    }

    response = client.post("/api/kyc/applications", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["result"]["outcome"] in ("high_risk", "review_required")
    consistency_check = next(c for c in data["result"]["checks"] if c["name"] == "Extracted Field Consistency")
    assert consistency_check["status"] in ("failed", "pending")


def test_liveness_session_and_verify_endpoints(client):
    """Verifies that liveness session initialization and telemetry verification succeed."""
    # 1. Session create
    res_session = client.post("/api/kyc/liveness/session", json={"technology": "mediapipe_liveness"})
    assert res_session.status_code == 200
    session_data = res_session.json()
    assert "sessionId" in session_data
    assert session_data["provider"] == "mediapipe_local"

    # 2. Verify evidence
    res_verify = client.post(
        "/api/kyc/liveness/verify",
        data={
            "sessionId": session_data["sessionId"],
            "challengesCompleted": '["blink", "turn_left"]',
            "antiSpoof": '{"isReal": true, "status": "real", "confidencePercent": 99.4, "logitDiff": 2.5}',
        },
    )
    assert res_verify.status_code == 200
    verify_data = res_verify.json()
    assert verify_data["verified"] is True
    assert verify_data["status"] == "passed"
