"""What the use cases take and return: plain dataclasses, serialized as they
are by the HTTP layer (field names are the JSON names)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from balatro_reports.domain import Status


@dataclass(frozen=True, kw_only=True)
class Player:
    """Who is calling: the identity service's account id and display name, or
    the anonymous player when the service runs without sign-in."""

    id: str
    name: str | None = None


@dataclass(frozen=True, kw_only=True)
class Me:
    id: str
    name: str | None
    admin: bool  # may read and triage every report


@dataclass(frozen=True, kw_only=True)
class NewReport:
    description: str
    game_id: str | None = None
    game_version: int | None = None
    history: dict[str, Any] | None = None
    client: dict[str, Any] = field(default_factory=dict)
    recording: dict[str, Any] = field(default_factory=dict)
    screenshot_type: str | None = None
    screenshot: bytes | None = None


@dataclass(frozen=True, kw_only=True)
class Received:
    id: str
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class ReportListItem:
    id: str
    created_at: datetime
    updated_at: datetime
    reporter: str
    reporter_name: str | None
    description: str
    status: Status
    game_id: str | None
    game_version: int | None
    has_screenshot: bool
    has_history: bool
    errors: int  # errors the game recorded before the report


@dataclass(frozen=True, kw_only=True)
class ReportView:
    """A whole report (the screenshot is at ``screenshot_url``)."""

    id: str
    created_at: datetime
    updated_at: datetime
    reporter: str
    reporter_name: str | None
    description: str
    status: Status
    notes: str
    game_id: str | None
    game_version: int | None
    history: dict[str, Any] | None  # the run's settings and commands (the game API's history)
    client: dict[str, Any]
    recording: dict[str, Any]
    screenshot_url: str | None


@dataclass(frozen=True, kw_only=True)
class Triage:
    status: Status | None = None
    notes: str | None = None
