import unittest

from monitor.main import ProbeRunner
from monitor.probes.web import build_web_probes, parse_stub_status


class CaptureLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warning(self, message, **kwargs):
        self.warnings.append((message, kwargs))

    def error(self, message, **kwargs):
        self.errors.append((message, kwargs))


class FakeTail:
    def __init__(self, lines):
        self.lines = lines

    def read_new_lines(self):
        return self.lines


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        current = self.value
        self.value += 15.0
        return current


class FakeResponse:
    def __init__(self, body):
        self.status = 200
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


class WebProbeTests(unittest.TestCase):
    def test_parses_nginx_stub_status(self):
        body = (
            b"Active connections: 7\nserver accepts handled requests\n 10 10 42\n"
            b"Reading: 1 Writing: 2 Waiting: 4\n"
        )
        self.assertEqual(parse_stub_status(body), 7)

    def test_invalid_stub_status_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_stub_status(b"not an nginx status page")

    def test_access_log_and_stub_status_are_separate_probes(self):
        lines = [
            '{"remote_addr":"192.0.2.1","status":200,"request_time":0.01}',
            '{"remote_addr":"192.0.2.2","status":503,"request_time":0.04}',
        ]
        probes = build_web_probes(
            log_tail=FakeTail(lines),
            stub_status_url="http://nginx/nginx_status",
            timeout_seconds=2,
            logger=CaptureLogger(),
            clock=FakeClock(),
            urlopen_fn=lambda *args, **kwargs: FakeResponse(
                b"Active connections: 7\nserver accepts handled requests\n 10 10 42\n"
                b"Reading: 1 Writing: 2 Waiting: 4\n"
            ),
        )
        self.assertEqual(len(probes), 2)
        class InlineExecutor:
            def submit(self, fn):
                from concurrent.futures import Future
                future = Future()
                try:
                    future.set_result(fn())
                except Exception as error:
                    future.set_exception(error)
                return future

        result = ProbeRunner(
            InlineExecutor(), timeout_seconds=1, logger=CaptureLogger()
        ).collect(probes)
        by_name = {metric.metric: metric for metric in result.metrics}
        self.assertEqual(by_name["web.rps"].value, 2 / 15)
        self.assertEqual(by_name["web.status_count"].value, 1.0)
        self.assertEqual(by_name["web.active_connections"].value, 7.0)

    def test_malformed_line_is_logged_without_copying_sensitive_input(self):
        logger = CaptureLogger()
        probes = build_web_probes(
            log_tail=FakeTail(["not-json-with-user-secret"]),
            stub_status_url="http://nginx/nginx_status",
            timeout_seconds=2,
            logger=logger,
            urlopen_fn=lambda *args, **kwargs: FakeResponse(
                b"Active connections: 0\nserver accepts handled requests\n 0 0 0\n"
                b"Reading: 0 Writing: 0 Waiting: 0\n"
            ),
        )
        result = probes[0].run()
        latency = next(
            metric for metric in result.metrics if metric.metric == "web.latency_p50_ms"
        )
        self.assertIsNone(latency.value)
        self.assertEqual(len(logger.warnings), 1)
        self.assertNotIn("user-secret", repr(logger.warnings))


if __name__ == "__main__":
    unittest.main()
