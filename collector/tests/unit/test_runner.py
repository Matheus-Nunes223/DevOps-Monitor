import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from monitor.main import ProbeRunner
from monitor.model import Metric, ProbeDefinition, ProbeResult


class CaptureLogger:
    def __init__(self):
        self.errors = []

    def error(self, message, **kwargs):
        self.errors.append((message, kwargs))


class ProbeRunnerTests(unittest.TestCase):
    def test_one_probe_failure_does_not_discard_successful_probe(self):
        logger = CaptureLogger()

        def failing_probe():
            raise RuntimeError("probe exploded")

        def healthy_probe():
            return ProbeResult(metrics=(Metric("web", "web.latency_p95_ms", 7.5),))

        probes = (
            ProbeDefinition("dns", "dns", ("dns.resolve_ms",), "protocol", failing_probe),
            ProbeDefinition("web", "web", ("web.latency_p95_ms",), "protocol", healthy_probe),
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = ProbeRunner(executor, timeout_seconds=1, logger=logger).collect(probes)

        self.assertEqual(len(logger.errors), 1)
        metrics = {(metric.service_id, metric.metric): metric.value for metric in result.metrics}
        self.assertIsNone(metrics[("dns", "dns.resolve_ms")])
        self.assertEqual(metrics[("web", "web.latency_p95_ms")], 7.5)
        self.assertEqual(len(result.statuses), 0)

    def test_probe_timeout_is_reported_as_missing_metric(self):
        logger = CaptureLogger()

        def slow_probe():
            time.sleep(0.1)
            return ProbeResult()

        with ThreadPoolExecutor(max_workers=1) as executor:
            runner = ProbeRunner(executor, timeout_seconds=0.01, logger=logger)
            definition = ProbeDefinition(
                "web", "web", ("web.rps",), "protocol", slow_probe
            )
            result = runner.collect((definition,))
        self.assertIsNone(result.metrics[0].value)
        self.assertTrue(logger.errors)


if __name__ == "__main__":
    unittest.main()
