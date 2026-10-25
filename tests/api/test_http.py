"""The service as the game and the portal use it, with sign-in."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from balatro_reports.bootstrap import build_use_cases
from balatro_reports.config import Settings
from balatro_reports.infrastructure.auth import JwtAuthenticator
from balatro_reports.presentation.http import create_app
from tests.samples import PNG, body
from tests.tokens import AUDIENCE, ISSUER, FixedKeys, token

ALICE = {"Authorization": f"Bearer {token(sub='alice', name='Alice')}"}
BOB = {"Authorization": f"Bearer {token(sub='bob', name='Bob')}"}
DEV = {"Authorization": f"Bearer {token(sub='dev', name='Dev')}"}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(database="memory", admins=("dev",), reports_per_hour=3, max_body_mb=1)
    auth = JwtAuthenticator(FixedKeys(), ISSUER, AUDIENCE)
    return TestClient(create_app(build_use_cases(settings, authenticator=auth), max_body_mb=1))


def test_a_report_from_the_game_to_the_developers(client):
    r = client.post("/v1/reports", json=body(), headers=ALICE)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert [x["id"] for x in client.get("/v1/reports/mine", headers=ALICE).json()] == [rid]
    assert client.get("/v1/reports/mine", headers=BOB).json() == []

    listed = client.get("/v1/reports", headers=DEV).json()
    assert listed[0]["id"] == rid and listed[0]["errors"] == 1 and listed[0]["reporter_name"] == "Alice"
    full = client.get(f"/v1/reports/{rid}", headers=DEV).json()
    assert full["history"]["commands"][1] == {"cmd": "play", "cards": [0, 1, 2, 3, 4]}
    assert full["recording"]["errors"][0]["message"].startswith("TypeError")
    assert full["game_id"] == "g1" and full["game_version"] == 2 and full["client"]["build"] == "abc123"
    shot = client.get(full["screenshot_url"], headers=DEV)
    assert shot.status_code == 200 and shot.headers["content-type"] == "image/png" and shot.content == PNG

    r = client.patch(f"/v1/reports/{rid}", json={"status": "closed", "notes": "fixed"}, headers=DEV)
    assert r.json()["status"] == "closed" and r.json()["notes"] == "fixed"
    assert client.get("/v1/reports?status=open", headers=DEV).json() == []


def test_only_admins_read_reports(client):
    rid = client.post("/v1/reports", json=body(), headers=ALICE).json()["id"]
    assert client.get("/v1/me", headers=ALICE).json() == {"id": "alice", "name": "Alice", "roles": [], "admin": False}
    assert client.get("/v1/me", headers=DEV).json()["admin"] is True
    for method, url in [("GET", "/v1/reports"), ("GET", f"/v1/reports/{rid}"), ("PATCH", f"/v1/reports/{rid}"),
                        ("GET", f"/v1/reports/{rid}/screenshot")]:
        r = client.request(method, url, json={} if method == "PATCH" else None, headers=ALICE)
        assert r.status_code == 403 and r.json()["code"] == "not_admin", url
    assert client.post("/v1/reports", json=body()).status_code == 401
    assert client.get("/health").json()["auth"] == "required"


def test_bad_reports(client):
    for bad in (body(description=""), body(screenshot="data:text/html;base64,PGI+"),
                body(screenshot="data:image/png;base64," + base64.b64encode(b"not a png").decode()),
                body(game={"id": "g1"}), body(extra=1)):
        r = client.post("/v1/reports", json=bad, headers=ALICE)
        assert r.status_code == 422, (r.text, bad.get("screenshot", "")[:30])
    big = body(recording={"events": ["x" * 1024] * 1100})
    r = client.post("/v1/reports", json=big, headers=ALICE)
    assert r.status_code == 413 and r.json()["code"] == "too_large"
    assert client.get("/v1/reports/nope", headers=DEV).status_code == 404


def test_a_few_reports_an_hour(client):
    for _ in range(3):
        assert client.post("/v1/reports", json=body(), headers=BOB).status_code == 201
    r = client.post("/v1/reports", json=body(), headers=BOB)
    assert r.status_code == 429 and r.json()["code"] == "too_many_reports"
    assert client.post("/v1/reports", json=body(), headers=ALICE).status_code == 201


def test_without_sign_in_everyone_is_the_developer():
    open_client = TestClient(create_app(build_use_cases(Settings(database="memory"))))
    rid = open_client.post("/v1/reports", json=body(screenshot=None, history=None, game=None)).json()["id"]
    assert open_client.get("/v1/me").json()["admin"] is True
    full = open_client.get(f"/v1/reports/{rid}").json()
    assert full["screenshot_url"] is None and full["history"] is None


def test_screenshot_urls_follow_the_mount_point(client):
    rid = client.post("/v1/reports", json=body(), headers=ALICE).json()["id"]
    full = client.get(f"/v1/reports/{rid}", headers={**DEV, "X-Forwarded-Prefix": "/reports"}).json()
    assert full["screenshot_url"] == f"/reports/v1/reports/{rid}/screenshot"


def test_the_developer_role_reads_reports(client):
    rid = client.post("/v1/reports", json=body(), headers=ALICE).json()["id"]
    for roles, ok in ((["developer"], True), (["admin"], True), (["tester"], False), (["emperor"], False)):
        who = {"Authorization": f"Bearer {token(sub='someone', roles=roles)}"}
        assert client.get("/v1/me", headers=who).json()["admin"] is ok
        assert (client.get(f"/v1/reports/{rid}", headers=who).status_code == 200) is ok, roles
