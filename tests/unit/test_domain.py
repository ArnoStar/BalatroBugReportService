from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from balatro_reports.domain import InvalidReport, Report, Screenshot, Status
from tests.samples import PNG

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_a_report_says_something():
    assert Report(id="r", created_at=NOW, reporter="p", description="  broke  ").description == "broke"
    for bad in ("", "   ", "x" * 5001):
        with pytest.raises(InvalidReport):
            Report(id="r", created_at=NOW, reporter="p", description=bad)
    with pytest.raises(InvalidReport):
        Report(id="r", created_at=NOW, reporter="p", description="x", game_id="g")  # without its version


def test_screenshots_are_images():
    assert Screenshot("image/png", PNG).media_type == "image/png"
    with pytest.raises(InvalidReport):
        Screenshot("image/png", b"<svg>")
    with pytest.raises(InvalidReport):
        Screenshot("image/gif", b"GIF89a")
    with pytest.raises(InvalidReport):
        Screenshot("image/jpeg", b"\xff\xd8\xff" + b"0" * (6 * 1024 * 1024))


def test_triage():
    r = Report(id="r", created_at=NOW, reporter="p", description="x")
    later = NOW + timedelta(hours=1)
    r.triage(later, status=Status.CLOSED, notes="fixed in 1a2b3c")
    assert (r.status, r.notes, r.updated_at) == (Status.CLOSED, "fixed in 1a2b3c", later)
