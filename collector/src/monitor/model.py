"""Typed data contracts shared by probes and persistence."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Callable, Literal, Mapping

ServiceId = Literal["web", "db", "dns", "smtp"]
CheckKind = Literal["icmp", "protocol"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_timestamp(timestamp: datetime) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")


@dataclass(frozen=True, slots=True)
class Metric:
    service_id: ServiceId
    metric: str
    value: float | None
    labels: Mapping[str, object] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.metric or "." not in self.metric:
            raise ValueError("metric names must use the <service>.<metric> format")
        if self.metric.split(".", maxsplit=1)[0] != self.service_id:
            raise ValueError("metric service prefix must match service_id")
        if self.value is not None and not isfinite(self.value):
            raise ValueError("metric values must be finite or None")
        _validate_timestamp(self.collected_at)


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service_id: ServiceId
    up: bool
    check_kind: CheckKind
    latency_ms: float | None = None
    error: str | None = None
    collected_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.latency_ms is not None and (not isfinite(self.latency_ms) or self.latency_ms < 0):
            raise ValueError("latency_ms must be a finite non-negative value or None")
        _validate_timestamp(self.collected_at)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    metrics: tuple[Metric, ...] = ()
    statuses: tuple[ServiceStatus, ...] = ()


@dataclass(frozen=True, slots=True)
class ProbeDefinition:
    name: str
    service_id: ServiceId
    metric_names: tuple[str, ...]
    check_kind: CheckKind
    run: Callable[[], ProbeResult]
    failure_means_down: bool = False


@dataclass(frozen=True, slots=True)
class CollectionBatch:
    metrics: tuple[Metric, ...] = ()
    statuses: tuple[ServiceStatus, ...] = ()


def combine_results(results: tuple[ProbeResult, ...]) -> CollectionBatch:
    return CollectionBatch(
        metrics=tuple(metric for result in results for metric in result.metrics),
        statuses=tuple(status for result in results for status in result.statuses),
    )


# ---------------------------------------------------------------------------
# US-13..US-18: alerts and security contracts
# ---------------------------------------------------------------------------
Level = Literal["green", "yellow", "red"]
AlertLevel = Literal["yellow", "red"]
AlertKind = Literal["threshold", "availability", "ddos", "bruteforce", "config_change", "cve"]
SecurityEventType = Literal["ddos", "bruteforce", "config_change"]
Operator = Literal[">", "<", ">="]


@dataclass(frozen=True, slots=True)
class AlertRule:
    id: int
    service_id: ServiceId
    metric: str
    operator: Operator
    warn_threshold: float
    crit_threshold: float
    consecutive_cycles: int = 2


@dataclass(frozen=True, slots=True)
class OpenAlert:
    id: int
    rule_id: int | None
    service_id: ServiceId
    kind: AlertKind
    level: AlertLevel
    message: str
    value: float | None = None
    details: Mapping[str, object] = field(default_factory=dict)
    opened_at: datetime = field(default_factory=utc_now)
    last_notified_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    service_id: ServiceId
    type: SecurityEventType
    details: Mapping[str, object]
    detected_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ActiveCondition:
    """A security condition that is true *right now*; the alert service opens/closes alerts."""

    key: str
    service_id: ServiceId
    kind: AlertKind
    level: AlertLevel
    message: str
    details: Mapping[str, object] = field(default_factory=dict)
    event: SecurityEvent | None = None
