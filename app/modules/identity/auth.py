import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import PlatformError
from app.infrastructure.database import get_db
from app.modules.identity.models import APIKey, User, ensure_utc, utcnow

_hasher = PasswordHasher()
_DUMMY_PASSWORD_HASH = _hasher.hash("argus-dummy-password-for-timing-mitigation")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return _hasher.verify(encoded_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def issue_access_token(user: User, now: datetime | None = None) -> tuple[str, datetime]:
    issued = now or utcnow()
    expires = issued + timedelta(seconds=settings.auth_access_token_seconds)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name or user.email.split("@")[0].title(),
        "role": user.role,
        "iss": settings.auth_jwt_issuer,
        "aud": settings.auth_jwt_audience,
        "iat": issued,
        "exp": expires,
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256")
    return token, expires


def new_refresh_token() -> str:
    return "argus_rfr_" + secrets.token_urlsafe(48)


def refresh_expiry(now: datetime | None = None) -> datetime:
    return (now or utcnow()) + timedelta(days=settings.auth_refresh_token_days)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_api_key() -> str:
    return "argus_key_" + secrets.token_urlsafe(36)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID | None
    api_key_id: uuid.UUID | None
    role: str
    scopes: frozenset[str]
    auth_kind: str  # "user" or "api_key"


def current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise PlatformError(401, "missing_token", "Authorization: Bearer token is required.")

    scheme, sep, token = authorization.partition(" ")
    if not sep or scheme.lower() != "bearer" or not token.strip():
        raise PlatformError(401, "invalid_header", "Authorization header must be 'Bearer <token>'.")

    token = token.strip()
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=["HS256"],
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            options={"require": ["sub", "exp", "iat", "iss", "aud", "jti", "typ"]},
        )
        if payload.get("typ") != "access":
            raise jwt.InvalidTokenError("Invalid token type.")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise PlatformError(401, "invalid_token", "Access token is invalid or expired.")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise PlatformError(401, "inactive_user", "User account is inactive or disabled.")

    return user


def current_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Principal:
    if authorization:
        user = current_user(authorization, db)
        base_scopes = {"kyc:submit", "kyc:read", "profile:manage"}
        if user.role in {"analyst", "admin"}:
            base_scopes.update({"kyc:review", "kyc:investigate", "graph:view"})
        if user.role == "admin":
            base_scopes.update({"admin:users", "admin:system"})
        return Principal(user.id, None, user.role, frozenset(base_scopes), "user")

    if x_api_key:
        hashed = hash_api_key(x_api_key)
        key = db.execute(select(APIKey).where(APIKey.key_hash == hashed)).scalar_one_or_none()
        now = utcnow()
        if not key or not key.is_active or key.revoked_at is not None or (key.expires_at and ensure_utc(key.expires_at) <= now):
            raise PlatformError(401, "invalid_api_key", "API key is invalid, revoked, or expired.")

        role = "service"
        if key.user_id:
            user = db.get(User, key.user_id)
            if not user or not user.is_active:
                raise PlatformError(401, "inactive_user", "Owner user account is disabled.")
            role = user.role

        return Principal(key.user_id, key.id, role, frozenset(key.scopes), "api_key")

    raise PlatformError(401, "credentials_required", "Provide a Bearer token or X-API-Key.")


STAFF_ROLES = {
    "admin",
    "analyst",
    "senior_analyst",
    "reviewer",
    "compliance_officer",
    "viewer",
    "auditor",
}


def require_role(*allowed_roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in allowed_roles:
            raise PlatformError(
                403,
                "forbidden_role",
                f"Role '{user.role}' does not have required permissions. Required: {allowed_roles}",
            )
        return user

    return dependency


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise PlatformError(403, "admin_required", "Administrator privileges required.")
    return user


def require_analyst(user: User = Depends(current_user)) -> User:
    if user.role not in {"analyst", "senior_analyst", "reviewer", "compliance_officer", "admin"}:
        raise PlatformError(403, "analyst_required", "Analyst or administrator privileges required.")
    return user


def require_staff(user: User = Depends(current_user)) -> User:
    if user.role not in STAFF_ROLES:
        raise PlatformError(403, "staff_required", "Staff or administrator privileges required.")
    return user
