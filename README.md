# BalatroBugReportService

Bug reports from Balatro in the browser
([BalatroFrontEnd](https://github.com/ArnoStar/BalatroFrontEnd)), with
everything needed to **see the bug again**:

- **the player's words** and a **screenshot**;
- **the run's history**: its settings and every command, as the game API
  ([BalatroWebAPI](https://github.com/ArnoStar/BalatroWebAPI)) keeps them. The
  game engine is deterministic, so the history rebuilds the run exactly, at any
  version;
- **the game's recording** of its last minutes: every API request and response
  (with the request id the API logged it under), the player's inputs, state
  changes, actions, and the errors (see [docs/recording.md](docs/recording.md));
- the game's build, the browser, the window and the game settings.

The game sends reports from inside the game (Options > *Report a bug*, the
**F8** key, or the note that appears after an error). The developers read them
in the portal (`/bugs`) and replay them in the game: `/play/?report=<id>`
rebuilds the run where the recording starts and replays the player's inputs on
it, up to the moment of the report.

## Endpoints

The site serves the service at `/reports/` (the portal's nginx, or the dev
servers' proxies); here are its own paths. With sign-in on, every route but
`/health` needs an access token from the identity service.

| | |
|---|---|
| `GET /health` | `{status, version, auth}` |
| `GET /v1/me` | `{id, name, admin}`: who is calling, and whether they read reports |
| `POST /v1/reports` | send a report: `{description, game: {id, version}?, history?, client, recording, screenshot?}` (screenshot: a `data:image/...;base64,` URL). `201 {id, created_at}`. At most `BALATRO_REPORTS_PER_HOUR` an hour per player (`429 too_many_reports`), at most `BALATRO_REPORTS_MAX_MB` (`413 too_large`) |
| `GET /v1/reports/mine` | the caller's reports |
| `GET /v1/reports?status=open` | every report, newest first (admins) |
| `GET /v1/reports/{id}` | a whole report, with `screenshot_url` (admins) |
| `PATCH /v1/reports/{id}` | `{status: open\|closed, notes}` (admins) |
| `GET /v1/reports/{id}/screenshot` | the image (admins) |

Errors are problem details with a stable `code` (`not_admin`,
`report_not_found`, `invalid_report`, `too_many_reports`, `too_large`,
`unauthenticated`). Interactive docs at `/docs`.

**Admins** (who read and triage reports) are the accounts with the
`developer` or `admin` role (the identity service's `roles` claim; given in the
portal's `/admin`), and the account ids in `BALATRO_REPORTS_ADMINS`. Without
sign-in everyone is the same player, and an admin. `/v1/me` says who you are,
your roles, and whether you are an admin here.

## Settings

| Variable | Default | |
|---|---|---|
| `BALATRO_REPORTS_DATABASE_URL` | `postgresql://reports:reports@127.0.0.1:55434/reports` (`make db`) | PostgreSQL, or `memory` |
| `BALATRO_REPORTS_ADMINS` | none | account ids that read and triage reports, besides the developer and admin roles |
| `BALATRO_REPORTS_AUTH_JWKS_URL` | unset (sign-in off) | the identity service's `/.well-known/jwks.json` |
| `BALATRO_REPORTS_AUTH_ISSUER` | | required with the JWKS URL: the identity service's `PUBLIC_URL` |
| `BALATRO_REPORTS_AUTH_AUDIENCE` | `balatro` | |
| `BALATRO_REPORTS_PER_HOUR` | `10` | reports a player may send an hour |
| `BALATRO_REPORTS_MAX_MB` | `20` | the largest report |
| `BALATRO_REPORTS_CORS_ORIGINS` | `*` | |
| `BALATRO_REPORTS_HOST`, `BALATRO_REPORTS_PORT` | `127.0.0.1`, `8003` | for `balatro-reports` |

## Development

```
make install && make db && make run     # http://127.0.0.1:8003/docs, no sign-in
make run-auth                           # with the identity service on :8001
make check                              # tests (PostgreSQL ones on make db's database), ruff, mypy
```

`make dev` in BalatroFrontEnd runs the whole site with this service
(`ADMINS=<your account id> make dev` to read the reports there). Its
`scripts/report-e2e.mjs` checks the whole loop in a browser: it plays, reports
with F8, replays the report and compares the actions and the final run.

## Storage

PostgreSQL (`reports-db` in BalatroFrontEnd's compose file): one row per
report. The history and the environment are JSON, the recording is gzipped
JSON, the screenshot bytes. Migrations are numbered in
`infrastructure/persistence/postgres.py` and applied on start.

## Deployment

Like the other services: `.github/workflows/ci-cd.yml` runs the checks (with a
PostgreSQL service) on every push to `main` and `dev`; a push to `main` copies
the code to the server and restarts the `reports` service of BalatroFrontEnd's
compose file (once that file has it). The `DEPLOY_*` secrets are the same as in
the other repositories (BalatroFrontEnd's README, Deployment). On the server,
set `ADMINS` (and `REPORTS_DB_PASSWORD`) in BalatroFrontEnd's `.env`.

## Code

Clean architecture, as BalatroWebAPI (`AGENTS.md`):

```
src/balatro_reports/
  domain/           Report, Screenshot, Status and their rules
  application/      use cases, DTOs, ports
  infrastructure/   auth (the identity service's tokens), persistence (PostgreSQL, memory), clock and ids
  presentation/     http (FastAPI)
  bootstrap.py, config.py, main.py
```
