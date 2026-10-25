"""What both stores derive from a report the same way."""

from __future__ import annotations

from typing import Any

from balatro_reports.domain import Report, ReportSummary


def error_count(recording: Any) -> int:
    """The errors the game recorded (``recording.errors``, a list)."""
    errors = recording.get("errors") if isinstance(recording, dict) else None
    return len(errors) if isinstance(errors, list) else 0


def summary(r: Report) -> ReportSummary:
    assert r.updated_at is not None
    return ReportSummary(id=r.id, created_at=r.created_at, updated_at=r.updated_at, reporter=r.reporter,
                         reporter_name=r.reporter_name, description=r.description, status=r.status,
                         game_id=r.game_id, game_version=r.game_version, has_screenshot=r.screenshot is not None,
                         has_history=r.history is not None, errors=error_count(r.recording))
