"""Temporarily stop and restore a running monitored Compose service."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from loadgen.scenarios.core import MAX_DURATION_SECONDS, check_bound, find_project_root

ALLOWED_SERVICES = ("nginx", "postgres", "coredns", "postfix")
PROJECT_ROOT = find_project_root()


def _compose_command(arguments: list[str]) -> str:
    result = subprocess.run(
        arguments,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_stop_service(
    service: str,
    *,
    duration_seconds: int = 10,
    confirm: bool = False,
    command: Callable[[list[str]], str] = _compose_command,
    sleep: Callable[[float], object] = time.sleep,
) -> None:
    if not confirm:
        raise PermissionError("stop_service requires explicit fault confirmation")
    if service not in ALLOWED_SERVICES:
        raise ValueError("service is not an allowed monitored Compose target")
    check_bound(
        duration_seconds, minimum=1, maximum=MAX_DURATION_SECONDS, name="duration_seconds"
    )
    running = command(["docker", "compose", "ps", "--status", "running", "-q", service])
    if not running.strip():
        raise RuntimeError("service was not running before the scenario; refusing state change")
    try:
        command(["docker", "compose", "stop", service])
        sleep(duration_seconds)
    finally:
        command(["docker", "compose", "start", service])
