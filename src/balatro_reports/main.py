"""``uvicorn balatro_reports.main:app`` (or the ``balatro-reports`` command).
Settings come from BALATRO_REPORTS_* environment variables (see config.py)."""

from __future__ import annotations

import logging
import os

from .bootstrap import build_use_cases
from .config import Settings
from .presentation.http import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = Settings.from_env()
app = create_app(build_use_cases(settings), settings.cors_origins, settings.max_body_mb)


def run() -> None:
    import uvicorn

    uvicorn.run("balatro_reports.main:app", host=os.environ.get("BALATRO_REPORTS_HOST", "127.0.0.1"),
                port=int(os.environ.get("BALATRO_REPORTS_PORT", "8003")))
