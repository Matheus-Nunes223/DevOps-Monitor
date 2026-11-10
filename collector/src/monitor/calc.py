"""Pure parsing and aggregation functions for the Nginx access log."""

import ipaddress
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class AccessLogEntry:
    remote_addr: str
    status: int
    request_time_ms: float
    request_uri: str = ""
    request_method: str = ""
    user: str = ""


@dataclass(frozen=True, slots=True)
class WebMetrics:
    rps: float
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    status_counts: Mapping[int, int]
    error_4xx_rate: float | None
    error_5xx_rate: float | None


def parse_access_log(line: str) -> AccessLogEntry:
    """Validate and normalize one access_json record; raw invalid input is omitted."""
    try:
        record = json.loads(line)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("access log line is not valid JSON") from error
    if not isinstance(record, dict):
        raise ValueError("access log entry must be a JSON object")

    remote_addr = record.get("remote_addr")
    if not isinstance(remote_addr, str):
        raise ValueError("remote_addr must be a string")
    try:
        ipaddress.ip_address(remote_addr)
    except ValueError as error:
        raise ValueError("remote_addr is not a valid IP address") from error

    status = record.get("status")
    if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
        raise ValueError("status must be an HTTP status code")

    request_time = record.get("request_time")
    if isinstance(request_time, bool) or not isinstance(request_time, (int, float)):
        raise ValueError("request_time must be numeric")
    if not isfinite(float(request_time)) or request_time < 0:
        raise ValueError("request_time must be finite and non-negative")

    optional_fields: dict[str, str] = {}
    for key in ("request_uri", "request_method", "user"):
        value = record.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        optional_fields[key] = value

    return AccessLogEntry(
        remote_addr=remote_addr,
        status=status,
        request_time_ms=float(request_time) * 1000.0,
        request_uri=optional_fields["request_uri"],
        request_method=optional_fields["request_method"],
        user=optional_fields["user"],
    )


def percentile(values: Sequence[float], quantile: float) -> float | None:
    """Compute a linearly interpolated percentile; return None for no samples."""
    if not isfinite(quantile) or not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def calculate_web_metrics(
    entries: Sequence[AccessLogEntry], duration_seconds: float
) -> WebMetrics:
    if not isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("duration_seconds must be finite and greater than zero")

    total = len(entries)
    counts = dict(sorted(Counter(entry.status for entry in entries).items()))
    latencies = [entry.request_time_ms for entry in entries]
    error_4xx = sum(1 for entry in entries if 400 <= entry.status <= 499)
    error_5xx = sum(1 for entry in entries if 500 <= entry.status <= 599)

    return WebMetrics(
        rps=total / duration_seconds,
        latency_p50_ms=percentile(latencies, 0.50),
        latency_p95_ms=percentile(latencies, 0.95),
        status_counts=counts,
        error_4xx_rate=(error_4xx / total) if total else None,
        error_5xx_rate=(error_5xx / total) if total else None,
    )
