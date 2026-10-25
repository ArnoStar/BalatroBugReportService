"""Errors of the application layer."""

from __future__ import annotations

from balatro_reports.domain import DomainError


class NotAuthenticated(DomainError):
    """No access token, or one the identity service didn't sign (or expired)."""

    code = "unauthenticated"


class AuthUnavailable(DomainError):
    """The identity service's keys couldn't be fetched to check a token."""

    code = "auth_unavailable"


class NotAdmin(DomainError):
    code = "not_admin"

    def __init__(self) -> None:
        super().__init__("reading reports is for the developers (the developer role)")


class TooManyReports(DomainError):
    code = "too_many_reports"

    def __init__(self, limit: int) -> None:
        super().__init__(f"at most {limit} reports an hour: thank you, try again a bit later")
