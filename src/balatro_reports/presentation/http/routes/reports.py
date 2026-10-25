"""Bug reports: players send them and see their own; admins read and triage them."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from balatro_reports.application.dto import Received, ReportListItem, ReportView
from balatro_reports.domain import InvalidReport, Status
from balatro_reports.presentation.http.deps import CurrentPlayer, Uses
from balatro_reports.presentation.http.schemas import NewReportRequest, TriageRequest

router = APIRouter(prefix="/v1/reports", tags=["reports"])


def screenshot_url(request: Request, report_id: str) -> str:
    # relative to where the service is mounted (the site serves it at /reports/)
    prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
    return f"{prefix}/v1/reports/{report_id}/screenshot"


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Received, summary="Report a bug")
def submit(body: NewReportRequest, player: CurrentPlayer, uses: Uses) -> Received:
    """What went wrong, with the game's recording, the run's history and a
    screenshot. At most a few reports an hour per player (``429``)."""
    try:
        new = body.to_dto()
    except ValueError as e:
        raise InvalidReport(str(e)) from e
    return uses.submit(player, new)


@router.get("/mine", response_model=list[ReportListItem], summary="The caller's reports, newest first")
def mine(player: CurrentPlayer, uses: Uses, limit: Annotated[int, Query(ge=1, le=200)] = 50,
         offset: Annotated[int, Query(ge=0)] = 0) -> list[ReportListItem]:
    return uses.mine(player, limit, offset)


@router.get("", response_model=list[ReportListItem], summary="Every report, newest first (admins)")
def list_reports(player: CurrentPlayer, uses: Uses, status: Status | None = None,
                 limit: Annotated[int, Query(ge=1, le=200)] = 50,
                 offset: Annotated[int, Query(ge=0)] = 0) -> list[ReportListItem]:
    return uses.list(player, status, limit, offset)


@router.get("/{report_id}", response_model=ReportView, summary="A whole report (admins)")
def get_report(report_id: str, player: CurrentPlayer, uses: Uses, request: Request) -> ReportView:
    return uses.get(player, report_id, screenshot_url(request, report_id))


@router.patch("/{report_id}", response_model=ReportView, summary="Close, reopen or annotate a report (admins)")
def triage(report_id: str, body: TriageRequest, player: CurrentPlayer, uses: Uses, request: Request) -> ReportView:
    return uses.triage(player, report_id, body.to_dto(), screenshot_url(request, report_id))


@router.get("/{report_id}/screenshot", summary="The report's screenshot (admins)",
            responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}, 404: {}})
def screenshot(report_id: str, player: CurrentPlayer, uses: Uses) -> Response:
    shot = uses.screenshot(player, report_id)
    if shot is None:
        return Response(status_code=404)
    return Response(shot.data, media_type=shot.media_type, headers={"Cache-Control": "private, max-age=3600"})
