# The game's recording (format 1)

What BalatroFrontEnd's recorder (`src/shared/lib/recorder`) sends in a
report's `recording`. The service keeps it as it is.

```
{
  "format": 1,
  "page_started_at": "2026-10-25T20:55:06.123Z",   // when the page loaded
  "t": 40.2,           // seconds since the page loaded, when the report was made
  "dropped": 0,        // events that fell off the start (15 minutes, 40 000 events at most)
  "events": [ { "t": 12.5, "k": "...", ... } ],     // in order
  "errors": [ { "t": 39.9, "message": "...", "stack": "...", "source": "console|uncaught|rejection" } ]
}
```

`t` is in seconds since the page loaded. The errors (100 at most) are kept
apart from the events, so a report always has them.

| `k` | Fields | |
|---|---|---|
| `input` | `type` (`move`, `down`, `up`, `key`, `keyup`), `x`, `y` (game units, the room's coordinates), `button`, `key` (KeyboardEvent.key), `f` (the game frame) | the player's mouse and keys. Moves are recorded 30 times a second, every one while a button is held |
| `api` | `method`, `path`, `status`, `ms`, `rid`, `req`, `res` | a call to the game API. `rid` is the request id the API logged it under (`X-Request-ID`). Only the last 4 responses are whole; older ones are digests (version, phase, state, hand ids, jokers) |
| `action` | `phase` (`start`, `end`, `refused`), `type`, `action` (start), `version`, `error` (refused) | a player action: what was sent, and the run's version once it played |
| `run` | `id`, `version` | a run opened (new, or continued): where a replay starts |
| `state` | `state`, `stage` | G.STATE / G.STAGE changed |
| `log` | `level`, `message` | console warnings and errors |

## The replay

`/play/?report=<id>` (BalatroFrontEnd, `features/bug-report/model/replay.ts`):

1. It starts at the last `run` event of the reported run (or, if that fell
   off, the first `action` end: the screen may then differ a little).
2. The API rebuilds the run from the history's first `version` commands
   (`POST /api/v1/games/import`, admins or debug servers), and the game opens it.
3. Each recorded `input` after the start waits for as many `action` ends as
   had happened before it, then for the same delay after the last one, so a
   different API latency doesn't shift the clicks. Inputs of different
   recorded frames (`f`) go in different frames: a drag stays a drag.
4. The replay compares each action it makes with the player's and says where
   they differ.

`?report=<id>&at=<version>` only rebuilds the run at that version;
`&inputs=0` rebuilds where the recording starts, without the inputs.
