"""A bug report: what the player says, and what the game recorded.

The report keeps everything needed to see the bug again:

- ``history``: the run's settings and commands (the game API's
  ``GET /games/{id}/history`` when the report was made). The game engine is
  deterministic, so they rebuild the run exactly, at any version.
- ``recording``: the game's own record of the last minutes (its API requests
  and responses with their request ids, the player's inputs, state changes,
  errors), from which the front end can replay the inputs on that run.
- ``screenshot``: the screen when the player asked to report.

The domain checks what is true of every report; the recording and the
history are documents it keeps as they come (the game and the API own their
formats).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .errors import InvalidReport

# who files reports when the services run without sign-in (as in the game API)
ANONYMOUS_PLAYER = "local"
MAX_DESCRIPTION = 5000
MAX_NOTES = 10000
SCREENSHOT_TYPES = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff", "image/webp": b"RIFF"}
MAX_SCREENSHOT = 5 * 1024 * 1024


class Status(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class Screenshot:
    media_type: str
    data: bytes

    def __post_init__(self) -> None:
        magic = SCREENSHOT_TYPES.get(self.media_type)
        if magic is None:
            raise InvalidReport(f"a screenshot is {', '.join(SCREENSHOT_TYPES)}")
        if not self.data.startswith(magic):
            raise InvalidReport(f"the screenshot is not a {self.media_type} image")
        if len(self.data) > MAX_SCREENSHOT:
            raise InvalidReport(f"the screenshot is over {MAX_SCREENSHOT // (1024 * 1024)} MB")


@dataclass
class Report:
    id: str
    created_at: datetime
    reporter: str  # the player's account id at the identity service
    description: str
    reporter_name: str | None = None
    game_id: str | None = None  # the run the player was in
    game_version: int | None = None  # its version when the report was made
    history: Mapping[str, Any] | None = None
    client: Mapping[str, Any] = field(default_factory=dict)  # the game's version, browser, screen ...
    recording: Mapping[str, Any] = field(default_factory=dict)
    screenshot: Screenshot | None = None
    status: Status = Status.OPEN
    notes: str = ""  # the developers' notes
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.description = self.description.strip()
        if not self.description:
            raise InvalidReport("say what went wrong")
        if len(self.description) > MAX_DESCRIPTION:
            raise InvalidReport(f"the description is over {MAX_DESCRIPTION} characters")
        if (self.game_id is None) != (self.game_version is None):
            raise InvalidReport("a run is given with its version")
        if self.updated_at is None:
            self.updated_at = self.created_at

    def triage(self, at: datetime, status: Status | None = None, notes: str | None = None) -> None:
        if notes is not None:
            if len(notes) > MAX_NOTES:
                raise InvalidReport(f"the notes are over {MAX_NOTES} characters")
            self.notes = notes
        if status is not None:
            self.status = status
        self.updated_at = at


@dataclass(frozen=True)
class ReportSummary:
    id: str
    created_at: datetime
    updated_at: datetime
    reporter: str
    reporter_name: str | None
    description: str
    status: Status
    game_id: str | None
    game_version: int | None
    has_screenshot: bool
    has_history: bool
    errors: int  # errors the game recorded
