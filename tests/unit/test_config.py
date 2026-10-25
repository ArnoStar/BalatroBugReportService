from __future__ import annotations

import pytest

from balatro_reports.config import DEFAULT_DATABASE, Settings


def test_settings():
    s = Settings.from_env({"BALATRO_REPORTS_ADMINS": "a, b,", "BALATRO_REPORTS_PER_HOUR": "5"})
    assert (s.database, s.admins, s.reports_per_hour) == (DEFAULT_DATABASE, ("a", "b"), 5)
    with pytest.raises(ValueError):
        Settings.from_env({"BALATRO_REPORTS_DATABASE_URL": "reports.db"})
    with pytest.raises(ValueError):
        Settings.from_env({"BALATRO_REPORTS_AUTH_JWKS_URL": "http://x/jwks"})
