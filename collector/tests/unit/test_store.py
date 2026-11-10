import unittest
from datetime import datetime, timezone

from monitor.model import CollectionBatch, Metric, ServiceStatus
from monitor.store import PostgresStore


class FakeCursor:
    def __init__(self):
        self.executemany_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def executemany(self, query, rows):
        self.executemany_calls.append((query, list(rows)))


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.fake_cursor


class StoreTests(unittest.TestCase):
    def test_writes_metrics_and_statuses_in_batches_with_missing_value_preserved(self):
        connection = FakeConnection()
        store = PostgresStore("postgresql://example/db", connector=lambda dsn: connection)
        timestamp = datetime.now(timezone.utc)
        batch = CollectionBatch(
            metrics=(Metric("web", "web.rps", None, {"reason": "timeout"}, timestamp),),
            statuses=(ServiceStatus("web", False, "protocol", None, "timeout", timestamp),),
        )
        store.write(batch)

        self.assertEqual(len(connection.fake_cursor.executemany_calls), 2)
        metric_rows = connection.fake_cursor.executemany_calls[0][1]
        self.assertIsNone(metric_rows[0][2])
        self.assertEqual(metric_rows[0][3], '{"reason":"timeout"}')


if __name__ == "__main__":
    unittest.main()
