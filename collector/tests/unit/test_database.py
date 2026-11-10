from __future__ import annotations

import unittest
from datetime import datetime, timezone

from monitor.probes.database import DatabaseMetricsProbe


class Cursor:
    def __init__(self, row: tuple[object, ...]) -> None:
        self.row = row
        self.query = ""

    def __enter__(self) -> Cursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, query: str) -> None:
        self.query = query

    def fetchone(self) -> tuple[object, ...]:
        return self.row


class Connection:
    def __init__(self, cursor: Cursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def cursor(self) -> Cursor:
        return self.fake_cursor


class DatabaseProbeTests(unittest.TestCase):
    def test_collects_metrics_from_aggregate_query_without_sql_text(self) -> None:
        row = (100, 5, 2, 10, 100, 5000, 100, 2000, 500)
        cursor = Cursor(row)
        connections: list[tuple[str, int]] = []

        def connect(dsn: str, connect_timeout: int) -> Connection:
            connections.append((dsn, connect_timeout))
            return Connection(cursor)

        probe = DatabaseMetricsProbe(
            "postgresql://secret@db/test",
            timeout_seconds=2,
            connect_fn=connect,
            clock=lambda: 100.0,
            wall_clock=lambda: datetime(2026, 11, 9, tzinfo=timezone.utc),
        )
        result = probe.collect()
        names = {metric.metric for metric in result.metrics}

        self.assertIn("db.connections", names)
        self.assertIn("db.connections_ratio", names)
        self.assertIn("db.size_bytes", names)
        self.assertEqual(connections, [("postgresql://secret@db/test", 2)])
        self.assertNotIn("query", cursor.query.lower())
        self.assertNotIn("secret", repr(probe))

    def test_first_sample_is_baseline_and_second_sample_emits_rates(self) -> None:
        rows = iter(((100, 5, 2, 10, 100, 5000, 100, 2000, 500),
                     (130, 8, 3, 11, 100, 5100, 160, 2120, 520)))

        class RowsCursor(Cursor):
            def fetchone(self) -> tuple[object, ...]:
                return next(rows)

        cursor = RowsCursor(())
        ticks = iter((10.0, 40.0))
        probe = DatabaseMetricsProbe(
            "postgresql://user@db/test",
            timeout_seconds=2,
            connect_fn=lambda *_args, **_kwargs: Connection(cursor),
            clock=lambda: next(ticks),
        )

        first = {metric.metric: metric.value for metric in probe.collect().metrics}
        second = {metric.metric: metric.value for metric in probe.collect().metrics}

        self.assertIsNone(first["db.qps"])
        self.assertAlmostEqual(second["db.qps"], 4.0)
        self.assertAlmostEqual(second["db.slow_queries_per_min"], 40.0)


if __name__ == "__main__":
    unittest.main()
