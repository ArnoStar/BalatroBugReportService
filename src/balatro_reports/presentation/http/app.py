"""The FastAPI application."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from balatro_reports import __version__
from balatro_reports.application.use_cases import UseCases

from . import errors
from .routes import meta, reports

DESCRIPTION = """
Bug reports from the Balatro game in the browser. A report keeps what the
player says, the run's history (which rebuilds the run exactly), the game's
recording of its last minutes (API traffic with request ids, inputs, state
changes, errors) and a screenshot, so a bug can be seen again and fixed.

Players send reports (`POST /v1/reports`) and see theirs; the accounts in
`BALATRO_REPORTS_ADMINS` read and triage every report. With sign-in on, every
route but `/health` needs an access token from the identity service.
"""


def create_app(use_cases: UseCases, cors_origins: Sequence[str] = ("*",), max_body_mb: int = 20) -> FastAPI:
    app = FastAPI(title="Balatro bug reports", version=__version__, description=DESCRIPTION)
    app.state.use_cases = use_cases
    app.add_middleware(CORSMiddleware, allow_origins=list(cors_origins), allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["Location", "WWW-Authenticate"])
    errors.install(app)

    @app.middleware("http")
    async def limit_size(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        size = request.headers.get("content-length")
        if size is not None and size.isdigit() and int(size) > max_body_mb * 1024 * 1024:
            return errors.problem(413, "too_large", f"a report is at most {max_body_mb} MB")
        return await call_next(request)

    app.include_router(meta.router)
    app.include_router(reports.router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("docs")

    return app
