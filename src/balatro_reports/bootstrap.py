"""The composition root: picks the adapters and builds the use cases."""

from __future__ import annotations

import logging

from .application.ports import Authenticator, Clock, IdGenerator, ReportRepository
from .application.use_cases import (
    Admins,
    Authenticate,
    GetReport,
    GetScreenshot,
    ListReports,
    MyReports,
    SubmitReport,
    TriageReport,
    UseCases,
    WhoAmI,
)
from .config import Settings
from .infrastructure.auth import AnonymousAuthenticator, JwtAuthenticator
from .infrastructure.persistence import InMemoryReportRepository, PostgresReportRepository
from .infrastructure.system import SystemClock, UuidGenerator

log = logging.getLogger(__name__)


def build_authenticator(settings: Settings) -> Authenticator:
    if settings.auth_jwks_url and settings.auth_issuer:
        return JwtAuthenticator.from_jwks_url(settings.auth_jwks_url, settings.auth_issuer, settings.auth_audience)
    log.warning("sign-in is off (BALATRO_REPORTS_AUTH_JWKS_URL is not set): every caller is the same player, an admin")
    return AnonymousAuthenticator()


def build_repository(settings: Settings) -> ReportRepository:
    if settings.database == "memory":
        return InMemoryReportRepository()
    return PostgresReportRepository(settings.database)


def build_use_cases(settings: Settings, reports: ReportRepository | None = None, ids: IdGenerator | None = None,
                    clock: Clock | None = None, authenticator: Authenticator | None = None) -> UseCases:
    reports = reports if reports is not None else build_repository(settings)
    ids = ids or UuidGenerator()
    clock = clock or SystemClock()
    admins = Admins(settings.admins)
    return UseCases(
        authenticate=Authenticate(authenticator or build_authenticator(settings)),
        who_am_i=WhoAmI(admins),
        submit=SubmitReport(reports, ids, clock, settings.reports_per_hour),
        mine=MyReports(reports),
        list=ListReports(reports, admins),
        get=GetReport(reports, admins),
        screenshot=GetScreenshot(reports, admins),
        triage=TriageReport(reports, admins, clock),
    )
