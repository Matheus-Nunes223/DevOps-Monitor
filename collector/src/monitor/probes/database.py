"""PostgreSQL database metrics probe using cumulative statistics snapshots."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol, Self

from monitor.dbcalc import CounterSnapshot, counter_rates, growth_gb_per_day
from monitor.model import Metric, ProbeDefinition, ProbeResult

DATABASE_METRICS_QUERY = """
SELECT
    d.xact_commit,
    d.xact_rollback,
    d.deadlocks,
    (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()),
    (SELECT setting::bigint FROM pg_settings WHERE name = 'max_connections'),
    pg_database_size(current_database()),
    d.blk_read_time,
    COALESCE((SELECT sum(calls) FROM pg_stat_statements
              WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())), 0),
    COALESCE((SELECT sum(calls) FROM pg_stat_statements
              WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
                AND mean_exec_time > 500), 0)
FROM pg_stat_database AS d
WHERE d.datname = current_database()
""".strip()


class Cursor(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> object: ...
    def execute(self, query: str) -> object: ...
    def fetchone(self) -> tuple[object, ...] | None: ...


class Connection(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> object: ...
    def cursor(self) -> Cursor: ...


class DatabaseMetricsProbe:
    """Collect database load metrics; first sample establishes a counter baseline."""

    def __init__(
        self,
        database_url: str,
        timeout_seconds: int,
        connect_fn: Callable[..., Connection] | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("LAB_DB_URL must be a PostgreSQL connection URL")
        self._database_url = database_url
        self._timeout_seconds = timeout_seconds
        self._connect_fn = connect_fn
        self._clock = clock
        self._wall_clock = wall_clock
        self._previous: CounterSnapshot | None = None
        self._previous_at: float | None = None
        self._previous_read_ms: float | None = None
        self._sizes: deque[tuple[float, float]] = deque()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(database_url=<redacted>)"

    def collect(self) -> ProbeResult:
        connect_fn = self._connect_fn
        if connect_fn is None:
            import psycopg

            connect_fn = psycopg.connect
        with connect_fn(self._database_url, connect_timeout=self._timeout_seconds) as connection:
            with connection.cursor() as cursor:
                cursor.execute(DATABASE_METRICS_QUERY)
                row = cursor.fetchone()
        if row is None or len(row) != 9:
            raise RuntimeError("PostgreSQL metrics query returned an invalid row")

        (
            commits,
            rollbacks,
            deadlocks,
            connections,
            maximum,
            size,
            read_ms,
            statements,
            slow_calls,
        ) = (
            int(row[0]),
            int(row[1]),
            int(row[2]),
            int(row[3]),
            int(row[4]),
            int(row[5]),
            float(row[6]),
            int(row[7]),
            int(row[8]),
        )
        now = self._clock()
        timestamp = self._wall_clock()
        if timestamp.tzinfo is None:
            raise ValueError("wall clock must return a timezone-aware datetime")
        snapshot = CounterSnapshot(commits, rollbacks, deadlocks, statements, slow_calls)
        elapsed = now - self._previous_at if self._previous_at is not None else 0
        rates = (
            counter_rates(self._previous, snapshot, elapsed)
            if self._previous is not None
            else None
        )
        disk_read_ms = (
            float(read_ms - self._previous_read_ms)
            if self._previous_read_ms is not None and read_ms >= self._previous_read_ms
            else None
        )
        self._previous = snapshot
        self._previous_at = now
        self._previous_read_ms = read_ms

        self._sizes.append((timestamp.timestamp(), float(size)))
        cutoff = timestamp.timestamp() - 86400
        while self._sizes and self._sizes[0][0] < cutoff:
            self._sizes.popleft()
        growth = growth_gb_per_day(self._sizes)

        metrics = [
            Metric("db", "db.qps", rates.qps if rates else None, collected_at=timestamp),
            Metric(
                "db", "db.rollback_rate", rates.rollback_rate if rates else None,
                collected_at=timestamp,
            ),
            Metric(
                "db", "db.xact_failure_rate", rates.xact_failure_rate if rates else None,
                collected_at=timestamp,
            ),
            Metric("db", "db.connections", float(connections), collected_at=timestamp),
            Metric(
                "db", "db.connections_ratio",
                connections / maximum if maximum > 0 else None,
                collected_at=timestamp,
            ),
            Metric("db", "db.disk_read_ms", disk_read_ms, collected_at=timestamp),
            Metric("db", "db.size_bytes", float(size), collected_at=timestamp),
            Metric("db", "db.growth_gb_day", growth, collected_at=timestamp),
            Metric(
                "db", "db.slow_queries_per_min",
                rates.slow_queries_per_min if rates else None,
                collected_at=timestamp,
            ),
        ]
        return ProbeResult(metrics=tuple(metrics))


def build_database_metrics_probe(
    database_url: str,
    timeout_seconds: int,
    connect_fn: Callable[..., Connection] | None = None,
    clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ProbeDefinition:
    collector = DatabaseMetricsProbe(
        database_url,
        timeout_seconds,
        connect_fn=connect_fn,
        clock=clock,
        wall_clock=wall_clock,
    )
    names = (
        "db.qps",
        "db.rollback_rate",
        "db.xact_failure_rate",
        "db.connections",
        "db.connections_ratio",
        "db.disk_read_ms",
        "db.size_bytes",
        "db.growth_gb_day",
        "db.slow_queries_per_min",
    )
    return ProbeDefinition(
        name="database-metrics",
        service_id="db",
        metric_names=names,
        check_kind="protocol",
        run=collector.collect,
    )
