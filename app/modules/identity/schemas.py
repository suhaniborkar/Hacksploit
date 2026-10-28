import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_email_format(value: str) -> str:
    cleaned = value.strip().casefold()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", cleaned):
        raise ValueError("Invalid email format.")
    return cleaned


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        return validate_email_format(v)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        return validate_email_format(v)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class DashboardUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    lastLogin: str
    createdAt: str


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=320)
    role: str = Field(default="reviewer")
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        return validate_email_format(v)


class AuthTokens(BaseModel):
    token_type: str = "Bearer"
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    user: UserView


class KeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["kyc:read", "kyc:submit"])
    expires_at: datetime | None = None


class KeyIssued(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    raw_key: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None = None


class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        allowed = {
            "user",
            "analyst",
            "senior_analyst",
            "reviewer",
            "compliance_officer",
            "viewer",
            "auditor",
            "admin",
        }
        if v not in allowed:
            raise ValueError(f"Role must be one of: {allowed}")
        return v
