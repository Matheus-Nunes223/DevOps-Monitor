"""Supabase persistence for rules, alerts, security events, baselines and CVEs."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from monitor.model import AlertKind, AlertLevel, AlertRule, Level, OpenAlert, SecurityEvent

LOGGER = logging.getLogger(__name__)


class Repository(Protocol):
    def load_rules(self) -> list[AlertRule]: ...
    def fetch_open_alerts(self) -> list[OpenAlert]: ...
    def open_alert(
        self,
        *,
        rule_id: int | None,
        service_id: str,
        kind: AlertKind,
        level: AlertLevel,
        value: float | None,
        message: str,
        details: Mapping[str, object],
        opened_at: datetime,
    ) -> int: ...
    def resolve_alert(self, alert_id: int, resolved_at: datetime) -> None: ...
    def mark_notified(self, alert_id: int, notified_at: datetime) -> None: ...
    def set_service_level(self, service_id: str, level: Level) -> None: ...
    def insert_security_event(self, event: SecurityEvent) -> None: ...
    def load_baselines(self) -> dict[str, str]: ...
    def load_baseline_contents(self) -> dict[str, tuple[str, str]]: ...
    def insert_baseline(self, path: str, service_id: str, sha256: str, content: str) -> None: ...
    def replace_vulnerabilities(
        self, service_id: str, version: str, rows: Sequence[Mapping[str, object]]
    ) -> None: ...


def _json(value: Mapping[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


class PostgresRepository:
    """One long-lived connection, reopened after an OperationalError."""

    def __init__(self, database_url: str, connector: Callable[[str], Any] | None = None) -> None:
        self._url = database_url
        self._lock = threading.RLock()
        self._conn: Any = None
        if connector is None:
            import psycopg

            connector = psycopg.connect
        self._connector = connector

    def _run(self, work: Callable[[Any], Any]) -> Any:
        with self._lock:
            for attempt in (1, 2):
                if self._conn is None or getattr(self._conn, "closed", False):
                    self._conn = self._connector(self._url)
                try:
                    result = work(self._conn)
                    self._conn.commit()
                    return result
                except Exception as error:
                    try:
                        self._conn.rollback()
                    except Exception:  # connection already broken
                        self._conn = None
                    if attempt == 2 or type(error).__name__ != "OperationalError":
                        raise
                    LOGGER.warning(
                        "repository reconnecting", extra={"error_type": type(error).__name__}
                    )
                    self._conn = None

    # -- rules and alerts -------------------------------------------------
    def load_rules(self) -> list[AlertRule]:
        def work(conn: Any) -> list[AlertRule]:
            cur = conn.execute(
                "select id, service_id, metric, operator, warn_threshold, crit_threshold,"
                " consecutive_cycles from public.alert_rules where enabled order by id"
            )
            return [AlertRule(*row) for row in cur.fetchall()]

        return self._run(work)

    def fetch_open_alerts(self) -> list[OpenAlert]:
        def work(conn: Any) -> list[OpenAlert]:
            cur = conn.execute(
                "select id, rule_id, service_id, kind, level, message, value, details,"
                " opened_at, last_notified_at from public.alerts where status = 'open'"
                " order by id"
            )
            return [
                OpenAlert(
                    id=r[0], rule_id=r[1], service_id=r[2], kind=r[3], level=r[4],
                    message=r[5], value=r[6], details=r[7] or {}, opened_at=r[8],
                    last_notified_at=r[9],
                )
                for r in cur.fetchall()
            ]

        return self._run(work)

    def open_alert(
        self,
        *,
        rule_id: int | None,
        service_id: str,
        kind: AlertKind,
        level: AlertLevel,
        value: float | None,
        message: str,
        details: Mapping[str, object],
        opened_at: datetime,
    ) -> int:
        def work(conn: Any) -> int:
            cur = conn.execute(
                "insert into public.alerts (rule_id, service_id, kind, level, value, message,"
                " details, opened_at) values (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)"
                " returning id",
                (rule_id, service_id, kind, level, value, message, _json(details), opened_at),
            )
            return int(cur.fetchone()[0])

        return self._run(work)

    def resolve_alert(self, alert_id: int, resolved_at: datetime) -> None:
        self._run(
            lambda conn: conn.execute(
                "update public.alerts set status = 'resolved', resolved_at = %s"
                " where id = %s and status = 'open'",
                (resolved_at, alert_id),
            )
        )

    def mark_notified(self, alert_id: int, notified_at: datetime) -> None:
        self._run(
            lambda conn: conn.execute(
                "update public.alerts set last_notified_at = %s where id = %s",
                (notified_at, alert_id),
            )
        )

    def set_service_level(self, service_id: str, level: Level) -> None:
        self._run(
            lambda conn: conn.execute(
                "update public.services set current_level = %s where id = %s"
                " and current_level is distinct from %s",
                (level, service_id, level),
            )
        )

    # -- security ---------------------------------------------------------
    def insert_security_event(self, event: SecurityEvent) -> None:
        self._run(
            lambda conn: conn.execute(
                "insert into public.security_events (service_id, type, details, detected_at)"
                " values (%s, %s, %s::jsonb, %s)",
                (event.service_id, event.type, _json(event.details), event.detected_at),
            )
        )

    def load_baselines(self) -> dict[str, str]:
        def work(conn: Any) -> dict[str, str]:
            cur = conn.execute("select path, sha256 from public.config_baselines")
            return {row[0]: row[1] for row in cur.fetchall()}

        return self._run(work)

    def load_baseline_contents(self) -> dict[str, tuple[str, str]]:
        def work(conn: Any) -> dict[str, tuple[str, str]]:
            cur = conn.execute("select path, sha256, content from public.config_baselines")
            return {row[0]: (row[1], row[2]) for row in cur.fetchall()}

        return self._run(work)

    def insert_baseline(self, path: str, service_id: str, sha256: str, content: str) -> None:
        self._run(
            lambda conn: conn.execute(
                "insert into public.config_baselines (path, service_id, sha256, content)"
                " values (%s, %s, %s, %s) on conflict (path) do nothing",
                (path, service_id, sha256, content),
            )
        )

    def replace_vulnerabilities(
        self, service_id: str, version: str, rows: Sequence[Mapping[str, object]]
    ) -> None:
        def work(conn: Any) -> None:
            cve_ids = [str(row["cve_id"]) for row in rows]
            conn.execute(
                "delete from public.vulnerabilities where service_id = %s"
                " and not (cve_id = any(%s))",
                (service_id, cve_ids),
            )
            for row in rows:
                conn.execute(
                    "insert into public.vulnerabilities (service_id, product_version, cve_id,"
                    " cvss, summary, published_at, checked_at)"
                    " values (%s, %s, %s, %s, %s, %s, now())"
                    " on conflict (service_id, cve_id) do update set"
                    " product_version = excluded.product_version, cvss = excluded.cvss,"
                    " summary = excluded.summary, published_at = excluded.published_at,"
                    " checked_at = now()",
                    (service_id, version, row["cve_id"], row["cvss"], row["summary"],
                     row["published_at"]),
                )

        self._run(work)
