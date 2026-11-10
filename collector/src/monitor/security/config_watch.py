"""Configuration drift detector (US-17, RF-16).

Compares SHA-256 of each watched file with the accepted baseline stored in Supabase.
First sight of a file (no baseline yet) is trusted and stored. The operator can accept
a change from the dashboard (RPC `accept_config_baseline`), which resolves the alert.
"""

from __future__ import annotations

import difflib
import hashlib
import logging
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from monitor.alerts.repository import Repository
from monitor.model import ActiveCondition, SecurityEvent, ServiceId

LOGGER = logging.getLogger(__name__)

# Must match the allowlist in public.accept_config_baseline().
SERVICE_BY_FILE: dict[str, ServiceId] = {
    "nginx.conf": "web",
    "Corefile": "dns",
    "postgresql.conf": "db",
    "main.cf": "smtp",
}
MAX_DIFF_CHARS = 4000
MAX_CONTENT_CHARS = 65536  # keeps alerts.details small; the UI button needs the content


def sha256_text(content: str) -> str:
    # Same bytes Postgres hashes in accept_config_baseline: convert_to(content, 'UTF8').
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def make_diff(label: str, baseline: str, current: str) -> str:
    lines = difflib.unified_diff(
        baseline.splitlines(),
        current.splitlines(),
        fromfile=f"base/{label}",
        tofile=f"atual/{label}",
        lineterm="",
    )
    text = "\n".join(lines)
    return text if len(text) <= MAX_DIFF_CHARS else text[:MAX_DIFF_CHARS] + "\n… (diff truncado)"


class ConfigWatcher:
    def __init__(self, files: Mapping[str, Path], repository: Repository) -> None:
        self._files = {label: Path(path) for label, path in files.items()}
        self._repo = repository
        self._reported: dict[str, str] = {}

    def check(self, now: datetime) -> list[ActiveCondition]:
        baselines = self._repo.load_baseline_contents()
        conditions: list[ActiveCondition] = []
        for label, path in self._files.items():
            service_id = SERVICE_BY_FILE.get(label)
            if service_id is None:
                LOGGER.error("unknown watched config file", extra={"probe": label})
                continue
            try:
                content = path.read_bytes().decode("utf-8", errors="replace")
            except OSError as error:
                LOGGER.error(
                    "config file unreadable",
                    extra={"probe": f"config-watch:{label}", "error_type": type(error).__name__},
                )
                continue
            digest = sha256_text(content)
            baseline = baselines.get(label)
            if baseline is None:
                self._repo.insert_baseline(label, service_id, digest, content)
                LOGGER.info("config baseline initialised", extra={"probe": f"config-watch:{label}"})
                continue
            base_sha, base_content = baseline
            if digest == base_sha:
                self._reported.pop(label, None)
                continue
            details: dict[str, object] = {
                "path": label,
                "baseline_sha256": base_sha,
                "current_sha256": digest,
                "diff": make_diff(label, base_content, content),
            }
            if len(content) <= MAX_CONTENT_CHARS:
                details["current_content"] = content
            event = None
            if self._reported.get(label) != digest:
                event = SecurityEvent(
                    service_id,
                    "config_change",
                    {k: v for k, v in details.items() if k != "current_content"},
                    now,
                )
                self._reported[label] = digest
            conditions.append(
                ActiveCondition(
                    key=f"config:{label}",
                    service_id=service_id,
                    kind="config_change",
                    level="yellow",
                    message=f"config alterada: {label}",
                    details=details,
                    event=event,
                )
            )
        return conditions
