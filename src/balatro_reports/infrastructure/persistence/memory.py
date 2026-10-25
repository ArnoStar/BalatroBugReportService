"""Reports kept in memory (lost when the service stops).  For tests and demos."""

from __future__ import annotations

import builtins
import copy
import threading
from datetime import datetime

from balatro_reports.domain import Report, ReportNotFound, ReportSummary, Screenshot, Status

from .common import summary


class InMemoryReportRepository:
    def __init__(self) -> None:
        self._reports: dict[str, Report] = {}
        self._lock = threading.Lock()

    def add(self, report: Report) -> None:
        with self._lock:
            self._reports[report.id] = copy.deepcopy(report)

    def get(self, report_id: str) -> Report:
        with self._lock:
            r = self._reports.get(report_id)
            if r is None:
                raise ReportNotFound(report_id)
            return copy.deepcopy(r)

    def save(self, report: Report) -> None:
        with self._lock:
            if report.id not in self._reports:
                raise ReportNotFound(report.id)
            self._reports[report.id] = copy.deepcopy(report)

    def list(self, status: Status | None, limit: int, offset: int,
             reporter: str | None = None) -> builtins.list[ReportSummary]:
        with self._lock:
            rs = sorted((r for r in self._reports.values() if (status is None or r.status is status)
                         and (reporter is None or r.reporter == reporter)),
                        key=lambda r: r.created_at, reverse=True)
            return [summary(r) for r in rs[offset:offset + limit]]

    def screenshot(self, report_id: str) -> Screenshot | None:
        return self.get(report_id).screenshot

    def count_since(self, reporter: str, since: datetime) -> int:
        with self._lock:
            return sum(1 for r in self._reports.values() if r.reporter == reporter and r.created_at >= since)
