"""Settings, from BALATRO_REPORTS_* environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

# the database of `make db` (BalatroFrontEnd's docker-compose.yml, service reports-db)
DEFAULT_DATABASE = "postgresql://reports:reports@127.0.0.1:55434/reports"


@dataclass(frozen=True)
class Settings:
    database: str = DEFAULT_DATABASE  # a PostgreSQL URL, or "memory" (reports are lost when the service stops)
    cors_origins: tuple[str, ...] = ("*",)
    admins: tuple[str, ...] = ()  # account ids that read and triage the reports
    reports_per_hour: int = 10  # per player
    max_body_mb: int = 20
    # sign-in with the identity service: on when the JWKS URL is set; then the issuer is required too
    auth_jwks_url: str | None = None
    auth_issuer: str | None = None
    auth_audience: str = "balatro"

    def __post_init__(self) -> None:
        if self.database != "memory" and not self.database.startswith(("postgresql://", "postgres://")):
            raise ValueError("BALATRO_REPORTS_DATABASE_URL is a postgresql:// URL or 'memory'")
        if self.auth_jwks_url and not self.auth_issuer:
            raise ValueError("BALATRO_REPORTS_AUTH_ISSUER is required with BALATRO_REPORTS_AUTH_JWKS_URL")

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> Settings:
        d = cls()

        def items(name: str) -> tuple[str, ...]:
            return tuple(x.strip() for x in env.get(name, "").split(",") if x.strip())

        return cls(
            database=env.get("BALATRO_REPORTS_DATABASE_URL") or d.database,
            cors_origins=items("BALATRO_REPORTS_CORS_ORIGINS") or d.cors_origins,
            admins=items("BALATRO_REPORTS_ADMINS"),
            reports_per_hour=int(env.get("BALATRO_REPORTS_PER_HOUR", d.reports_per_hour)),
            max_body_mb=int(env.get("BALATRO_REPORTS_MAX_MB", d.max_body_mb)),
            auth_jwks_url=env.get("BALATRO_REPORTS_AUTH_JWKS_URL") or None,
            auth_issuer=(env.get("BALATRO_REPORTS_AUTH_ISSUER") or "").rstrip("/") or None,
            auth_audience=env.get("BALATRO_REPORTS_AUTH_AUDIENCE") or d.auth_audience,
        )
