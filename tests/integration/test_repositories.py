"""Both stores keep reports the same way."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from balatro_reports.domain import Report, ReportNotFound, Screenshot, Status
from balatro_reports.infrastructure.persistence import InMemoryReportRepository
from tests.samples import HISTORY, PNG, RECORDING

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(params=["memory", "postgres"])
def repo(request):
    return InMemoryReportRepository() if request.param == "memory" else request.getfixturevalue("pg")()


def make(i: int, reporter: str = "p1", **kw: object) -> Report:
    return Report(id=f"r{i}", created_at=T0 + timedelta(minutes=i), reporter=reporter, description=f"bug {i}",
                  **kw)  # type: ignore[arg-type]


def test_round_trip(repo):
    r = make(1, reporter_name="Jimbo", game_id="g1", game_version=2, history=HISTORY, client={"build": "x"},
             recording=RECORDING, screenshot=Screenshot("image/png", PNG))
    repo.add(r)
    assert repo.get("r1") == r
    assert repo.screenshot("r1") == Screenshot("image/png", PNG)
    [s] = repo.list(None, 10, 0)
    assert (s.has_screenshot, s.has_history, s.errors, s.reporter_name) == (True, True, 1, "Jimbo")
    with pytest.raises(ReportNotFound):
        repo.get("nope")
    with pytest.raises(ReportNotFound):
        repo.screenshot("nope")


def test_list_triage_and_count(repo):
    for i in range(3):
        repo.add(make(i))
    repo.add(make(9, reporter="p2"))
    assert [s.id for s in repo.list(None, 10, 0)] == ["r9", "r2", "r1", "r0"]
    assert [s.id for s in repo.list(None, 2, 1)] == ["r2", "r1"]
    assert [s.id for s in repo.list(None, 10, 0, reporter="p2")] == ["r9"]
    r = repo.get("r1")
    r.triage(T0 + timedelta(days=1), status=Status.CLOSED, notes="dup of r0")
    repo.save(r)
    assert repo.get("r1").notes == "dup of r0"
    assert [s.id for s in repo.list(Status.CLOSED, 10, 0)] == ["r1"]
    assert [s.id for s in repo.list(Status.OPEN, 10, 0)] == ["r9", "r2", "r0"]
    assert repo.count_since("p1", T0 + timedelta(minutes=1)) == 2
    assert repo.screenshot("r0") is None
    with pytest.raises(ReportNotFound):
        repo.save(make(42))


def test_postgres_migrates_once(pg):
    pg().add(make(1))
    assert pg().get("r1").description == "bug 1"
