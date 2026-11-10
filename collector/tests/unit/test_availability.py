import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from monitor.main import ProbeRunner
from monitor.model import ProbeDefinition
from monitor.probes.availability import (
    AvailabilityTargets,
    build_availability_probes,
    check_database,
    check_dns,
    check_http,
    check_icmp,
    check_smtp,
)


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query):
        self.query = query

    def fetchone(self):
        return (1,)


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return FakeCursor()


class FakeResolver:
    def __init__(self):
        self.nameservers = []
        self.port = None
        self.timeout = None
        self.lifetime = None
        self.requested = None

    def resolve(self, name, record_type):
        self.requested = (name, record_type)
        return ["172.28.0.10"]


class FakeSMTP:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def ehlo(self):
        return (250, b"postfix.lab.local")


class FakeHttpResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def close(self):
        pass


class AvailabilityTests(unittest.TestCase):
    def targets(self):
        return AvailabilityTargets(
            icmp_hosts={"web": "nginx", "db": "postgres", "dns": "coredns", "smtp": "postfix"},
            web_url="http://nginx/",
            database_url="postgresql://lab.invalid/db",
            dns_nameserver="172.28.0.53",
            dns_query_name="web.lab.local",
            smtp_host="postfix",
            smtp_port=25,
            timeout_seconds=2,
        )

    def test_icmp_alive_records_measured_rtt_and_status(self):
        result = check_icmp(
            "web",
            "nginx",
            2,
            ping_fn=lambda *args, **kwargs: SimpleNamespace(is_alive=True, avg_rtt=2.5),
        )
        self.assertEqual(result.metrics[0].metric, "web.icmp_latency_ms")
        self.assertEqual(result.metrics[0].value, 2.5)
        self.assertTrue(result.statuses[0].up)
        self.assertEqual(result.statuses[0].check_kind, "icmp")

    def test_icmp_no_reply_records_down_without_zero_latency(self):
        result = check_icmp(
            "dns",
            "coredns",
            2,
            ping_fn=lambda *args, **kwargs: SimpleNamespace(is_alive=False, avg_rtt=0),
        )
        self.assertIsNone(result.metrics[0].value)
        self.assertFalse(result.statuses[0].up)

    def test_icmp_permission_error_is_missing_data_not_false_down(self):
        class Logger:
            def error(self, message, **kwargs):
                pass

        def permission_error(*args, **kwargs):
            raise PermissionError("raw socket unavailable")

        definition = ProbeDefinition(
            "web-icmp", "web", ("web.icmp_latency_ms",), "icmp",
            lambda: check_icmp("web", "nginx", 2, ping_fn=permission_error),
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            batch = ProbeRunner(executor, 2, Logger()).collect((definition,))
        self.assertIsNone(batch.metrics[0].value)
        self.assertEqual(batch.statuses, ())

    def test_http_response_records_latency_and_requires_200(self):
        response = FakeHttpResponse(503)
        result = check_http("http://nginx/", 2, urlopen_fn=lambda *args, **kwargs: response)
        self.assertEqual(result.metrics[0].metric, "web.protocol_latency_ms")
        self.assertIsNotNone(result.metrics[0].value)
        self.assertFalse(result.statuses[0].up)
        self.assertEqual(result.statuses[0].error, "HTTP 503")

    def test_database_uses_select_one(self):
        result = check_database(
            "postgresql://lab.invalid/db",
            2,
            connect_fn=lambda *args, **kwargs: FakeConnection(),
        )
        self.assertTrue(result.statuses[0].up)
        self.assertEqual(result.statuses[0].check_kind, "protocol")

    def test_dns_queries_lab_resolver_directly(self):
        resolver = FakeResolver()
        result = check_dns("172.28.0.53", "web.lab.local", 2, resolver_factory=lambda: resolver)
        self.assertEqual(resolver.nameservers, ["172.28.0.53"])
        self.assertEqual(resolver.requested, ("web.lab.local", "A"))
        self.assertTrue(result.statuses[0].up)

    def test_smtp_uses_ehlo(self):
        result = check_smtp("postfix", 25, 2, smtp_factory=FakeSMTP)
        self.assertTrue(result.statuses[0].up)
        self.assertEqual(result.metrics[0].metric, "smtp.protocol_latency_ms")

    def test_builder_registers_icmp_and_protocol_independently(self):
        probes = build_availability_probes(self.targets())
        self.assertEqual(len(probes), 8)
        self.assertEqual(sum(probe.check_kind == "icmp" for probe in probes), 4)
        self.assertEqual(sum(probe.check_kind == "protocol" for probe in probes), 4)
        protocol_probes = [probe for probe in probes if probe.check_kind == "protocol"]
        icmp_probes = [probe for probe in probes if probe.check_kind == "icmp"]
        self.assertTrue(all(probe.failure_means_down for probe in protocol_probes))
        self.assertTrue(all(not probe.failure_means_down for probe in icmp_probes))

    def test_all_eight_probes_run_and_return_measured_values(self):
        class Logger:
            def error(self, message, **kwargs):
                raise AssertionError(message)

        probes = build_availability_probes(
            self.targets(),
            ping_fn=lambda *args, **kwargs: SimpleNamespace(is_alive=True, avg_rtt=1.0),
            urlopen_fn=lambda *args, **kwargs: FakeHttpResponse(200),
            connect_fn=lambda *args, **kwargs: FakeConnection(),
            resolver_factory=FakeResolver,
            smtp_factory=FakeSMTP,
        )
        with ThreadPoolExecutor(max_workers=8) as executor:
            batch = ProbeRunner(executor, timeout_seconds=2, logger=Logger()).collect(probes)

        self.assertEqual(len(batch.metrics), 8)
        self.assertEqual(len(batch.statuses), 8)
        self.assertTrue(all(metric.value is not None for metric in batch.metrics))
        self.assertTrue(all(status.up for status in batch.statuses))


if __name__ == "__main__":
    unittest.main()
