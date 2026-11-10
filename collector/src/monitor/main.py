"""Collector cycle isolation, JSON logging, and recurring scheduler."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Sequence
from concurrent.futures import Executor, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol

from monitor.model import (
    CollectionBatch,
    Metric,
    ProbeDefinition,
    ProbeResult,
    ServiceStatus,
    combine_results,
)
from monitor.store import PostgresStore

if TYPE_CHECKING:
    from monitor.config import Settings


class JsonFormatter(logging.Formatter):
    """Emit one safe, machine-readable object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "probe",
            "error_type",
            "http_status",
            "parse_error_count",
            "metric_count",
            "status_count",
            "duration_ms",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


class ErrorLogger(Protocol):
    def error(self, message: str, **kwargs: object) -> object: ...


class ProbeRunner:
    """Execute probes concurrently; isolate exceptions and timeouts per probe."""

    def __init__(self, executor: Executor, timeout_seconds: int, logger: ErrorLogger) -> None:
        self._executor = executor
        self._timeout_seconds = timeout_seconds
        self._logger = logger

    def collect(self, probes: Sequence[ProbeDefinition]) -> CollectionBatch:
        future_to_probe: dict[Future[ProbeResult], ProbeDefinition] = {
            self._executor.submit(probe.run): probe for probe in probes
        }
        completed, pending = wait(future_to_probe, timeout=self._timeout_seconds)
        results: list[ProbeResult] = []

        for future in completed:
            probe = future_to_probe[future]
            try:
                results.append(future.result())
            except Exception as error:
                self._logger.error(
                    "probe failed",
                    extra={"probe": probe.name, "error_type": type(error).__name__},
                )
                results.append(self._missing_result(probe, type(error).__name__))

        for future in pending:
            probe = future_to_probe[future]
            future.cancel()
            self._logger.error(
                "probe timed out",
                extra={"probe": probe.name, "error_type": "TimeoutError"},
            )
            results.append(self._missing_result(probe, "TimeoutError"))

        return combine_results(tuple(results))

    @staticmethod
    def _missing_result(probe: ProbeDefinition, error_type: str) -> ProbeResult:
        timestamp = datetime.now(timezone.utc)
        metrics = tuple(
            Metric(probe.service_id, metric_name, None, {"error_type": error_type}, timestamp)
            for metric_name in probe.metric_names
        )
        statuses = (
            (ServiceStatus(probe.service_id, False, probe.check_kind, None, error_type, timestamp),)
            if probe.failure_means_down
            else ()
        )
        return ProbeResult(metrics=metrics, statuses=statuses)


class Scheduler(Protocol):
    def add_job(self, func: Callable[[], object], trigger: str, **kwargs: object) -> object: ...
    def start(self) -> object: ...
    def shutdown(self, wait: bool = True) -> object: ...


class CollectorApplication:
    def __init__(
        self,
        settings: Settings,
        store: PostgresStore,
        probes: Sequence[ProbeDefinition],
        logger: logging.Logger | None = None,
        executor: Executor | None = None,
        post_cycle: Callable[[CollectionBatch], object] | None = None,
    ) -> None:
        self._post_cycle = post_cycle
        self._settings = settings
        self._store = store
        self._probes = tuple(probes)
        self._logger = logger or logging.getLogger(__name__)
        self._owns_executor = executor is None
        self._executor = executor or ThreadPoolExecutor(max_workers=settings.max_probe_workers)
        self._runner = ProbeRunner(self._executor, settings.probe_timeout_seconds, self._logger)

    def run_cycle(self) -> None:
        started = time.monotonic()
        batch = self._runner.collect(self._probes)
        try:
            self._store.write(batch)
        except Exception as error:
            self._logger.error(
                "cycle persistence failed",
                extra={"error_type": type(error).__name__},
            )
        if self._post_cycle is not None:
            try:
                self._post_cycle(batch)
            except Exception as error:  # alerts must never break collection (P1)
                self._logger.error(
                    "alerting pass failed",
                    extra={"probe": "alerting", "error_type": type(error).__name__},
                )
        self._logger.info(
            "collection cycle completed",
            extra={
                "metric_count": len(batch.metrics),
                "status_count": len(batch.statuses),
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )

    def close(self) -> None:
        if self._owns_executor and isinstance(self._executor, ThreadPoolExecutor):
            self._executor.shutdown(wait=False, cancel_futures=True)


def build_scheduler(
    application: CollectorApplication,
    interval_seconds: int,
    scheduler: Scheduler | None = None,
) -> Scheduler:
    if scheduler is None:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        application.run_cycle,
        "interval",
        seconds=interval_seconds,
        id="collector-cycle",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=interval_seconds,
    )
    return scheduler


def build_alerting(settings: Settings, logger: logging.Logger):  # noqa: ANN201
    """Wire US-13..US-18: alert engine, e-mail, security detectors and CVE job."""
    from pathlib import Path

    from monitor.alerts.notifier import EmailNotifier
    from monitor.alerts.repository import PostgresRepository
    from monitor.alerts.service import AlertService
    from monitor.logtail import LogTail
    from monitor.pipeline import AlertingPipeline
    from monitor.security.bruteforce import BruteForceDetector
    from monitor.security.config_watch import ConfigWatcher
    from monitor.security.cve import (
        CveScanner,
        NvdClient,
        detect_db_version,
        detect_dns_version,
        detect_smtp_version,
        detect_web_version,
    )
    from monitor.security.monitor import SecurityMonitor
    from monitor.security.traffic import TrafficDetector

    repository = PostgresRepository(settings.database_url.get_secret_value())
    notifier = EmailNotifier(
        host=settings.alert_smtp_host,
        port=settings.alert_smtp_port,
        recipients=settings.alert_email_to,
        sender=settings.alert_email_from,
        user=settings.alert_smtp_user,
        password=settings.alert_smtp_password.get_secret_value(),
    )
    alerts = AlertService(repository, notifier, settings.dashboard_url)
    security = SecurityMonitor(
        LogTail(settings.nginx_access_log),
        TrafficDetector(),
        BruteForceDetector(),
        ConfigWatcher({k: Path(v) for k, v in settings.config_watch_files.items()}, repository),
    )
    detectors = {
        "web": lambda: detect_web_version(settings.web_probe_url),
        "dns": lambda: detect_dns_version(settings.coredns_metrics_url),
        "smtp": lambda: detect_smtp_version(
            settings.smtp_host, settings.smtp_port, settings.postfix_version
        ),
    }
    if settings.lab_database_url is not None:
        lab_url = settings.lab_database_url.get_secret_value()
        detectors["db"] = lambda: detect_db_version(lab_url)
    nvd = NvdClient(settings.nvd_api_key.get_secret_value())
    scanner = CveScanner(detectors, nvd, repository, alerts)  # type: ignore[arg-type]
    if not settings.alert_email_to:
        logger.warning("ALERT_EMAIL_TO is empty: alert e-mails are disabled")
    return AlertingPipeline(alerts, security), scanner


def main() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)
    try:
        from monitor.config import get_settings

        settings = get_settings()
    except Exception as error:
        logger.error("invalid collector configuration", extra={"error_type": type(error).__name__})
        return 2

    try:
        from monitor.logtail import LogTail
        from monitor.probes.availability import build_availability_probes, targets_from_settings
        from monitor.probes.database import build_database_metrics_probe
        from monitor.probes.dns import build_dns_metrics_probes
        from monitor.probes.docker_metrics import build_docker_database_stats_probe
        from monitor.probes.smtp import build_smtp_probes
        from monitor.probes.web import build_web_probes

        availability_probes = build_availability_probes(targets_from_settings(settings))
        web_probes = build_web_probes(
            LogTail(settings.nginx_access_log),
            settings.stub_status_url,
            timeout_seconds=settings.probe_timeout_seconds,
            logger=logger,
        )
        database_url = (
            settings.lab_database_url.get_secret_value()
            if settings.lab_database_url is not None
            else ""
        )
        database_metrics_probe = build_database_metrics_probe(
            database_url,
            timeout_seconds=settings.probe_timeout_seconds,
        )
        docker_metrics_probe = build_docker_database_stats_probe()
        dns_metrics_probes = build_dns_metrics_probes(
            settings.dns_nameserver,
            settings.dns_query_name,
            settings.dns_missing_query_name,
            external_name=settings.dns_external_query_name,
            timeout_seconds=max(1, settings.probe_timeout_seconds // 5),
        )
        smtp_probes = build_smtp_probes(
            settings.smtp_host,
            settings.smtp_port,
            settings.mailhog_api_url,
            settings.smtp_probe_from,
            settings.smtp_probe_to,
            timeout_seconds=settings.smtp_probe_timeout_seconds,
        )
        probes = (
            *availability_probes,
            *web_probes,
            database_metrics_probe,
            docker_metrics_probe,
            *dns_metrics_probes,
            *smtp_probes,
        )
    except Exception as error:
        logger.error(
            "collector probe configuration is incomplete",
            extra={"error_type": type(error).__name__},
        )
        return 2

    store = PostgresStore(settings.database_url.get_secret_value())
    pipeline, cve_scanner = build_alerting(settings, logger)
    application = CollectorApplication(
        settings, store, probes=probes, post_cycle=pipeline.on_cycle
    )
    scheduler = build_scheduler(application, settings.collect_interval_seconds)
    if cve_scanner is not None:
        from datetime import timedelta

        scheduler.add_job(
            cve_scanner.run,
            "interval",
            hours=24,
            id="cve-scan",
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30),
        )
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        application.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
