"""Reports stored in PostgreSQL: one row per report.

The run's history and the game's environment are JSON documents; the
recording (the larger part, minutes of API traffic and inputs) is kept as
gzip-compressed JSON, and the screenshot as bytes.  The schema comes from the
numbered ``MIGRATIONS`` (each applied once, in order, under a lock); never
change a released one: add one.
"""

from __future__ import annotations

import builtins
import gzip
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from psycopg import Connection, sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import DictRow, dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

from balatro_reports.domain import Report, ReportNotFound, ReportSummary, Screenshot, Status

from .common import error_count

MIGRATIONS: tuple[str, ...] = (
    # 1: the reports
    """
    CREATE TABLE reports (
        id TEXT PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        reporter TEXT NOT NULL,
        reporter_name TEXT,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        notes TEXT NOT NULL,
        game_id TEXT,
        game_version INTEGER,
        history JSONB,
        client JSONB NOT NULL,
        recording BYTEA NOT NULL,
        errors INTEGER NOT NULL,
        screenshot_type TEXT,
        screenshot BYTEA
    );
    CREATE INDEX reports_created ON reports (created_at DESC);
    CREATE INDEX reports_reporter_created ON reports (reporter, created_at DESC);
    """,
)

SUMMARY = ("id, created_at, updated_at, reporter, reporter_name, description, status, game_id, game_version, errors, "
           "screenshot IS NOT NULL AS has_screenshot, history IS NOT NULL AS has_history")


class DatabaseUnavailable(RuntimeError):
    """The database doesn't answer when the service starts."""


def where(url: str) -> str:
    """The database's address, without the password."""
    try:
        d = conninfo_to_dict(url)
    except Exception:
        return "(an unreadable URL)"
    return f"{d.get('host', 'localhost')}:{d.get('port', 5432)}/{d.get('dbname', '')}"


def pack(recording: Any) -> bytes:
    return gzip.compress(json.dumps(recording, separators=(",", ":")).encode(), compresslevel=6)


def unpack(data: bytes) -> Any:
    return json.loads(gzip.decompress(data))


class PostgresReportRepository:
    """``url``: postgresql://user:password@host/db.  ``schema``: keep the tables
    in this schema (made if needed).  ``connect_timeout``: how long to wait
    for the database at start (seconds) before raising DatabaseUnavailable."""

    def __init__(self, url: str, schema: str | None = None, max_connections: int = 5,
                 connect_timeout: float = 30) -> None:
        def configure(conn: Connection[Any]) -> None:
            conn.execute("SET TIME ZONE 'UTC'")
            if schema:
                conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.commit()

        if schema:
            with Connection.connect(url, autocommit=True) as conn:
                conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
        self._pool: ConnectionPool[Connection[DictRow]] = ConnectionPool(
            url, min_size=1, max_size=max_connections, configure=configure, open=False,
            kwargs={"row_factory": dict_row}, connection_class=Connection[DictRow])
        try:
            self._pool.open(wait=True, timeout=connect_timeout)
        except PoolTimeout:
            self._pool.close()
            raise DatabaseUnavailable(
                f"PostgreSQL at {where(url)} doesn't answer (BALATRO_REPORTS_DATABASE_URL). In Docker, the "
                "reports-db service of BalatroFrontEnd's docker-compose.yml is this service's database") from None
        self.migrate()

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def _tx(self) -> Iterator[Connection[DictRow]]:
        with self._pool.connection() as conn, conn.transaction():
            yield conn

    def migrate(self) -> None:
        with self._tx() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('balatro_reports.migrations'))")
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, "
                         "applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
            row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
            done = row["v"] if row else 0
            for version, script in enumerate(MIGRATIONS, 1):
                if version > done:
                    conn.execute(script.encode())
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))

    @staticmethod
    def _summary(row: DictRow) -> ReportSummary:
        return ReportSummary(id=row["id"], created_at=row["created_at"], updated_at=row["updated_at"],
                             reporter=row["reporter"], reporter_name=row["reporter_name"],
                             description=row["description"], status=Status(row["status"]), game_id=row["game_id"],
                             game_version=row["game_version"], has_screenshot=row["has_screenshot"],
                             has_history=row["has_history"], errors=row["errors"])

    def add(self, r: Report) -> None:
        shot = r.screenshot
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO reports (id, created_at, updated_at, reporter, reporter_name, description, status, "
                "notes, game_id, game_version, history, client, recording, errors, screenshot_type, screenshot) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (r.id, r.created_at, r.updated_at, r.reporter, r.reporter_name, r.description, r.status.value,
                 r.notes, r.game_id, r.game_version, Jsonb(r.history) if r.history is not None else None,
                 Jsonb(dict(r.client)), pack(r.recording), error_count(r.recording),
                 shot.media_type if shot else None, shot.data if shot else None))

    def get(self, report_id: str) -> Report:
        with self._tx() as conn:
            row = conn.execute("SELECT * FROM reports WHERE id = %s", (report_id,)).fetchone()
        if row is None:
            raise ReportNotFound(report_id)
        shot = Screenshot(row["screenshot_type"], bytes(row["screenshot"])) if row["screenshot"] is not None else None
        return Report(id=row["id"], created_at=row["created_at"], updated_at=row["updated_at"],
                      reporter=row["reporter"], reporter_name=row["reporter_name"], description=row["description"],
                      status=Status(row["status"]), notes=row["notes"], game_id=row["game_id"],
                      game_version=row["game_version"], history=row["history"], client=row["client"],
                      recording=unpack(bytes(row["recording"])), screenshot=shot)

    def save(self, r: Report) -> None:
        with self._tx() as conn:
            cur = conn.execute("UPDATE reports SET status = %s, notes = %s, updated_at = %s WHERE id = %s",
                               (r.status.value, r.notes, r.updated_at, r.id))
            if cur.rowcount != 1:
                raise ReportNotFound(r.id)

    def list(self, status: Status | None, limit: int, offset: int,
             reporter: str | None = None) -> builtins.list[ReportSummary]:
        with self._tx() as conn:
            rows = conn.execute(
                f"SELECT {SUMMARY} FROM reports WHERE (%(status)s::text IS NULL OR status = %(status)s) "
                "AND (%(reporter)s::text IS NULL OR reporter = %(reporter)s) "
                "ORDER BY created_at DESC LIMIT %(limit)s OFFSET %(offset)s",
                {"status": status.value if status else None, "reporter": reporter, "limit": limit,
                 "offset": offset}).fetchall()
        return [self._summary(r) for r in rows]

    def screenshot(self, report_id: str) -> Screenshot | None:
        with self._tx() as conn:
            row = conn.execute("SELECT screenshot_type, screenshot FROM reports WHERE id = %s",
                               (report_id,)).fetchone()
        if row is None:
            raise ReportNotFound(report_id)
        return Screenshot(row["screenshot_type"], bytes(row["screenshot"])) if row["screenshot"] is not None else None

    def count_since(self, reporter: str, since: datetime) -> int:
        with self._tx() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM reports WHERE reporter = %s AND created_at >= %s",
                               (reporter, since)).fetchone()
        return int(row["n"]) if row else 0
