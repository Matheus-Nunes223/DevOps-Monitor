"""Glue between the pure engine, the repository and the e-mail notifier (US-13, US-14)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone

from monitor.alerts.engine import AlertEngine, MetricKey, Transition, worst_level
from monitor.alerts.notifier import Notifier, resend_due
from monitor.alerts.repository import Repository
from monitor.alerts.templates import (
    render_open,
    render_resolved,
    threshold_message,
)
from monitor.model import (
    ActiveCondition,
    AlertKind,
    AlertLevel,
    CollectionBatch,
    Level,
    OpenAlert,
    ServiceId,
)

LOGGER = logging.getLogger(__name__)

SERVICES: tuple[ServiceId, ...] = ("web", "db", "dns", "smtp")
CONDITION_KINDS: tuple[AlertKind, ...] = ("ddos", "bruteforce", "config_change")


class UpTracker:
    """Turns protocol UP/DOWN checks into the `<svc>.up` value: consecutive failed checks."""

    def __init__(self) -> None:
        self._failures: dict[str, int] = {}

    def update(self, batch: CollectionBatch) -> dict[MetricKey, float]:
        values: dict[MetricKey, float] = {}
        for status in batch.statuses:
            if status.check_kind != "protocol":
                continue
            failures = 0 if status.up else self._failures.get(status.service_id, 0) + 1
            self._failures[status.service_id] = failures
            values[(status.service_id, f"{status.service_id}.up")] = float(failures)
        return values


def extract_values(batch: CollectionBatch) -> dict[MetricKey, float | None]:
    """Latest unlabeled value per metric in the batch."""
    values: dict[MetricKey, float | None] = {}
    for metric in batch.metrics:
        if metric.labels and set(metric.labels) != {"error_type"}:
            continue  # labeled series (e.g. status_count{code}) have no rule
        values[(metric.service_id, metric.metric)] = metric.value
    return values


class AlertService:
    def __init__(
        self,
        repository: Repository,
        notifier: Notifier,
        dashboard_url: str,
    ) -> None:
        self._repo = repository
        self._notifier = notifier
        self._dashboard_url = dashboard_url
        self._lock = threading.RLock()
        self._engine: AlertEngine | None = None
        self._up = UpTracker()
        self._inactive: dict[str, int] = {}
        self._last_levels: dict[str, Level] = {}

    # -- lifecycle ---------------------------------------------------------
    def _ensure_started(self) -> AlertEngine:
        if self._engine is None:
            rules = self._repo.load_rules()
            engine = AlertEngine(rules)
            confirmed: dict[int, Level] = {
                alert.rule_id: alert.level
                for alert in self._repo.fetch_open_alerts()
                if alert.rule_id is not None
            }
            engine.restore(confirmed)
            self._engine = engine
            LOGGER.info("alert engine started", extra={"metric_count": len(rules)})
        return self._engine

    # -- per-cycle entry point ----------------------------------------------
    def process_cycle(
        self,
        batch: CollectionBatch,
        conditions: Sequence[ActiveCondition] = (),
        now: datetime | None = None,
        evaluated_kinds: Sequence[AlertKind] = CONDITION_KINDS,
    ) -> None:
        now = now or datetime.now(timezone.utc)
        with self._lock:
            engine = self._ensure_started()
            values: dict[MetricKey, float | None] = extract_values(batch)
            values.update(self._up.update(batch))
            transitions = engine.evaluate(values)
            open_alerts = self._repo.fetch_open_alerts()
            for transition in transitions:
                self._apply_transition(transition, open_alerts, now)
            open_alerts = self._repo.fetch_open_alerts()
            self._sync(conditions, tuple(evaluated_kinds), 2, None, open_alerts, now)
            open_alerts = self._repo.fetch_open_alerts()
            self._send_reminders(open_alerts, now)
            self._update_service_levels(engine, open_alerts)

    def sync_conditions(
        self,
        conditions: Sequence[ActiveCondition],
        kinds: Iterable[AlertKind],
        clear_after: int = 1,
        services: Iterable[ServiceId] | None = None,
        now: datetime | None = None,
    ) -> None:
        """Used by jobs outside the 15 s cycle (CVE scan)."""
        now = now or datetime.now(timezone.utc)
        with self._lock:
            engine = self._ensure_started()
            open_alerts = self._repo.fetch_open_alerts()
            self._sync(conditions, tuple(kinds), clear_after, services, open_alerts, now)
            self._update_service_levels(engine, self._repo.fetch_open_alerts())

    # -- rule transitions ----------------------------------------------------
    def _apply_transition(
        self, transition: Transition, open_alerts: Sequence[OpenAlert], now: datetime
    ) -> None:
        rule = transition.rule
        existing = [a for a in open_alerts if a.rule_id == rule.id]
        for alert in existing:
            self._repo.resolve_alert(alert.id, now)
        if transition.current == "green":
            for alert in existing:
                self._notify_resolved(alert, now)
            return
        level: AlertLevel = "red" if transition.current == "red" else "yellow"
        kind: AlertKind = "availability" if rule.metric.endswith(".up") else "threshold"
        message = threshold_message(rule, level, transition.value)
        alert_id = self._repo.open_alert(
            rule_id=rule.id,
            service_id=rule.service_id,
            kind=kind,
            level=level,
            value=transition.value,
            message=message,
            details={"metric": rule.metric},
            opened_at=now,
        )
        self._notify_open(
            OpenAlert(alert_id, rule.id, rule.service_id, kind, level, message,
                      transition.value, {"metric": rule.metric}, now, None),
            now,
        )

    # -- security / CVE conditions -------------------------------------------
    def _sync(
        self,
        conditions: Sequence[ActiveCondition],
        kinds: Sequence[AlertKind],
        clear_after: int,
        services: Iterable[ServiceId] | None,
        open_alerts: Sequence[OpenAlert],
        now: datetime,
    ) -> None:
        scope = set(services) if services is not None else None
        by_key = {str(a.details.get("key")): a for a in open_alerts if a.kind in kinds}
        active_keys: set[str] = set()
        for condition in conditions:
            active_keys.add(condition.key)
            if condition.event is not None:
                self._repo.insert_security_event(condition.event)
            existing = by_key.get(condition.key)
            self._inactive.pop(condition.key, None)
            if existing is not None and existing.level == condition.level:
                continue
            if existing is not None:
                self._repo.resolve_alert(existing.id, now)
            details = {**condition.details, "key": condition.key}
            alert_id = self._repo.open_alert(
                rule_id=None,
                service_id=condition.service_id,
                kind=condition.kind,
                level=condition.level,
                value=None,
                message=condition.message,
                details=details,
                opened_at=now,
            )
            self._notify_open(
                OpenAlert(alert_id, None, condition.service_id, condition.kind, condition.level,
                          condition.message, None, details, now, None),
                now,
            )
        for key, alert in by_key.items():
            if key in active_keys or (scope is not None and alert.service_id not in scope):
                continue
            count = self._inactive.get(key, 0) + 1
            if count < clear_after:
                self._inactive[key] = count
                continue
            self._inactive.pop(key, None)
            self._repo.resolve_alert(alert.id, now)
            self._notify_resolved(alert, now)

    # -- e-mail ------------------------------------------------------------------
    def _notify_open(self, alert: OpenAlert, now: datetime, reminder: bool = False) -> None:
        email = render_open(
            service_id=alert.service_id,
            kind=alert.kind,
            level=alert.level,
            message=alert.message,
            metric=str(alert.details.get("metric")) if alert.details.get("metric") else None,
            value=alert.value,
            dashboard_url=self._dashboard_url,
            opened_at=alert.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
            reminder=reminder,
        )
        if self._notifier.send(email):
            self._repo.mark_notified(alert.id, now)

    def _notify_resolved(self, alert: OpenAlert, now: datetime) -> None:
        self._notifier.send(
            render_resolved(
                service_id=alert.service_id,
                kind=alert.kind,
                message=alert.message,
                dashboard_url=self._dashboard_url,
                resolved_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    def _send_reminders(self, open_alerts: Sequence[OpenAlert], now: datetime) -> None:
        for alert in open_alerts:
            if resend_due(alert.level, alert.last_notified_at, now):
                self._notify_open(alert, now, reminder=alert.last_notified_at is not None)

    # -- service level -------------------------------------------------------------
    def _update_service_levels(self, engine: AlertEngine, open_alerts: Sequence[OpenAlert]) -> None:
        by_rule = engine.levels_by_service()
        for service_id in SERVICES:
            security: list[Level] = [
                a.level for a in open_alerts if a.service_id == service_id and a.rule_id is None
            ]
            level = worst_level([by_rule.get(service_id, "green"), *security])
            if self._last_levels.get(service_id) != level:
                self._repo.set_service_level(service_id, level)
                self._last_levels[service_id] = level


