"""ICMP and service-protocol availability probes for the local lab."""

from __future__ import annotations

import logging
import smtplib
import time
from collections.abc import Callable, Mapping, Sized
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, Self
from urllib.error import HTTPError
from urllib.request import urlopen

from monitor.model import (
    CheckKind,
    Metric,
    ProbeDefinition,
    ProbeResult,
    ServiceId,
    ServiceStatus,
)

if TYPE_CHECKING:
    from monitor.config import Settings

LOGGER = logging.getLogger(__name__)


class IcmpHost(Protocol):
    is_alive: bool
    avg_rtt: float


class HttpResponse(Protocol):
    status: int

    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def close(self) -> None: ...


class DatabaseCursor(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def execute(self, query: str) -> object: ...
    def fetchone(self) -> tuple[object, ...] | None: ...


class DatabaseConnection(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def cursor(self) -> DatabaseCursor: ...


class DnsResolver(Protocol):
    nameservers: list[str]
    port: int
    timeout: float
    lifetime: float

    def resolve(self, name: str, record_type: str) -> Sized: ...


class SmtpClient(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def ehlo(self) -> tuple[int, bytes]: ...


@dataclass(frozen=True, slots=True)
class AvailabilityTargets:
    icmp_hosts: Mapping[str, str]
    web_url: str
    database_url: str = field(repr=False)
    dns_nameserver: str
    dns_query_name: str
    smtp_host: str
    smtp_port: int = 25
    timeout_seconds: int = 3


def _result(
    service: ServiceId,
    check_kind: CheckKind,
    latency_ms: float | None,
    up: bool,
    error: str | None = None,
) -> ProbeResult:
    metric = Metric(service, f"{service}.{check_kind}_latency_ms", latency_ms)
    status = ServiceStatus(service, up, check_kind, latency_ms, error)
    return ProbeResult(metrics=(metric,), statuses=(status,))


def check_icmp(
    service: ServiceId,
    host: str,
    timeout_seconds: int,
    ping_fn: Callable[..., IcmpHost] | None = None,
) -> ProbeResult:
    """Run an unprivileged ICMP echo; a socket/library error is not a DOWN result."""
    if ping_fn is None:
        from icmplib import ping

        ping_fn = ping

    response = ping_fn(host, count=1, timeout=timeout_seconds, privileged=False)
    latency = float(response.avg_rtt) if response.is_alive else None
    return _result(service, "icmp", latency, bool(response.is_alive))


def check_http(
    url: str,
    timeout_seconds: int,
    urlopen_fn: Callable[..., HttpResponse] = urlopen,
) -> ProbeResult:
    started = time.monotonic()
    try:
        with urlopen_fn(url, timeout=timeout_seconds) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
        error.close()
        LOGGER.error(
            "HTTP availability check returned a non-200 response",
            extra={"error_type": "HTTPError", "http_status": status},
        )
    latency = (time.monotonic() - started) * 1000
    error = None if status == 200 else f"HTTP {status}"
    return _result("web", "protocol", latency, status == 200, error)


def check_database(
    database_url: str,
    timeout_seconds: int,
    connect_fn: Callable[..., DatabaseConnection] | None = None,
) -> ProbeResult:
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise ValueError("LAB_DB_URL must be a PostgreSQL connection URL")
    if connect_fn is None:
        import psycopg

        connect_fn = psycopg.connect

    started = time.monotonic()
    with connect_fn(database_url, connect_timeout=timeout_seconds) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
    latency = (time.monotonic() - started) * 1000
    healthy = row == (1,)
    return _result("db", "protocol", latency, healthy, None if healthy else "SELECT 1 failed")


def check_dns(
    nameserver: str,
    query_name: str,
    timeout_seconds: int,
    resolver_factory: Callable[[], DnsResolver] | None = None,
) -> ProbeResult:
    if resolver_factory is None:
        import dns.resolver

        resolver = dns.resolver.Resolver(configure=False)
    else:
        resolver = resolver_factory()
    resolver.nameservers = [nameserver]
    resolver.port = 53
    resolver.timeout = timeout_seconds
    resolver.lifetime = timeout_seconds

    started = time.monotonic()
    answer = resolver.resolve(query_name, "A")
    latency = (time.monotonic() - started) * 1000
    healthy = bool(answer)
    return _result("dns", "protocol", latency, healthy, None if healthy else "empty DNS answer")


def check_smtp(
    host: str,
    port: int,
    timeout_seconds: int,
    smtp_factory: Callable[..., SmtpClient] = smtplib.SMTP,
) -> ProbeResult:
    started = time.monotonic()
    with smtp_factory(host, port, timeout=timeout_seconds) as client:
        code, _ = client.ehlo()
    latency = (time.monotonic() - started) * 1000
    healthy = code == 250
    return _result("smtp", "protocol", latency, healthy, None if healthy else f"EHLO {code}")


def targets_from_settings(settings: Settings) -> AvailabilityTargets:
    database_url = (
        settings.lab_database_url.get_secret_value()
        if settings.lab_database_url is not None
        else ""
    )
    return AvailabilityTargets(
        icmp_hosts=settings.icmp_hosts,
        web_url=settings.web_probe_url,
        database_url=database_url,
        dns_nameserver=settings.dns_nameserver,
        dns_query_name=settings.dns_query_name,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        timeout_seconds=settings.probe_timeout_seconds,
    )


def build_availability_probes(
    targets: AvailabilityTargets,
    *,
    ping_fn: Callable[..., IcmpHost] | None = None,
    urlopen_fn: Callable[..., HttpResponse] = urlopen,
    connect_fn: Callable[..., DatabaseConnection] | None = None,
    resolver_factory: Callable[[], DnsResolver] | None = None,
    smtp_factory: Callable[..., SmtpClient] = smtplib.SMTP,
) -> tuple[ProbeDefinition, ...]:
    if not targets.database_url:
        raise ValueError("LAB_DB_URL is required for the PostgreSQL protocol probe")

    definitions: list[ProbeDefinition] = []
    service_hosts: tuple[tuple[ServiceId, str], ...] = (
        ("web", targets.icmp_hosts["web"]),
        ("db", targets.icmp_hosts["db"]),
        ("dns", targets.icmp_hosts["dns"]),
        ("smtp", targets.icmp_hosts["smtp"]),
    )
    for service, host in service_hosts:
        definitions.append(
            ProbeDefinition(
                name=f"{service}-icmp",
                service_id=service,
                metric_names=(f"{service}.icmp_latency_ms",),
                check_kind="icmp",
                run=lambda service=service, host=host: check_icmp(
                    service, host, targets.timeout_seconds, ping_fn=ping_fn
                ),
            )
        )

    definitions.extend(
        (
            ProbeDefinition(
                name="web-protocol",
                service_id="web",
                metric_names=("web.protocol_latency_ms",),
                check_kind="protocol",
                run=lambda: check_http(
                    targets.web_url,
                    targets.timeout_seconds,
                    urlopen_fn=urlopen_fn,
                ),
                failure_means_down=True,
            ),
            ProbeDefinition(
                name="db-protocol",
                service_id="db",
                metric_names=("db.protocol_latency_ms",),
                check_kind="protocol",
                run=lambda: check_database(
                    targets.database_url,
                    targets.timeout_seconds,
                    connect_fn=connect_fn,
                ),
                failure_means_down=True,
            ),
            ProbeDefinition(
                name="dns-protocol",
                service_id="dns",
                metric_names=("dns.protocol_latency_ms",),
                check_kind="protocol",
                run=lambda: check_dns(
                    targets.dns_nameserver,
                    targets.dns_query_name,
                    targets.timeout_seconds,
                    resolver_factory=resolver_factory,
                ),
                failure_means_down=True,
            ),
            ProbeDefinition(
                name="smtp-protocol",
                service_id="smtp",
                metric_names=("smtp.protocol_latency_ms",),
                check_kind="protocol",
                run=lambda: check_smtp(
                    targets.smtp_host,
                    targets.smtp_port,
                    targets.timeout_seconds,
                    smtp_factory=smtp_factory,
                ),
                failure_means_down=True,
            ),
        )
    )
    return tuple(definitions)
