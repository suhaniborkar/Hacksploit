import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.auth import hash_password
from app.modules.identity.models import User, utcnow


DEFAULT_STAFF_ACCOUNTS = [
    {
        "email": "admin@argus.internal",
        "name": "Administrator",
        "role": "admin",
        "password": "ArgusAdmin2026!",
    },
    {
        "email": "analyst@argus.internal",
        "name": "Sarah Chen",
        "role": "analyst",
        "password": "ArgusAnalyst2026!",
    },
    {
        "email": "compliance@argus.internal",
        "name": "Marcus Vance",
        "role": "reviewer",
        "password": "ArgusReviewer2026!",
    },
    {
        "email": "auditor@argus.internal",
        "name": "Elena Rostova",
        "role": "viewer",
        "password": "ArgusAuditor2026!",
    },
]


def normalize_role(role: str) -> str:
    """Normalize internal role names to dashboard roles: admin, analyst, reviewer, viewer."""
    role_lower = role.strip().lower()
    if role_lower in ("admin", "administrator"):
        return "admin"
    if role_lower in ("analyst", "senior_analyst", "fraud_analyst"):
        return "analyst"
    if role_lower in ("reviewer", "compliance_officer", "compliance", "officer"):
        return "reviewer"
    if role_lower in ("viewer", "auditor", "read_only"):
        return "viewer"
    return "viewer"


def format_last_login(dt: datetime | None) -> str:
    """Formats last login datetime for frontend display."""
    if not dt:
        return "Never"
    diff = datetime.now(timezone.utc) - (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        mins = seconds // 60
        return f"{mins} min ago" if mins == 1 else f"{mins} mins ago"
    if seconds < 86400:
        hrs = seconds // 3600
        return f"{hrs} hour ago" if hrs == 1 else f"{hrs} hours ago"
    days = seconds // 86400
    return f"{days} day ago" if days == 1 else f"{days} days ago"


def to_dashboard_user_dict(user: User) -> dict:
    """Serializes a User instance into the exact shape required by DashboardUser."""
    return {
        "id": str(user.id),
        "name": user.name or user.email.split("@")[0].replace(".", " ").title(),
        "email": user.email,
        "role": normalize_role(user.role),
        "status": "active" if user.is_active else "inactive",
        "lastLogin": format_last_login(user.last_login_at),
        "createdAt": (user.created_at if user.created_at else utcnow()).strftime("%Y-%m-%d"),
    }


def seed_default_staff(db: Session) -> list[User]:
    """
    Idempotently seeds standard staff accounts for Project ARGUS.
    Returns the list of seeded staff users.
    """
    seeded_users: list[User] = []
    for account in DEFAULT_STAFF_ACCOUNTS:
        existing = db.execute(select(User).where(User.email == account["email"])).scalar_one_or_none()
        if existing is None:
            new_user = User(
                id=uuid.uuid4(),
                email=account["email"],
                name=account["name"],
                password_hash=hash_password(account["password"]),
                role=account["role"],
                is_active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(new_user)
            seeded_users.append(new_user)
        else:
            # Ensure name and active status are set
            if not existing.name:
                existing.name = account["name"]
            existing.is_active = True
            seeded_users.append(existing)

    db.commit()
    for u in seeded_users:
        db.refresh(u)
    return seeded_users
