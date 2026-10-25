"""What the use cases need from the outside world."""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import Protocol

from balatro_reports.domain import Report, ReportSummary, Screenshot, Status

from .dto import Player


class ReportRepository(Protocol):
    def add(self, report: Report) -> None: ...

    def get(self, report_id: str) -> Report:
        """Raises ReportNotFound."""
        ...

    def save(self, report: Report) -> None:
        """Store a triaged report (status, notes).  Raises ReportNotFound."""
        ...

    def list(self, status: Status | None, limit: int, offset: int,
             reporter: str | None = None) -> builtins.list[ReportSummary]:
        """Reports, newest first (only ``reporter``'s when given)."""
        ...

    def screenshot(self, report_id: str) -> Screenshot | None:
        """Raises ReportNotFound."""
        ...

    def count_since(self, reporter: str, since: datetime) -> int: ...


class Authenticator(Protocol):
    @property
    def required(self) -> bool: ...

    def authenticate(self, token: str | None) -> Player:
        """Raises NotAuthenticated, or AuthUnavailable."""
        ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> str: ...
