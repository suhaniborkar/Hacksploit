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


def test_seed_staff_logins(client):
    """Verifies that all 4 default roles can log in and receive valid JWT tokens."""
    roles_and_creds = [
        ("admin@argus.internal", "ArgusAdmin2026!", "admin"),
        ("analyst@argus.internal", "ArgusAnalyst2026!", "analyst"),
        ("compliance@argus.internal", "ArgusReviewer2026!", "reviewer"),
        ("auditor@argus.internal", "ArgusAuditor2026!", "viewer"),
    ]

    for email, password, expected_role in roles_and_creds:
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert res.status_code == 200, f"Login failed for {email}: {res.text}"
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == email
        assert data["user"]["role"] == expected_role


def test_get_current_user_me(client):
    """Verifies that /auth/me returns the active authenticated user profile."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    token = login_res.json()["access_token"]

    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_info = me_res.json()
    assert user_info["email"] == "analyst@argus.internal"
    assert user_info["name"] == "Sarah Chen"
    assert user_info["role"] == "analyst"
    assert user_info["last_login_at"] is not None


def test_list_dashboard_users(client):
    """Verifies that staff can list users in the shape expected by DashboardUser."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "compliance@argus.internal", "password": "ArgusReviewer2026!"},
    )
    token = login_res.json()["access_token"]

    res = client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 4

    emails = [u["email"] for u in users]
    assert "admin@argus.internal" in emails
    assert "analyst@argus.internal" in emails
    assert "compliance@argus.internal" in emails
    assert "auditor@argus.internal" in emails

    first = users[0]
    for key in ("id", "name", "email", "role", "status", "lastLogin", "createdAt"):
        assert key in first


def test_create_user_admin_only(client):
    """Verifies that only administrators can create new staff users."""
    # 1. Admin creates user successfully
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@argus.internal", "password": "ArgusAdmin2026!"},
    )
    admin_token = admin_login.json()["access_token"]

    create_res = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Jane Investigator",
            "email": "jane@argus.internal",
            "role": "analyst",
            "password": "PasswordJane123!",
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["email"] == "jane@argus.internal"
    assert created["name"] == "Jane Investigator"
    assert created["role"] == "analyst"

    # Newly created user can immediately log in
    jane_login = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@argus.internal", "password": "PasswordJane123!"},
    )
    assert jane_login.status_code == 200

    # 2. Non-admin cannot create users
    analyst_login = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@argus.internal", "password": "ArgusAnalyst2026!"},
    )
    analyst_token = analyst_login.json()["access_token"]

    forbidden_res = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={
            "name": "Intruder User",
            "email": "intruder@argus.internal",
            "role": "reviewer",
        },
    )
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "admin_required"


def test_delete_user_admin_only(client):
    """Verifies that only administrators can delete users, and admins cannot delete themselves."""
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@argus.internal", "password": "ArgusAdmin2026!"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_id = admin_login.json()["user"]["id"]

    # Create temporary user to delete
    create_res = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Temporary User",
            "email": "temp@argus.internal",
            "role": "viewer",
        },
    )
    temp_id = create_res.json()["id"]

    # Admin tries to delete themselves -> rejected
    self_del = client.delete(
        f"/api/v1/auth/users/{admin_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert self_del.status_code == 400
    assert self_del.json()["error"]["code"] == "cannot_delete_self"

    # Admin deletes temp user -> succeeds
    del_res = client.delete(
        f"/api/v1/auth/users/{temp_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm user is gone
    users_res = client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    remaining_emails = [u["email"] for u in users_res.json()]
    assert "temp@argus.internal" not in remaining_emails


def test_api_prefix_compatibility(client):
    """Verifies that routes work seamlessly under both /api and /api/v1 prefixes."""
    res1 = client.post(
        "/api/auth/login",
        json={"email": "admin@argus.internal", "password": "ArgusAdmin2026!"},
    )
    assert res1.status_code == 200

    token = res1.json()["access_token"]
    res2 = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["email"] == "admin@argus.internal"
