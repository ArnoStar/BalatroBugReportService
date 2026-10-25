# AGENTS.md

Rules for anyone (human or agent) changing this repository. `README.md`
describes the service.

## What this project is

The bug reports of Balatro in the browser. Its point is that a report is
enough to **see the bug again**: the run's history rebuilds the run exactly
(BalatroEngine is deterministic), and the game's recording replays what the
player did on it.

## Rules

1. **Keep what the game sends.** The history and the recording are kept as
   they come: the game API owns the history's format, the game the recording's
   (docs/recording.md). Don't reshape them; a new field is the game's change.
2. **A report never loses its run.** It holds a copy of the run's history, so
   deleting the run in the API doesn't matter.
3. **Players don't read reports.** Only admins (`BALATRO_REPORTS_ADMINS`)
   read and triage them; a player sees the list of their own. Never put
   another player's report, or any report's recording, in a player's answer.
4. **No secrets in reports.** The game records its API traffic without
   headers (no tokens); keep it that way on both sides.
5. **The service stands alone.** It doesn't call the game API: a report must
   be sendable when the API is broken.

## Architecture

```
domain  <-  application  <-  infrastructure, presentation  <-  bootstrap, main
```

`tests/test_architecture.py` enforces it. DTOs are
`@dataclass(frozen=True, kw_only=True)`; requests are pydantic models in
`presentation/http/schemas.py`; errors are domain exceptions with a `code`,
mapped in `presentation/http/errors.py`.

## Changes

- **A new field in a report:** the game sends it (BalatroFrontEnd,
  `features/bug-report`), the service keeps it (domain, DTO, both stores, a
  migration), the portal shows it (`pages/bug`). Test it on both stores.
- **The schema:** add a migration at the end of `MIGRATIONS`; never edit a
  released one.

## Commands

```
make install   make db   make run   make run-auth   make check
```

Before committing, `make check` must pass. ruff (line length 120), mypy --strict.
