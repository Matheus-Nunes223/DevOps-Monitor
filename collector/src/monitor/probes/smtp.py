"""Postfix queue/log metrics and end-to-end SMTP delivery probe."""

from __future__ import annotations

import json
import re
import smtplib
import time
import uuid
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol, Self
from urllib.parse import urlencode
from urllib.request import urlopen

from monitor.model import Metric, ProbeDefinition, ProbeResult

_POSTFIX_PREFIX = re.compile(r"(?:^|\s)postfix/(?:smtp|qmgr|smtpd)\[\d+\]:")
_QUEUE_ID = re.compile(r"postfix/(?:smtp|qmgr|smtpd)\[\d+\]:\s+([A-F0-9]+):")
_STATUS = re.compile(r"\bstatus=(sent|deferred|bounced)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PostfixEvent:
    status: str | None = None
    rejected: bool = False
    timed_out: bool = False
    accepted: bool = False
    queue_id: str | None = None
    is_probe: bool = False


def parse_postfix_log(
    line: str,
    probe_sender: str = "monitor@devops.local",
    probe_recipient: str = "probe@devops.local",
) -> PostfixEvent:
    """Extract only aggregate-safe event fields from a Postfix log record."""
    if not _POSTFIX_PREFIX.search(line):
        return PostfixEvent()
    status_match = _STATUS.search(line)
    lowered = line.lower()
    accepted = "postfix/qmgr[" in lowered and "from=<" in lowered
    return PostfixEvent(
        status=status_match.group(1).lower() if status_match else None,
        rejected="reject:" in lowered,
        timed_out="timed out" in lowered or "timeout" in lowered,
        accepted=accepted,
        queue_id=(queue_match.group(1) if (queue_match := _QUEUE_ID.search(line)) else None),
        is_probe=(
            f"from=<{probe_sender.lower()}>" in lowered
            or f"to=<{probe_recipient.lower()}>" in lowered
        ),
    )


def parse_postqueue_json(output: str | bytes) -> int:
    """Count JSON Lines entries from `postqueue -j`; empty output means empty queue."""
    text = output.decode("utf-8", errors="strict") if isinstance(output, bytes) else output
    count = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("postqueue output contains invalid JSON") from error
        if not isinstance(message, dict) or not isinstance(message.get("queue_id"), str):
            raise ValueError("postqueue message has an invalid schema")
        count += 1
    return count


def parse_postfix_timestamp(line: str) -> str:
    """Remove Docker's RFC3339 log timestamp prefix when present."""
    parts = line.split(" ", 1)
    if len(parts) == 2 and re.match(r"^\d{4}-\d\d-\d\dT", parts[0]):
        return parts[1]
    return line


class HttpResponse(Protocol):
    status: int

    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> object: ...
    def read(self) -> bytes: ...


class SmtpClient(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> object: ...
    def send_message(self, message: EmailMessage) -> object: ...


class PostfixLogProbe:
    def __init__(
        self,
        read_lines: Callable[[], Iterable[str]],
        clock: Callable[[], float] = time.monotonic,
        probe_sender: str = "monitor@devops.local",
        probe_recipient: str = "probe@devops.local",
    ) -> None:
        self._read_lines = read_lines
        self._clock = clock
        self._last_read = clock()
        self._probe_sender = probe_sender
        self._probe_recipient = probe_recipient

    def collect(self) -> ProbeResult:
        now = self._clock()
        elapsed = max(now - self._last_read, 0.001)
        self._last_read = now
        events = [
            event
            for line in self._read_lines()
            if not (
                event := parse_postfix_log(
                    parse_postfix_timestamp(line), self._probe_sender, self._probe_recipient
                )
            ).is_probe
        ]
        sent = sum(event.status == "sent" for event in events)
        deferred = sum(event.status == "deferred" for event in events)
        bounced = sum(event.status == "bounced" for event in events)
        rejected = sum(event.rejected for event in events)
        timeouts = sum(event.timed_out for event in events)
        accepted = sum(event.accepted for event in events)
        attempts = sent + deferred + bounced
        observed = attempts + rejected
        metrics = (
            Metric("smtp", "smtp.delivery_rate", sent / attempts if attempts else None),
            Metric("smtp", "smtp.reject_rate", rejected / observed if observed else None),
            Metric(
                "smtp", "smtp.timeout_rate",
                min(timeouts, observed) / observed if observed else None,
            ),
            Metric("smtp", "smtp.volume_per_min", accepted * 60 / elapsed),
            Metric("smtp", "smtp.volume_per_hour", accepted * 3600 / elapsed),
        )
        return ProbeResult(metrics=metrics)


class PostfixDockerLogReader:
    """Fetch recent stdout through the narrowly allowlisted local Docker proxy."""

    def __init__(
        self,
        proxy_url: str = "http://docker-stats-proxy:2375/postfix-logs",
        clock: Callable[[], float] = time.time,
        urlopen_fn: Callable[..., HttpResponse] = urlopen,
        overlap_seconds: int = 2,
    ) -> None:
        self._url = proxy_url
        self._clock = clock
        self._urlopen = urlopen_fn
        self._overlap = overlap_seconds
        self._last_read = clock() - 15
        self._seen: deque[str] = deque(maxlen=2048)
        self._seen_set: set[str] = set()

    def read_lines(self) -> tuple[str, ...]:
        now = self._clock()
        since = max(0, int(self._last_read) - self._overlap)
        with self._urlopen(f"{self._url}?since={since}", timeout=3) as response:
            if response.status != 200:
                raise ValueError("Postfix logs endpoint returned non-200 response")
            body = response.read().decode("utf-8", errors="replace")
        self._last_read = now
        lines: list[str] = []
        for line in body.splitlines():
            fingerprint = line.strip()
            if not fingerprint or fingerprint in self._seen_set:
                continue
            if len(self._seen) == self._seen.maxlen:
                self._seen_set.discard(self._seen[0])
            self._seen.append(fingerprint)
            self._seen_set.add(fingerprint)
            lines.append(line)
        return tuple(lines)


class PostfixQueueReader:
    def __init__(
        self,
        url: str = "http://docker-stats-proxy:2375/postfix-queue",
        urlopen_fn: Callable[..., HttpResponse] = urlopen,
    ) -> None:
        self._url = url
        self._urlopen = urlopen_fn

    def queue_length(self) -> int:
        with self._urlopen(self._url, timeout=3) as response:
            if response.status != 200:
                raise ValueError("Postfix queue endpoint returned non-200 response")
            return parse_postqueue_json(response.read())


class PostfixQueueProbe:
    def __init__(self, read_queue: Callable[[], int]) -> None:
        self._read_queue = read_queue

    def collect(self) -> ProbeResult:
        metric = Metric("smtp", "smtp.queue_length", float(self._read_queue()))
        return ProbeResult(metrics=(metric,))


class SmtpDeliveryProbe:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        mailhog_api_url: str,
        sender: str,
        recipient: str,
        timeout_seconds: float = 6.0,
        smtp_factory: Callable[..., SmtpClient] = smtplib.SMTP,
        urlopen_fn: Callable[..., HttpResponse] = urlopen,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], object] = time.sleep,
    ) -> None:
        self._host = smtp_host
        self._port = smtp_port
        self._api = mailhog_api_url.rstrip("/") + "/api/v2/search"
        self._sender = sender
        self._recipient = recipient
        self._timeout = timeout_seconds
        self._smtp_factory = smtp_factory
        self._urlopen = urlopen_fn
        self._clock = clock
        self._sleep = sleep

    def _message_arrived(self, token: str) -> bool:
        query = urlencode({"kind": "containing", "query": token, "limit": 1})
        with self._urlopen(f"{self._api}?{query}", timeout=2) as response:
            if response.status != 200:
                raise ValueError("MailHog search returned non-200 response")
            payload = json.loads(response.read())
        return isinstance(payload, dict) and int(payload.get("total", 0)) > 0

    def collect(self) -> ProbeResult:
        token = uuid.uuid4().hex
        started = self._clock()
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = self._recipient
        message["Subject"] = f"DevOps Monitor SMTP probe {token}"
        message["Message-ID"] = f"<devops-monitor-{token}@monitor.local>"
        message.set_content(f"SMTP delivery probe token: {token}")
        with self._smtp_factory(self._host, self._port, timeout=self._timeout) as client:
            client.send_message(message)

        deadline = started + self._timeout
        while self._clock() < deadline:
            if self._message_arrived(token):
                elapsed_ms = (self._clock() - started) * 1000
                return ProbeResult(
                    metrics=(Metric("smtp", "smtp.send_latency_ms", elapsed_ms),)
                )
            self._sleep(0.2)
        raise TimeoutError("SMTP probe message did not arrive in MailHog")


def build_smtp_probes(
    smtp_host: str,
    smtp_port: int,
    mailhog_api_url: str,
    sender: str,
    recipient: str,
    timeout_seconds: float = 6.0,
    log_reader: PostfixDockerLogReader | None = None,
    queue_reader: PostfixQueueReader | None = None,
    smtp_factory: Callable[..., SmtpClient] = smtplib.SMTP,
    urlopen_fn: Callable[..., HttpResponse] = urlopen,
) -> tuple[ProbeDefinition, ...]:
    logs = PostfixLogProbe(
        (log_reader or PostfixDockerLogReader(urlopen_fn=urlopen_fn)).read_lines,
        probe_sender=sender,
        probe_recipient=recipient,
    )
    queue = PostfixQueueProbe(
        (queue_reader or PostfixQueueReader(urlopen_fn=urlopen_fn)).queue_length
    )
    delivery = SmtpDeliveryProbe(
        smtp_host,
        smtp_port,
        mailhog_api_url,
        sender,
        recipient,
        timeout_seconds=timeout_seconds,
        smtp_factory=smtp_factory,
        urlopen_fn=urlopen_fn,
    )
    return (
        ProbeDefinition(
            "smtp-logs",
            "smtp",
            (
                "smtp.delivery_rate",
                "smtp.reject_rate",
                "smtp.timeout_rate",
                "smtp.volume_per_min",
                "smtp.volume_per_hour",
            ),
            "protocol",
            logs.collect,
        ),
        ProbeDefinition("smtp-queue", "smtp", ("smtp.queue_length",), "protocol", queue.collect),
        ProbeDefinition(
            "smtp-delivery-probe",
            "smtp",
            ("smtp.send_latency_ms",),
            "protocol",
            delivery.collect,
        ),
    )
