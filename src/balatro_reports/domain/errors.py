"""Errors of the domain.  Each has a stable ``code`` that clients can rely on."""

from __future__ import annotations


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidReport(DomainError):
    code = "invalid_report"


class ReportNotFound(DomainError):
    code = "report_not_found"

    def __init__(self, report_id: str) -> None:
        super().__init__(f"no report {report_id!r}")
        self.report_id = report_id
