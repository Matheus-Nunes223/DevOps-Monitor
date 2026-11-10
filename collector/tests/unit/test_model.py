import unittest
from datetime import datetime, timezone

from monitor.model import Metric, ServiceStatus


class ModelTests(unittest.TestCase):
    def test_metric_accepts_missing_measurement(self):
        metric = Metric("web", "web.rps", None)
        self.assertIsNone(metric.value)
        self.assertIsNotNone(metric.collected_at.tzinfo)

    def test_metric_rejects_nonfinite_measurement(self):
        with self.assertRaises(ValueError):
            Metric("db", "db.cpu_percent", float("nan"))

    def test_metric_rejects_timestamp_without_timezone(self):
        with self.assertRaises(ValueError):
            Metric("dns", "dns.resolve_ms", 1.0, collected_at=datetime(2026, 1, 1))

    def test_status_rejects_negative_latency(self):
        with self.assertRaises(ValueError):
            ServiceStatus("smtp", False, "protocol", latency_ms=-1.0)


if __name__ == "__main__":
    unittest.main()
