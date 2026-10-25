"""Errors as RFC 9457 problem details: ``{type, title, status, detail, code}``."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from balatro_reports.application.errors import AuthUnavailable, NotAdmin, NotAuthenticated, TooManyReports
from balatro_reports.domain import DomainError, InvalidReport, ReportNotFound

log = logging.getLogger(__name__)

STATUS: list[tuple[type[DomainError], int]] = [
    (ReportNotFound, 404),
    (InvalidReport, 422),
    (NotAdmin, 403),
    (TooManyReports, 429),
    (NotAuthenticated, 401),
    (AuthUnavailable, 503),
]
TITLES = {401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 413: "Content Too Large",
          422: "Unprocessable Content", 429: "Too Many Requests", 500: "Internal Server Error",
          503: "Service Unavailable"}


def problem(status: int, code: str, detail: str, headers: dict[str, str] | None = None, **extra: Any) -> JSONResponse:
    body = {"type": f"https://balatro-reports/errors/{code}", "title": TITLES.get(status, "Error"), "status": status,
            "detail": detail, "code": code, **extra}
    return JSONResponse(body, status_code=status, headers=headers, media_type="application/problem+json")


def install(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = next((s for cls, s in STATUS if isinstance(exc, cls)), 400)
        headers = {"WWW-Authenticate": 'Bearer error="invalid_token"'} if isinstance(exc, NotAuthenticated) else None
        return problem(status, exc.code, exc.message, headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return problem(422, "invalid_request", "the request doesn't match the schema", errors=errors)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unexpected error in %s %s", request.method, request.url.path, exc_info=exc)
        return problem(500, "internal_error", "unexpected server error")
