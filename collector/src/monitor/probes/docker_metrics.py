"""Read-only Docker Engine stats for the monitored PostgreSQL container."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Protocol

from monitor.model import Metric, ProbeDefinition, ProbeResult


class DockerClient(Protocol):
    def stats(self, container: str, **kwargs: object) -> dict[str, object]: ...


def calculate_cpu_percent(
    current: Mapping[str, object], previous: Mapping[str, object]
) -> float | None:
    """Calculate CPU percent using the deltas returned by Docker's stats API."""
    try:
        current_cpu = current["cpu_usage"]["total_usage"]  # type: ignore[index]
        previous_cpu = previous["cpu_usage"]["total_usage"]  # type: ignore[index]
        current_system = current["system_cpu_usage"]
        previous_system = previous["system_cpu_usage"]
        cpu_count = current.get("online_cpus") or len(
            current["cpu_usage"]["percpu_usage"]  # type: ignore[index,union-attr]
        )
        cpu_delta = int(current_cpu) - int(previous_cpu)
        system_delta = int(current_system) - int(previous_system)
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if cpu_delta < 0 or system_delta <= 0 or int(cpu_count) <= 0:
        return None
    return cpu_delta / system_delta * int(cpu_count) * 100.0


def _memory_bytes(stats: Mapping[str, object]) -> float | None:
    try:
        memory = stats["memory_stats"]
        usage = int(memory["usage"])  # type: ignore[index]
        details = memory.get("stats", {})  # type: ignore[union-attr]
        cache = int(
            details.get("inactive_file", details.get("cache", 0))  # type: ignore[union-attr]
        )
    except (KeyError, TypeError, ValueError):
        return None
    return float(max(0, usage - cache))


def _io_bytes(stats: Mapping[str, object]) -> tuple[int, int] | None:
    try:
        entries = stats["blkio_stats"]["io_service_bytes_recursive"]  # type: ignore[index]
        if entries is None:
            return (0, 0)
        totals = {"read": 0, "write": 0}
        for entry in entries:
            operation = str(entry["op"]).lower()
            if operation in totals:
                totals[operation] += int(entry["value"])
    except (KeyError, TypeError, ValueError):
        return None
    return totals["read"], totals["write"]


class DockerDatabaseStatsProbe:
    def __init__(
        self,
        client: DockerClient | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._client = client
        self._clock = clock
        self._wall_clock = wall_clock
        self._previous_io: tuple[int, int] | None = None
        self._previous_at: float | None = None

    def _get_client(self) -> DockerClient:
        if self._client is None:
            import docker

            self._client = docker.APIClient(version="1.41", timeout=8)
        return self._client

    def collect(self) -> ProbeResult:
        raw_stats = self._get_client().stats("devops-monitor-postgres", stream=False)
        cpu_stats = raw_stats.get("cpu_stats")
        previous_cpu_stats = raw_stats.get("precpu_stats")
        cpu_percent = (
            calculate_cpu_percent(cpu_stats, previous_cpu_stats)
            if isinstance(cpu_stats, Mapping) and isinstance(previous_cpu_stats, Mapping)
            else None
        )
        memory_bytes = _memory_bytes(raw_stats)
        io_totals = _io_bytes(raw_stats)
        now = self._clock()
        timestamp = self._wall_clock()
        if timestamp.tzinfo is None:
            raise ValueError("wall clock must return a timezone-aware datetime")
        elapsed = now - self._previous_at if self._previous_at is not None else 0
        rates: tuple[float | None, float | None] = (None, None)
        if io_totals is not None and self._previous_io is not None and elapsed > 0:
            old_read, old_write = self._previous_io
            new_read, new_write = io_totals
            if new_read >= old_read and new_write >= old_write:
                rates = ((new_read - old_read) / elapsed, (new_write - old_write) / elapsed)
        self._previous_io = io_totals
        self._previous_at = now
        return ProbeResult(
            metrics=(
                Metric("db", "db.cpu_percent", cpu_percent, collected_at=timestamp),
                Metric("db", "db.mem_bytes", memory_bytes, collected_at=timestamp),
                Metric("db", "db.io_read_bps", rates[0], collected_at=timestamp),
                Metric("db", "db.io_write_bps", rates[1], collected_at=timestamp),
            )
        )


def build_docker_database_stats_probe(
    client: DockerClient | None = None,
    clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ProbeDefinition:
    collector = DockerDatabaseStatsProbe(client=client, clock=clock, wall_clock=wall_clock)
    return ProbeDefinition(
        name="database-container-stats",
        service_id="db",
        metric_names=(
            "db.cpu_percent",
            "db.mem_bytes",
            "db.io_read_bps",
            "db.io_write_bps",
        ),
        check_kind="protocol",
        run=collector.collect,
    )
