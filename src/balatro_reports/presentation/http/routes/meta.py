"""Health, and who is calling."""

from __future__ import annotations

from fastapi import APIRouter

from balatro_reports import __version__
from balatro_reports.application.dto import Me
from balatro_reports.presentation.http.deps import CurrentPlayer, Uses

router = APIRouter(tags=["meta"])


@router.get("/health", summary="Is the service up")
def health(uses: Uses) -> dict[str, str]:
    return {"status": "ok", "version": __version__, "auth": "required" if uses.authenticate.required else "off"}


@router.get("/v1/me", response_model=Me, summary="Who is calling, and whether they may read reports")
def me(player: CurrentPlayer, uses: Uses) -> Me:
    return uses.who_am_i(player)
