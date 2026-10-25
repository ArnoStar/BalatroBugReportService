"""Pieces of reports as the game sends them."""

from __future__ import annotations

import base64
from typing import Any

# a 1x1 PNG
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
HISTORY = {"id": "g1", "version": 2, "engine_version": "0.4.0",
           "settings": {"seed": "TESTSEED", "deck": "b_red", "stake": 1, "challenge": None, "game_speed": 1.0},
           "commands": [{"cmd": "select_blind"}, {"cmd": "play", "cards": [0, 1, 2, 3, 4]}]}
RECORDING = {"format": 1, "started_at": 12.5, "events": [{"t": 13.0, "k": "input", "type": "down", "x": 1, "y": 2}],
             "errors": [{"t": 14.0, "message": "TypeError: x is undefined", "stack": "at f (a.ts:1)"}]}


def body(**over: Any) -> dict[str, Any]:
    return {"description": "The joker vanished after I sold it", "game": {"id": "g1", "version": 2},
            "history": HISTORY, "client": {"build": "abc123", "user_agent": "test"}, "recording": RECORDING,
            "screenshot": "data:image/png;base64," + base64.b64encode(PNG).decode(), **over}
