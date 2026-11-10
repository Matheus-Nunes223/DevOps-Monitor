"""Brute-force login detector (US-16, RF-15).

>= 10 HTTP 401 on POST /login from one IP within 5 min, or >= 5 on one account.
Timestamps are the collector's observation time (15 s resolution).
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from monitor.calc import AccessLogEntry
from monitor.model import ActiveCondition, SecurityEvent


@dataclass(frozen=True, slots=True)
class LoginFailure:
    ip: str
    user: str


def login_failures(entries: Sequence[AccessLogEntry]) -> list[LoginFailure]:
    return [
        LoginFailure(entry.remote_addr, entry.user)
        for entry in entries
        if entry.request_method == "POST"
        and entry.status == 401
        and entry.request_uri.split("?", 1)[0].rstrip("/") == "/login"
    ]


class BruteForceDetector:
    def __init__(
        self, window_seconds: int = 300, ip_threshold: int = 10, user_threshold: int = 5
    ) -> None:
        self._window = timedelta(seconds=window_seconds)
        self._ip_threshold = ip_threshold
        self._user_threshold = user_threshold
        self._events: deque[tuple[datetime, LoginFailure]] = deque()
        self._reported: set[str] = set()

    def observe(self, now: datetime, failures: Sequence[LoginFailure]) -> ActiveCondition | None:
        self._events.extend((now, failure) for failure in failures)
        while self._events and now - self._events[0][0] > self._window:
            self._events.popleft()

        by_ip = Counter(failure.ip for _, failure in self._events)
        by_user = Counter(f.user for _, f in self._events if f.user)
        ips = {ip: n for ip, n in by_ip.items() if n >= self._ip_threshold}
        users = {user: n for user, n in by_user.items() if n >= self._user_threshold}
        if not ips and not users:
            self._reported.clear()
            return None

        offenders = {f"ip:{ip}" for ip in ips} | {f"user:{user}" for user in users}
        details: dict[str, object] = {
            "window_seconds": int(self._window.total_seconds()),
            "ips": [{"ip": ip, "count": n} for ip, n in sorted(ips.items(), key=lambda i: -i[1])],
            "accounts": [
                {"user": user, "count": n} for user, n in sorted(users.items(), key=lambda i: -i[1])
            ],
        }
        event = None
        if offenders - self._reported:
            event = SecurityEvent("web", "bruteforce", details, now)
            self._reported |= offenders
        parts = [f"IP {ip}: {n} falhas" for ip, n in list(ips.items())[:3]]
        parts += [f"conta {user}: {n} falhas" for user, n in list(users.items())[:3]]
        return ActiveCondition(
            key="bruteforce",
            service_id="web",
            kind="bruteforce",
            level="red",
            message="Brute-force em /login — " + "; ".join(parts),
            details=details,
            event=event,
        )
