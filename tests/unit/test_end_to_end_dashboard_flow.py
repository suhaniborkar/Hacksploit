"""
End-to-End Integration Test for Project ARGUS Dashboard & Fraud Detection.
Validates:
1. Scenario seeding (Clean, AI Forgery, Synthetic Fraud Ring).
2. Staff authentication & JWT issuance.
3. Dashboard core metrics, applications queue filtering & search.
4. Full forensic dossier retrieval.
5. Fraud ring and shared identifier cluster detection.
6. Case adjudication decision with immutable audit history.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database import SessionLocal
from scripts.seed_demo_scenarios import seed_demo_scenarios


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def seeded_db():
    db = SessionLocal()
    seed_demo_scenarios(db=db)
    yield db
    db.close()


def test_auth_and_login_seeded_staff(client, seeded_db):
    """Verify that seeded staff account logs in and receives valid JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]

    # Verify /me endpoint
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "analyst@argus.internal"
    assert me_data["role"] in ("analyst", "senior_analyst")


def test_dashboard_metrics(client, seeded_db):
    """Verify that live aggregated metrics reflect seeded applications and fraud rings."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/dashboard/metrics", headers=headers)
    assert resp.status_code == 200, resp.text
    metrics = resp.json()
    assert len(metrics) == 4

    labels = {m["label"]: m["value"] for m in metrics}
    assert "Total Applications" in labels
    assert int(labels["Total Applications"]) >= 8
    assert "Flagged Fraud Rings" in labels
    assert int(labels["Flagged Fraud Rings"]) >= 1


def test_dashboard_applications_queue_and_filters(client, seeded_db):
    """Verify application queue search, status filtering, and document filtering."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. All applications
    resp = client.get("/api/v1/dashboard/applications", headers=headers)
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) >= 8

    # 2. Filter verified
    resp_verified = client.get("/api/v1/dashboard/applications?status=verified", headers=headers)
    assert resp_verified.status_code == 200
    verified_apps = resp_verified.json()
    assert any(a["applicant"]["fullName"] == "Aarav Sharma" for a in verified_apps)

    # 3. Text search
    resp_search = client.get("/api/v1/dashboard/applications?search=Vikram", headers=headers)
    assert resp_search.status_code == 200
    search_apps = resp_search.json()
    assert len(search_apps) == 1
    assert search_apps[0]["applicant"]["fullName"] == "Vikram Joshi"
    assert search_apps[0]["appId"] == "KYC-2026-3001"


def test_dashboard_forensic_dossier_detail(client, seeded_db):
    """Verify complete dossier schema with forensic flags and history."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/dashboard/applications/KYC-2026-3001", headers=headers)
    assert resp.status_code == 200, resp.text
    dossier = resp.json()

    assert dossier["appId"] == "KYC-2026-3001"
    assert dossier["applicant"]["fullName"] == "Vikram Joshi"
    assert dossier["risk"]["level"] in ("critical", "high")
    assert dossier["risk"]["score"] >= 80
    assert len(dossier["history"]) >= 2

    # Check that forensic indicators are present
    indicators = [ind["description"] for ind in dossier["risk"]["indicators"]]
    assert any("PHONE_REUSE" in ind for ind in indicators)
    assert any("DEVICE_REUSE" in ind for ind in indicators)


def test_dashboard_fraud_clusters_and_rings(client, seeded_db):
    """Verify Union-Find fraud ring detection and shared identifier clusters."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/dashboard/clusters", headers=headers)
    assert resp.status_code == 200, resp.text
    clusters = resp.json()

    assert "shared" in clusters
    assert "rings" in clusters

    # Check shared identifier clusters (phone and device)
    shared = clusters["shared"]
    phone_clusters = [c for c in shared if c["identifierType"] == "phone"]
    device_clusters = [c for c in shared if c["identifierType"] == "device"]

    assert len(phone_clusters) >= 1
    assert len(device_clusters) >= 1

    # Check that the 3 syndicate applicants are linked to the shared phone cluster
    syndicate_ids = {"KYC-2026-3001", "KYC-2026-3002", "KYC-2026-3003"}
    found_shared_phone = False
    for pc in phone_clusters:
        if syndicate_ids.issubset(set(pc["applicationIds"])):
            found_shared_phone = True
            break
    assert found_shared_phone is True

    # Check fraud rings
    rings = clusters["rings"]
    assert len(rings) >= 1
    ring_app_ids = set()
    for r in rings:
        ring_app_ids.update(r["applicationIds"])
    assert syndicate_ids.issubset(ring_app_ids)


def test_case_adjudication_decision(client, seeded_db):
    """Verify that analyst can execute an adjudication decision with audit logging."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    decision_resp = client.post(
        "/api/v1/dashboard/applications/KYC-2026-3001/decision",
        headers=headers,
        json={
            "status": "flagged",
            "note": "Analyst confirmed coordinated synthetic identity fraud ring with shared device & face reuse.",
        },
    )
    assert decision_resp.status_code == 200, decision_resp.text
    updated = decision_resp.json()
    assert updated["status"] == "flagged"

    # Verify audit event in history
    history = updated["history"]
    latest_event = history[-1]
    assert latest_event["action"] == "Decision: flagged"
    assert "Analyst confirmed coordinated synthetic identity" in (latest_event.get("note") or "")
