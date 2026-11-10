"""Post-cycle hook: security detectors -> alert engine -> e-mail."""

from __future__ import annotations

from datetime import datetime, timezone

from monitor.alerts.service import AlertService
from monitor.model import CollectionBatch
from monitor.security.monitor import SecurityMonitor


class AlertingPipeline:
    def __init__(self, alerts: AlertService, security: SecurityMonitor | None) -> None:
        self._alerts = alerts
        self._security = security

    def on_cycle(self, batch: CollectionBatch) -> None:
        now = datetime.now(timezone.utc)
        if self._security is None:
            self._alerts.process_cycle(batch, (), now, evaluated_kinds=())
            return
        report = self._security.collect(now)
        self._alerts.process_cycle(
            batch, report.conditions, now, evaluated_kinds=report.evaluated
        )
