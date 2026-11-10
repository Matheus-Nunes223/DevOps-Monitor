"""Pure calculations for PostgreSQL cumulative statistics."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum
from typing import Iterable


@dataclass(frozen=True, slots=True)
class CounterSnapshot:
    commits: int
    rollbacks: int
    deadlocks: int
    statements: int
    slow_calls: int


@dataclass(frozen=True, slots=True)
class CounterRates:
    qps: float | None
    rollback_rate: float | None
    xact_failure_rate: float | None
    slow_queries_per_min: float | None


def counter_rates(
    before: CounterSnapshot,
    after: CounterSnapshot,
    elapsed_seconds: float,
) -> CounterRates:
    """Return rates from cumulative deltas; resets or invalid intervals are missing."""
    counters_before = (
        before.commits,
        before.rollbacks,
        before.deadlocks,
        before.statements,
        before.slow_calls,
    )
    counters_after = (
        after.commits,
        after.rollbacks,
        after.deadlocks,
        after.statements,
        after.slow_calls,
    )
    if elapsed_seconds <= 0 or any(new < old for old, new in zip(counters_before, counters_after)):
        return CounterRates(None, None, None, None)

    commits = after.commits - before.commits
    rollbacks = after.rollbacks - before.rollbacks
    deadlocks = after.deadlocks - before.deadlocks
    transactions = commits + rollbacks
    return CounterRates(
        qps=(after.statements - before.statements) / elapsed_seconds,
        rollback_rate=rollbacks / transactions if transactions else None,
        xact_failure_rate=deadlocks / transactions if transactions else None,
        slow_queries_per_min=(after.slow_calls - before.slow_calls) * 60 / elapsed_seconds,
    )


def growth_gb_per_day(samples: Iterable[tuple[float, float]]) -> float | None:
    """Estimate size slope by least squares; samples are (Unix time, bytes)."""
    points = tuple(samples)
    if len(points) < 2:
        return None
    mean_time = fsum(timestamp for timestamp, _ in points) / len(points)
    mean_size = fsum(size for _, size in points) / len(points)
    variance = fsum((timestamp - mean_time) ** 2 for timestamp, _ in points)
    if variance == 0:
        return None
    slope_bytes_per_second = fsum(
        (timestamp - mean_time) * (size - mean_size) for timestamp, size in points
    ) / variance
    return slope_bytes_per_second * 86400 / (1024**3)
