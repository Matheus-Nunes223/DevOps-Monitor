"""Active DNS resolution metrics and CoreDNS Prometheus counter collection."""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable
from typing import Protocol, Self
from urllib.request import urlopen

from monitor.model import Metric, ProbeDefinition, ProbeResult

REQUESTS_METRIC = "coredns_dns_requests_total"
_COUNTER_LINE = re.compile(
    rf"^{REQUESTS_METRIC}(?:\{{[^}}]*\}})?\s+([0-9]+(?:\.[0-9]+)?)(?:\s|$)"
)


class Resolver(Protocol):
    nameservers: list[str]
    port: int
    timeout: float
    lifetime: float

    def resolve(self, name: str, record_type: str) -> object: ...


class Response(Protocol):
    status: int

    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> object: ...
    def read(self) -> bytes: ...


def parse_coredns_requests(body: bytes | str) -> int:
    text = body.decode("utf-8", errors="strict") if isinstance(body, bytes) else body
    total = 0.0
    found = False
    for line in text.splitlines():
        match = _COUNTER_LINE.fullmatch(line.strip())
        if match:
            value = float(match.group(1))
            if not math.isfinite(value) or value < 0:
                raise ValueError("CoreDNS request counter is invalid")
            total += value
            found = True
    if not found:
        raise ValueError("CoreDNS request counter is missing")
    return int(total)


def _is_nxdomain(error: Exception) -> bool:
    return type(error).__name__ == "NXDOMAIN"


class DnsMetricsProbe:
    def __init__(
        self,
        nameserver: str,
        existing_name: str,
        missing_name: str,
        external_name: str,
        resolver_factory: Callable[[], Resolver] | None = None,
        urlopen_fn: Callable[..., Response] = urlopen,
        clock: Callable[[], float] = time.monotonic,
        timeout_seconds: float = 2.0,
        metrics_url: str = "http://coredns:9153/metrics",
    ) -> None:
        self._nameserver = nameserver
        self._queries = (
            (existing_name, True),
            (missing_name, False),
            (external_name, True),
        )
        self._resolver_factory = resolver_factory
        self._urlopen = urlopen_fn
        self._clock = clock
        self._timeout = timeout_seconds
        self._metrics_url = metrics_url
        self._previous_requests: int | None = None
        self._previous_at: float | None = None

    def _make_resolver(self) -> Resolver:
        if self._resolver_factory is not None:
            resolver = self._resolver_factory()
        else:
            import dns.resolver

            resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [self._nameserver]
        resolver.port = 53
        resolver.timeout = self._timeout
        resolver.lifetime = self._timeout
        return resolver

    def _resolve_metrics(self) -> tuple[float, float]:
        latencies: list[float] = []
        failures = 0
        resolver = self._make_resolver()
        for name, expects_answer in self._queries:
            started = self._clock()
            try:
                resolver.resolve(name, "A")
                success = expects_answer
            except Exception as error:
                success = not expects_answer and _is_nxdomain(error)
            elapsed_ms = max(self._clock() - started, 0.0) * 1000
            latencies.append(elapsed_ms)
            failures += not success
        return sum(latencies) / len(latencies), failures / len(self._queries)

    def _read_requests(self) -> int:
        with self._urlopen(self._metrics_url, timeout=self._timeout) as response:
            if response.status != 200:
                raise ValueError("CoreDNS metrics endpoint returned non-200 response")
            return parse_coredns_requests(response.read())

    def collect_resolution(self) -> ProbeResult:
        resolve_ms, failure_rate = self._resolve_metrics()
        return ProbeResult(
            metrics=(
                Metric("dns", "dns.resolve_ms", resolve_ms),
                Metric("dns", "dns.failure_rate", failure_rate),
            )
        )

    def collect_qps(self) -> ProbeResult:
        requests = self._read_requests()
        now = self._clock()
        qps = None
        if self._previous_requests is not None and self._previous_at is not None:
            elapsed = now - self._previous_at
            delta = requests - self._previous_requests
            if elapsed > 0 and delta >= 0:
                qps = delta / elapsed
        self._previous_requests = requests
        self._previous_at = now
        return ProbeResult(metrics=(Metric("dns", "dns.qps", qps),))

    def collect(self) -> ProbeResult:
        resolution = self.collect_resolution()
        qps = self.collect_qps()
        return ProbeResult(metrics=(*resolution.metrics, *qps.metrics))


def build_dns_metrics_probes(
    nameserver: str,
    existing_name: str,
    missing_name: str,
    external_name: str = "example.com",
    timeout_seconds: int = 2,
    resolver_factory: Callable[[], Resolver] | None = None,
    urlopen_fn: Callable[..., Response] = urlopen,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[ProbeDefinition, ProbeDefinition]:
    collector = DnsMetricsProbe(
        nameserver,
        existing_name,
        missing_name,
        external_name,
        resolver_factory=resolver_factory,
        urlopen_fn=urlopen_fn,
        clock=clock,
        timeout_seconds=timeout_seconds,
    )
    return (
        ProbeDefinition(
            name="dns-resolution-metrics",
            service_id="dns",
            metric_names=("dns.resolve_ms", "dns.failure_rate"),
            check_kind="protocol",
            run=collector.collect_resolution,
        ),
        ProbeDefinition(
            name="coredns-qps",
            service_id="dns",
            metric_names=("dns.qps",),
            check_kind="protocol",
            run=collector.collect_qps,
        ),
    )
