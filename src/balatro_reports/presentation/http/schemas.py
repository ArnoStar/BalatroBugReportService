"""Request bodies.  (Responses are the application's dataclasses.)"""

from __future__ import annotations

import base64
import binascii
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from balatro_reports.application.dto import NewReport, Triage
from balatro_reports.domain import MAX_DESCRIPTION, Status

DATA_URL = re.compile(r"data:(image/[a-z]+);base64,(.*)", re.S)


class GameRef(BaseModel):
    id: str = Field(max_length=64)
    version: int = Field(ge=0)


class NewReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION,
                             description="what went wrong, in the player's words")
    game: GameRef | None = Field(None, description="the run the player was in, and its version")
    history: dict[str, Any] | None = Field(
        None, description="the run's history as the game API gives it (GET /api/v1/games/{id}/history): its settings "
                          "and commands, which rebuild the run exactly")
    client: dict[str, Any] = Field(default_factory=dict, description="the game's build, browser, screen, settings ...")
    recording: dict[str, Any] = Field(
        default_factory=dict, description="the game's record of the last minutes: API requests and responses, "
                                          "inputs, state changes, errors (see the game's recorder)")
    screenshot: str | None = Field(None, description="the screen, as a data URL (image/png, image/jpeg or image/webp)")

    @field_validator("screenshot")
    @classmethod
    def _data_url(cls, v: str | None) -> str | None:
        if v is not None and not DATA_URL.fullmatch(v):
            raise ValueError("a data:image/...;base64,... URL")
        return v

    def to_dto(self) -> NewReport:
        shot_type, shot = None, None
        if self.screenshot:
            m = DATA_URL.fullmatch(self.screenshot)
            assert m
            try:
                shot_type, shot = m.group(1), base64.b64decode(m.group(2), validate=True)
            except binascii.Error as e:
                raise ValueError("the screenshot is not base64") from e
        return NewReport(description=self.description, game_id=self.game.id if self.game else None,
                         game_version=self.game.version if self.game else None, history=self.history,
                         client=self.client, recording=self.recording, screenshot_type=shot_type, screenshot=shot)


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status | None = None
    notes: str | None = Field(None, max_length=10000)

    def to_dto(self) -> Triage:
        return Triage(status=self.status, notes=self.notes)
