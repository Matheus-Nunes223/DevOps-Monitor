from __future__ import annotations

import unittest

from monitor.probes.dns import (
    DnsMetricsProbe,
    build_dns_metrics_probes,
    parse_coredns_requests,
)


class Answer:
    def __bool__(self) -> bool:
        return True


class NXDOMAIN(Exception):
    pass


class Resolver:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.nameservers: list[str] = []
        self.port = 0
        self.timeout = 0.0
        self.lifetime = 0.0
        self.queries: list[str] = []

    def resolve(self, name: str, record_type: str) -> Answer:
        self.queries.append(name)
        result = self.responses[name]
        if isinstance(result, Exception):
            raise result
        return result  # type: ignore[return-value]


class Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class DnsProbeTests(unittest.TestCase):
    def test_parses_request_counter_with_and_without_labels(self) -> None:
        body = b"""
# HELP coredns_dns_requests_total Counter of DNS requests made.
# TYPE coredns_dns_requests_total counter
coredns_dns_requests_total{server="dns://:53",zone="."} 10
coredns_dns_requests_total{server="dns://:53",zone="lab.local."} 4
other_metric 99
"""
        self.assertEqual(parse_coredns_requests(body), 14)

    def test_rejects_missing_or_invalid_counter(self) -> None:
        with self.assertRaises(ValueError):
            parse_coredns_requests("other_metric 4\n")
        with self.assertRaises(ValueError):
            parse_coredns_requests("coredns_dns_requests_total NaN\n")

    def test_three_queries_record_average_latency_and_failure_rate(self) -> None:
        resolver = Resolver(
            {
                "web.lab.local": Answer(),
                "missing.lab.local": NXDOMAIN(),
                "example.com": Answer(),
            }
        )
        clock_values = iter(index / 10 for index in range(7))
        metrics_body = b'coredns_dns_requests_total{server="dns://:53"} 20\n'
        probe = DnsMetricsProbe(
            nameserver="172.28.0.53",
            existing_name="web.lab.local",
            missing_name="missing.lab.local",
            external_name="example.com",
            resolver_factory=lambda: resolver,
            urlopen_fn=lambda *_a, **_kw: Response(metrics_body),
            clock=lambda: next(clock_values),
        )

        result = {metric.metric: metric.value for metric in probe.collect().metrics}

        self.assertEqual(resolver.nameservers, ["172.28.0.53"])
        self.assertEqual(resolver.queries, ["web.lab.local", "missing.lab.local", "example.com"])
        self.assertAlmostEqual(result["dns.failure_rate"], 0.0)
        self.assertAlmostEqual(result["dns.resolve_ms"], 100.0)
        self.assertIsNone(result["dns.qps"])

    def test_unexpected_failure_and_nxdomain_expectation_affect_failure_rate(self) -> None:
        resolver = Resolver(
            {
                "web.lab.local": TimeoutError(),
                "missing.lab.local": Answer(),
                "example.com": Answer(),
            }
        )
        clock_values = iter(index / 10 for index in range(7))
        probe = DnsMetricsProbe(
            "172.28.0.53", "web.lab.local", "missing.lab.local", "example.com",
            resolver_factory=lambda: resolver,
            urlopen_fn=lambda *_a, **_kw: Response(
                b'coredns_dns_requests_total{server="dns://:53"} 25\n'
            ),
            clock=lambda: next(clock_values),
        )
        result = {metric.metric: metric.value for metric in probe.collect().metrics}
        self.assertAlmostEqual(result["dns.failure_rate"], 2 / 3)

    def test_qps_uses_counter_delta_and_resets_are_missing(self) -> None:
        resolver_factory = lambda: Resolver(
            {"web.lab.local": Answer(), "missing.lab.local": NXDOMAIN(), "example.com": Answer()}
        )
        class Clock:
            value = 0.0

            def __call__(self) -> float:
                current = self.value
                self.value += 0.1
                return current

        cycle_clock = Clock()
        sequence = iter((100, 160, 2))

        def urlopen(*_args: object, **_kwargs: object) -> Response:
            return Response(f"coredns_dns_requests_total {next(sequence)}\n".encode())

        probe = DnsMetricsProbe(
            "172.28.0.53", "web.lab.local", "missing.lab.local", "example.com",
            resolver_factory=resolver_factory,
            urlopen_fn=urlopen,
            clock=cycle_clock,
        )
        first = {m.metric: m.value for m in probe.collect().metrics}
        second = {m.metric: m.value for m in probe.collect().metrics}
        third = {m.metric: m.value for m in probe.collect().metrics}
        self.assertIsNone(first["dns.qps"])
        self.assertAlmostEqual(second["dns.qps"], 60 / 0.7)
        self.assertIsNone(third["dns.qps"])

    def test_resolution_and_prometheus_scrape_are_separate_probes(self) -> None:
        resolver = Resolver(
            {
                "web.lab.local": Answer(),
                "missing.lab.local": NXDOMAIN(),
                "example.com": Answer(),
            }
        )

        def unavailable_metrics(*_args: object, **_kwargs: object) -> Response:
            raise OSError("metrics endpoint unavailable")

        probes = build_dns_metrics_probes(
            "172.28.0.53",
            "web.lab.local",
            "missing.lab.local",
            resolver_factory=lambda: resolver,
            urlopen_fn=unavailable_metrics,
        )
        self.assertEqual(len(probes), 2)
        self.assertEqual(
            {metric.metric for metric in probes[0].run().metrics},
            {"dns.resolve_ms", "dns.failure_rate"},
        )
        with self.assertRaises(OSError):
            probes[1].run()


if __name__ == "__main__":
    unittest.main()
