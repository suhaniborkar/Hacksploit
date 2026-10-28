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


def test_dashboard_metrics_endpoint(client, analyst_token):
    """Verifies that GET /dashboard/metrics returns calculated KPI cards."""
    # 1. Unauthenticated request rejected
    unauth = client.get("/api/v1/dashboard/metrics")
    assert unauth.status_code == 401

    # 2. Staff authenticated request succeeds
    res = client.get(
        "/api/v1/dashboard/metrics",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    cards = res.json()
    assert len(cards) == 4

    labels = [c["label"] for c in cards]
    assert "Total Applications" in labels
    assert "Verified" in labels
    assert "Pending Review" in labels
    assert "Flagged Fraud Rings" in labels

    for card in cards:
        assert "label" in card
        assert "value" in card
        assert "delta" in card
        assert "deltaLabel" in card


def test_dashboard_applications_listing_and_filtering(client, analyst_token):
    """Verifies that GET /dashboard/applications returns structured applications with filters."""
    # 1. Fetch all applications
    res = client.get(
        "/api/v1/dashboard/applications",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    apps = res.json()
    assert len(apps) >= 3

    first = apps[0]
    assert "id" in first
    assert "appId" in first
    assert "applicant" in first
    assert "status" in first
    assert "documentType" in first
    assert "document" in first
    assert "biometric" in first
    assert "risk" in first
    assert "history" in first

    # Applicant demographic structure
    applicant = first["applicant"]
    assert "fullName" in applicant
    assert "email" in applicant
    assert "phone" in applicant
    assert "city" in applicant

    # Risk score structure
    risk = first["risk"]
    assert "score" in risk
    assert "level" in risk
    assert risk["level"] in ("low", "medium", "high", "critical")

    # 2. Filter by status: verified
    verified_res = client.get(
        "/api/v1/dashboard/applications?status=verified",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert verified_res.status_code == 200
    verified_apps = verified_res.json()
    assert all(a["status"] == "verified" for a in verified_apps)

    # 3. Filter by status: flagged
    flagged_res = client.get(
        "/api/v1/dashboard/applications?status=flagged",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert flagged_res.status_code == 200
    flagged_apps = flagged_res.json()
    assert all(a["status"] == "flagged" for a in flagged_apps)

    # 4. Search by applicant name
    search_name = client.get(
        "/api/v1/dashboard/applications?search=Arjun",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert search_name.status_code == 200
    matched = search_name.json()
    assert len(matched) >= 1
    assert "Arjun Mehta" in matched[0]["applicant"]["fullName"]

    # 5. Search by ID last4
    search_id = client.get(
        "/api/v1/dashboard/applications?search=5431",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert search_id.status_code == 200
    matched_id = search_id.json()
    assert len(matched_id) >= 1


def test_dashboard_analytics_endpoint(client, analyst_token):
    """Verifies that GET /dashboard/analytics returns time-series throughput and outcome ratios."""
    res = client.get(
        "/api/v1/dashboard/analytics",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert "volumeOverTime" in data
    assert "outcomeDistribution" in data
    assert "byDocumentType" in data
    assert "fraudFlagsOverTime" in data

    # Verify outcome distribution colors and structure
    outcomes = data["outcomeDistribution"]
    assert len(outcomes) == 4
    outcome_labels = [o["label"] for o in outcomes]
    assert "Verified" in outcome_labels
    assert "Pending" in outcome_labels
    assert "Flagged" in outcome_labels
    assert "Review Req." in outcome_labels

    for item in outcomes:
        assert "label" in item
        assert "value" in item
        assert "color" in item

    # Verify document types
    docs = data["byDocumentType"]
    assert len(docs) >= 3


def test_dashboard_api_prefix_aliases(client, analyst_token):
    """Verifies that dashboard endpoints resolve identically under /api and /api/v1."""
    res1 = client.get(
        "/api/dashboard/metrics",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res1.status_code == 200

    res2 = client.get(
        "/api/dashboard/applications",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res2.status_code == 200
