"""Web access-log and Nginx stub_status probes."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import Protocol, Self
from urllib.request import urlopen

from monitor.calc import AccessLogEntry, calculate_web_metrics, parse_access_log
from monitor.logtail import LogTail
from monitor.model import Metric, ProbeDefinition, ProbeResult


class ProbeLogger(Protocol):
    def warning(self, message: str, **kwargs: object) -> object: ...


class HttpResponse(Protocol):
    status: int

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def read(self) -> bytes: ...


def parse_stub_status(body: bytes | str) -> int:
    text = body.decode("utf-8", errors="strict") if isinstance(body, bytes) else body
    lines = text.splitlines()
    if len(lines) < 4:
        raise ValueError("stub_status response is incomplete")

    active_match = re.fullmatch(r"Active connections:\s*(\d+)", lines[0].strip())
    if active_match is None or lines[1].strip() != "server accepts handled requests":
        raise ValueError("stub_status response header is invalid")
    if len(lines[2].split()) != 3 or not all(part.isdigit() for part in lines[2].split()):
        raise ValueError("stub_status request counters are invalid")
    if re.fullmatch(r"Reading:\s*\d+\s+Writing:\s*\d+\s+Waiting:\s*\d+", lines[3].strip()) is None:
        raise ValueError("stub_status connection counters are invalid")
    return int(active_match.group(1))


def read_active_connections(
    url: str,
    timeout_seconds: int,
    urlopen_fn: Callable[..., HttpResponse] = urlopen,
) -> int:
    with urlopen_fn(url, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise ValueError("stub_status returned a non-200 response")
        return parse_stub_status(response.read())


class AccessLogProbe:
    def __init__(
        self,
        log_tail: LogTail,
        logger: ProbeLogger,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._tail = log_tail
        self._logger = logger
        self._clock = clock
        self._last_read = clock()

    def collect(self) -> ProbeResult:
        now = self._clock()
        duration = max(now - self._last_read, 0.001)
        self._last_read = now
        lines = self._tail.read_new_lines()
        entries: list[AccessLogEntry] = []
        invalid_count = 0
        for line in lines:
            try:
                entries.append(parse_access_log(line))
            except ValueError:
                invalid_count += 1

        if invalid_count:
            self._logger.warning(
                "malformed Nginx access log lines",
                extra={
                    "probe": "web-access-log",
                    "error_type": "InvalidAccessLog",
                    "parse_error_count": invalid_count,
                },
            )

        aggregate = calculate_web_metrics(entries, duration)
        metrics = [
            Metric("web", "web.rps", aggregate.rps),
            Metric("web", "web.latency_p50_ms", aggregate.latency_p50_ms),
            Metric("web", "web.latency_p95_ms", aggregate.latency_p95_ms),
            Metric("web", "web.error_4xx_rate", aggregate.error_4xx_rate),
            Metric("web", "web.error_5xx_rate", aggregate.error_5xx_rate),
            Metric("web", "web.log_parse_errors", float(invalid_count)),
        ]
        metrics.extend(
            Metric("web", "web.status_count", float(count), {"code": str(status)})
            for status, count in aggregate.status_counts.items()
        )
        return ProbeResult(metrics=tuple(metrics))


def build_web_probes(
    log_tail: LogTail,
    stub_status_url: str,
    timeout_seconds: int,
    logger: ProbeLogger | None = None,
    urlopen_fn: Callable[..., HttpResponse] = urlopen,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[ProbeDefinition, ProbeDefinition]:
    probe_logger = logger or logging.getLogger(__name__)
    access_probe = AccessLogProbe(log_tail, probe_logger, clock=clock)
    expected_log_metrics = (
        "web.rps",
        "web.latency_p50_ms",
        "web.latency_p95_ms",
        "web.error_4xx_rate",
        "web.error_5xx_rate",
        "web.log_parse_errors",
    )
    return (
        ProbeDefinition(
            name="web-access-log",
            service_id="web",
            metric_names=expected_log_metrics,
            check_kind="protocol",
            run=access_probe.collect,
        ),
        ProbeDefinition(
            name="web-stub-status",
            service_id="web",
            metric_names=("web.active_connections",),
            check_kind="protocol",
            run=lambda: ProbeResult(
                metrics=(
                    Metric(
                        "web",
                        "web.active_connections",
                        float(
                            read_active_connections(
                                stub_status_url,
                                timeout_seconds,
                                urlopen_fn,
                            )
                        ),
                    ),
                )
            ),
        ),
    )
