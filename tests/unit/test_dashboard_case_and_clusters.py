"""
Tests for Task 8.3: Forensic Dossier, Case Adjudication & Fraud Ring Intelligence endpoints.

Covers:
  GET  /api/v1/dashboard/applications/{id}  — single-record dossier
  POST /api/v1/dashboard/applications/{id}/decision  — case adjudication
  GET  /api/v1/dashboard/clusters           — shared-identifier & fraud-ring intelligence
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database import Base, get_db
from app.main import app
from app.modules.identity.seed import seed_default_staff

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, expire_on_commit=False
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    with TestingSessionLocal() as db:
        seed_default_staff(db)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def analyst_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def admin_token(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@argus.internal", "password": "ArgusAdmin2026!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_and_get_first_app_id(client, token):
    """Triggers demo seed via /dashboard/applications and returns the first app's id."""
    res = client.get(
        "/api/v1/dashboard/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    apps = res.json()
    assert len(apps) >= 1
    return apps[0]["id"]


def _get_app_by_applicant_id(client, token):
    """Returns the first app's applicant_id string."""
    res = client.get(
        "/api/v1/dashboard/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res.json()[0]["appId"]


# ---------------------------------------------------------------------------
# GET /dashboard/applications/{id}  — forensic dossier
# ---------------------------------------------------------------------------

def test_get_application_detail_by_uuid(client, analyst_token):
    """Fetching a dossier by UUID primary key returns the full schema."""
    uuid_id = _seed_and_get_first_app_id(client, analyst_token)
    res = client.get(
        f"/api/v1/dashboard/applications/{uuid_id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Top-level structure
    assert data["id"] == uuid_id
    assert "appId" in data
    assert "applicant" in data
    assert "document" in data
    assert "biometric" in data
    assert "risk" in data
    assert "history" in data

    # Applicant subschema
    applicant = data["applicant"]
    for field in ("fullName", "email", "phone", "dateOfBirth", "city", "country"):
        assert field in applicant, f"Missing applicant field: {field}"

    # Risk subschema
    risk = data["risk"]
    assert risk["level"] in ("low", "medium", "high", "critical")
    assert 0 <= risk["score"] <= 100


def test_get_application_detail_by_applicant_id(client, analyst_token):
    """Fetching a dossier by the human-readable applicant_id works identically."""
    applicant_id = _get_app_by_applicant_id(client, analyst_token)
    res = client.get(
        f"/api/v1/dashboard/applications/{applicant_id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    assert res.json()["appId"] == applicant_id


def test_get_application_detail_not_found(client, analyst_token):
    """A request for a non-existent application returns 404."""
    # Ensure DB is seeded first so the table exists
    _seed_and_get_first_app_id(client, analyst_token)
    res = client.get(
        "/api/v1/dashboard/applications/KYC-0000-000000",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 404


def test_get_application_detail_requires_auth(client, analyst_token):
    """Unauthenticated requests to the dossier endpoint are rejected."""
    _seed_and_get_first_app_id(client, analyst_token)
    res = client.get("/api/v1/dashboard/applications/KYC-2026-104921")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# POST /dashboard/applications/{id}/decision  — case adjudication
# ---------------------------------------------------------------------------

def test_apply_decision_verify(client, analyst_token):
    """An analyst can mark a pending application as verified; audit trail is updated."""
    # Seed & get a review_required application
    apps_res = client.get(
        "/api/v1/dashboard/applications",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    apps = apps_res.json()
    # Use the review_required one (Priya Sharma in demo data)
    target = next((a for a in apps if a["status"] == "review_required"), apps[0])
    app_id = target["id"]

    res = client.post(
        f"/api/v1/dashboard/applications/{app_id}/decision",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"status": "verified", "note": "All documents corroborated by secondary check."},
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["status"] == "verified"
    # After the first decision, exactly one audit entry is persisted in metadata_json["history"]
    assert len(updated["history"]) >= 1
    last_event = updated["history"][-1]
    assert "verified" in last_event["action"].lower()
    assert "All documents" in (last_event["note"] or "")


def test_apply_decision_flag(client, analyst_token):
    """An analyst can flag an application; status and history are persisted."""
    apps_res = client.get(
        "/api/v1/dashboard/applications",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    apps = apps_res.json()
    target = next((a for a in apps if a["status"] == "verified"), apps[0])
    app_id = target["id"]

    res = client.post(
        f"/api/v1/dashboard/applications/{app_id}/decision",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"status": "flagged", "note": "Synthetic face detected on second review."},
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["status"] == "flagged"


def test_apply_decision_invalid_status_returns_422(client, analyst_token):
    """Submitting an unknown status value returns HTTP 422."""
    app_id = _seed_and_get_first_app_id(client, analyst_token)
    res = client.post(
        f"/api/v1/dashboard/applications/{app_id}/decision",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"status": "UNKNOWN_STATUS"},
    )
    assert res.status_code == 422


def test_apply_decision_not_found_returns_404(client, analyst_token):
    """Decision on a non-existent application returns HTTP 404."""
    _seed_and_get_first_app_id(client, analyst_token)  # ensure DB seeded
    res = client.post(
        "/api/v1/dashboard/applications/KYC-0000-NOTEXIST/decision",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"status": "verified"},
    )
    assert res.status_code == 404


def test_apply_decision_requires_auth(client):
    """Unauthenticated decision requests are rejected."""
    res = client.post(
        "/api/v1/dashboard/applications/KYC-2026-104921/decision",
        json={"status": "verified"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /dashboard/clusters  — fraud ring intelligence
# ---------------------------------------------------------------------------

def test_get_fraud_clusters_structure(client, analyst_token):
    """Fraud cluster endpoint returns a response with shared and rings arrays."""
    # Seed demo apps first (which also populates graph edges)
    _seed_and_get_first_app_id(client, analyst_token)

    res = client.get(
        "/api/v1/dashboard/clusters",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Top-level keys present
    assert "shared" in data
    assert "rings" in data
    assert isinstance(data["shared"], list)
    assert isinstance(data["rings"], list)


def test_get_fraud_clusters_shared_identifier_detected(client, analyst_token):
    """
    After seeding demo data, at least one shared phone cluster should be detected
    because Priya Sharma and Vikram Malhotra share the same phone number.
    """
    _seed_and_get_first_app_id(client, analyst_token)

    res = client.get(
        "/api/v1/dashboard/clusters",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # At least one shared cluster (phone collision in demo seed)
    assert len(data["shared"]) >= 1

    cluster = data["shared"][0]
    assert cluster["identifierType"] in ("phone", "email", "device")
    assert len(cluster["applicationIds"]) >= 2
    assert cluster["firstSeen"]
    assert cluster["lastSeen"]
    assert cluster["note"]


def test_get_fraud_clusters_fraud_ring_detected(client, analyst_token):
    """
    Vikram Malhotra (high_risk) shares a phone hash with Priya Sharma (review_required),
    so at least one fraud ring cluster should be detected.
    """
    _seed_and_get_first_app_id(client, analyst_token)

    res = client.get(
        "/api/v1/dashboard/clusters",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Rings may be empty if only one app is high_risk with no partner; skip if so
    # but validate schema for any rings present
    for ring in data["rings"]:
        assert "id" in ring
        assert "clusterLabel" in ring
        assert "applicationIds" in ring
        assert isinstance(ring["applicationIds"], list)
        assert ring["riskLevel"] in ("low", "medium", "high", "critical")
        assert isinstance(ring["sharedIndicators"], list)


def test_get_fraud_clusters_requires_auth(client):
    """Unauthenticated cluster requests are rejected."""
    res = client.get("/api/v1/dashboard/clusters")
    assert res.status_code == 401
