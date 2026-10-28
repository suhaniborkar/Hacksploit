from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "ARGUS KYC Intelligence Platform"
    app_env: str = "development"
    app_log_level: str = "INFO"
    app_secret_key: str = "argus_dev_secret_hmac_pii_key_min_32_chars_123456"

    # Database: Supports PostgreSQL (via psycopg2) and SQLite (for unit tests)
    database_url: str = "postgresql+psycopg2://lab:local_dev_only@localhost:5432/backend_lab"

    # Artifact / Document Binary Storage
    artifact_storage_dir: str = "artifacts_data"
    artifact_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)  # 10 MB default
    allowed_artifact_mime_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    ]
    chroma_persist_dir: str = "artifacts_data/chroma_face_db"

    # Identity & JWT Authentication
    auth_jwt_secret: str = "argus_jwt_secret_dev_only_min_32_chars_abcdef123456"
    auth_jwt_issuer: str = "argus-kyc-platform"
    auth_jwt_audience: str = "argus-kyc-api"
    auth_access_token_seconds: int = Field(default=600, ge=60, le=3600)
    auth_refresh_token_days: int = Field(default=14, ge=1, le=90)

    # Worker Settings (Zero-Broker Lease Pipeline)
    worker_id: str = ""
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0, le=30)
    worker_concurrency: int = Field(default=2, ge=1, le=16)
    worker_lease_seconds: int = Field(default=45, ge=5, le=600)
    worker_execution_timeout_seconds: int = Field(default=30, ge=1, le=300)
    worker_max_attempts: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def validate_timings(self):
        if self.worker_lease_seconds <= self.worker_execution_timeout_seconds:
            raise ValueError("worker_lease_seconds must exceed worker_execution_timeout_seconds")
        # Ensure database_url has a compatible driver
        if self.database_url.startswith("postgresql+psycopg://"):
            try:
                import psycopg  # noqa: F401
            except ImportError:
                # Fall back to psycopg2 driver if psycopg3 is not present
                self.database_url = self.database_url.replace(
                    "postgresql+psycopg://", "postgresql+psycopg2://", 1
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()