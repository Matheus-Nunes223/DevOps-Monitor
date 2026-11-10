"""Per-cycle security pass: reads new access-log lines once and feeds the detectors."""

from __future__ import annotations

import logging
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from monitor.calc import AccessLogEntry, parse_access_log
from monitor.logtail import LogTail
from monitor.model import ActiveCondition, AlertKind
from monitor.security.bruteforce import BruteForceDetector, login_failures
from monitor.security.config_watch import ConfigWatcher
from monitor.security.traffic import TrafficDetector

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SecurityReport:
    """`evaluated` lists the kinds whose detector ran; only those may auto-resolve alerts."""

    conditions: tuple[ActiveCondition, ...]
    evaluated: tuple[AlertKind, ...]


class SecurityMonitor:
    def __init__(
        self,
        log_tail: LogTail,
        traffic: TrafficDetector,
        bruteforce: BruteForceDetector,
        config_watch: ConfigWatcher | None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # Own LogTail instance: offsets are independent from the web metrics probe.
        self._tail = log_tail
        self._traffic = traffic
        self._brute = bruteforce
        self._config = config_watch
        self._clock = clock
        self._last = clock()

    def collect(self, now: datetime) -> SecurityReport:
        current = self._clock()
        duration = max(current - self._last, 0.001)
        self._last = current

        entries: list[AccessLogEntry] = []
        try:
            for line in self._tail.read_new_lines():
                try:
                    entries.append(parse_access_log(line))
                except ValueError:
                    continue  # the web probe already reports malformed lines
        except OSError as error:
            LOGGER.error(
                "security log read failed",
                extra={"probe": "security-log", "error_type": type(error).__name__},
            )

        conditions: list[ActiveCondition] = []
        evaluated: list[AlertKind] = []
        ip_counts = Counter(entry.remote_addr for entry in entries)
        ok, traffic = self._guard(
            "traffic", lambda: self._traffic.observe(len(entries) / duration, ip_counts, now)
        )
        if ok:
            evaluated.append("ddos")
            if traffic is not None:
                conditions.append(traffic)
        ok, brute = self._guard(
            "bruteforce", lambda: self._brute.observe(now, login_failures(entries))
        )
        if ok:
            evaluated.append("bruteforce")
            if brute is not None:
                conditions.append(brute)
        if self._config is not None:
            watcher = self._config
            ok, drift = self._guard("config-watch", lambda: watcher.check(now))
            if ok and drift is not None:
                evaluated.append("config_change")
                conditions.extend(drift)
        return SecurityReport(tuple(conditions), tuple(evaluated))

    @staticmethod
    def _guard[T](name: str, work: Callable[[], T]) -> tuple[bool, T | None]:
        try:
            return True, work()
        except Exception as error:  # one detector must never stop the others (P1)
            LOGGER.error(
                "security detector failed",
                extra={"probe": name, "error_type": type(error).__name__},
            )
            return False, None
