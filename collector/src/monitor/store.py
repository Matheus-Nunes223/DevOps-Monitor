"""Batch persistence for collected metrics and service states."""

import json
import logging
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol, Self

from monitor.model import CollectionBatch, Metric, ServiceStatus

LOGGER = logging.getLogger(__name__)

METRIC_INSERT = """
INSERT INTO public.metrics (service_id, metric, value, labels, collected_at)
VALUES (%s, %s, %s, %s::jsonb, %s)
""".strip()

STATUS_INSERT = """
INSERT INTO public.service_status (service_id, up, check_kind, latency_ms, error, collected_at)
VALUES (%s, %s, %s, %s, %s, %s)
""".strip()


class Cursor(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def executemany(self, query: str, params_seq: Iterable[Sequence[object]]) -> object: ...


class Connection(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
    def cursor(self) -> Cursor: ...


Connector = Callable[[str], Connection]


def _metric_row(metric: Metric) -> tuple[object, ...]:
    labels_json = json.dumps(
        metric.labels,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (metric.service_id, metric.metric, metric.value, labels_json, metric.collected_at)


def _status_row(status: ServiceStatus) -> tuple[object, ...]:
    return (
        status.service_id,
        status.up,
        status.check_kind,
        status.latency_ms,
        status.error,
        status.collected_at,
    )


class PostgresStore:
    """Write one cycle's rows atomically using Psycopg 3."""

    def __init__(self, database_url: str, connector: Connector | None = None) -> None:
        self._database_url = database_url
        if connector is None:
            try:
                import psycopg
            except ImportError as error:
                raise RuntimeError(
                    "Install the collector dependencies to enable PostgreSQL storage"
                ) from error
            connector = psycopg.connect
        self._connector = connector

    def write(self, batch: CollectionBatch) -> None:
        if not batch.metrics and not batch.statuses:
            return

        metrics = [_metric_row(metric) for metric in batch.metrics]
        statuses = [_status_row(status) for status in batch.statuses]
        try:
            with self._connector(self._database_url) as connection:
                with connection.cursor() as cursor:
                    if metrics:
                        cursor.executemany(METRIC_INSERT, metrics)
                    if statuses:
                        cursor.executemany(STATUS_INSERT, statuses)
        except Exception as error:
            LOGGER.error(
                "batch persistence failed",
                extra={
                    "error_type": type(error).__name__,
                    "metric_count": len(metrics),
                    "status_count": len(statuses),
                },
            )
            raise
