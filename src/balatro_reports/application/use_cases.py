"""The use cases.  Players file reports and see their own; admins (the
accounts in BALATRO_REPORTS_ADMINS, or everyone when the service runs
without sign-in) read and triage every report."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from balatro_reports.domain import ANONYMOUS_PLAYER, Report, ReportSummary, Screenshot, Status

from .dto import Me, NewReport, Player, Received, ReportListItem, ReportView, Triage
from .errors import NotAdmin, TooManyReports
from .ports import Authenticator, Clock, IdGenerator, ReportRepository


class Authenticate:
    def __init__(self, authenticator: Authenticator) -> None:
        self.authenticator = authenticator

    @property
    def required(self) -> bool:
        return self.authenticator.required

    def __call__(self, token: str | None) -> Player:
        return self.authenticator.authenticate(token)


class Admins:
    def __init__(self, ids: Sequence[str]) -> None:
        self.ids = frozenset(ids)

    def __contains__(self, player: object) -> bool:
        return isinstance(player, Player) and (player.id in self.ids or player.id == ANONYMOUS_PLAYER)

    def check(self, player: Player) -> None:
        if player not in self:
            raise NotAdmin()


def list_item(s: ReportSummary) -> ReportListItem:
    return ReportListItem(id=s.id, created_at=s.created_at, updated_at=s.updated_at, reporter=s.reporter,
                          reporter_name=s.reporter_name, description=s.description, status=s.status,
                          game_id=s.game_id, game_version=s.game_version, has_screenshot=s.has_screenshot,
                          has_history=s.has_history, errors=s.errors)


class WhoAmI:
    def __init__(self, admins: Admins) -> None:
        self.admins = admins

    def __call__(self, player: Player) -> Me:
        return Me(id=player.id, name=player.name, admin=player in self.admins)


class SubmitReport:
    def __init__(self, reports: ReportRepository, ids: IdGenerator, clock: Clock, per_hour: int) -> None:
        self.reports, self.ids, self.clock, self.per_hour = reports, ids, clock, per_hour

    def __call__(self, player: Player, new: NewReport) -> Received:
        now = self.clock.now()
        if self.reports.count_since(player.id, now - timedelta(hours=1)) >= self.per_hour:
            raise TooManyReports(self.per_hour)
        shot = (Screenshot(new.screenshot_type, new.screenshot)
                if new.screenshot is not None and new.screenshot_type is not None else None)
        report = Report(id=self.ids.new_id(), created_at=now, reporter=player.id, reporter_name=player.name,
                        description=new.description, game_id=new.game_id, game_version=new.game_version,
                        history=new.history, client=new.client, recording=new.recording, screenshot=shot)
        self.reports.add(report)
        return Received(id=report.id, created_at=report.created_at)


class MyReports:
    def __init__(self, reports: ReportRepository) -> None:
        self.reports = reports

    def __call__(self, player: Player, limit: int = 50, offset: int = 0) -> list[ReportListItem]:
        return [list_item(s) for s in self.reports.list(None, limit, offset, reporter=player.id)]


class ListReports:
    def __init__(self, reports: ReportRepository, admins: Admins) -> None:
        self.reports, self.admins = reports, admins

    def __call__(self, player: Player, status: Status | None = None, limit: int = 50,
                 offset: int = 0) -> list[ReportListItem]:
        self.admins.check(player)
        return [list_item(s) for s in self.reports.list(status, limit, offset)]


def view(r: Report, screenshot_url: str | None) -> ReportView:
    assert r.updated_at is not None
    return ReportView(id=r.id, created_at=r.created_at, updated_at=r.updated_at, reporter=r.reporter,
                      reporter_name=r.reporter_name, description=r.description, status=r.status, notes=r.notes,
                      game_id=r.game_id, game_version=r.game_version,
                      history=dict(r.history) if r.history is not None else None, client=dict(r.client),
                      recording=dict(r.recording), screenshot_url=screenshot_url if r.screenshot else None)


class GetReport:
    def __init__(self, reports: ReportRepository, admins: Admins) -> None:
        self.reports, self.admins = reports, admins

    def __call__(self, player: Player, report_id: str, screenshot_url: str) -> ReportView:
        self.admins.check(player)
        return view(self.reports.get(report_id), screenshot_url)


class GetScreenshot:
    def __init__(self, reports: ReportRepository, admins: Admins) -> None:
        self.reports, self.admins = reports, admins

    def __call__(self, player: Player, report_id: str) -> Screenshot | None:
        self.admins.check(player)
        return self.reports.screenshot(report_id)


class TriageReport:
    def __init__(self, reports: ReportRepository, admins: Admins, clock: Clock) -> None:
        self.reports, self.admins, self.clock = reports, admins, clock

    def __call__(self, player: Player, report_id: str, triage: Triage, screenshot_url: str) -> ReportView:
        self.admins.check(player)
        report = self.reports.get(report_id)
        report.triage(self.clock.now(), status=triage.status, notes=triage.notes)
        self.reports.save(report)
        return view(report, screenshot_url)


@dataclass(frozen=True)
class UseCases:
    authenticate: Authenticate
    who_am_i: WhoAmI
    submit: SubmitReport
    mine: MyReports
    list: ListReports
    get: GetReport
    screenshot: GetScreenshot
    triage: TriageReport
