"""Apply a reversible Nginx config change and reload the Compose service."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from loadgen.scenarios.core import MAX_DURATION_SECONDS, check_bound, find_project_root

PROJECT_ROOT = find_project_root()
CONFIG_PATH = PROJECT_ROOT / "infra" / "nginx" / "nginx.conf"
ORIGINAL_DIRECTIVE = b"worker_connections 1024;"
CHANGED_DIRECTIVE = b"worker_connections 1023;"


def _compose_command(arguments: list[str]) -> str:
    result = subprocess.run(
        arguments,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_edit_config(
    config_path: Path = CONFIG_PATH,
    *,
    project_root: Path = PROJECT_ROOT,
    duration_seconds: int = 10,
    confirm: bool = False,
    command: Callable[[list[str]], str] = _compose_command,
    sleep: Callable[[float], object] = time.sleep,
) -> None:
    if not confirm:
        raise PermissionError("edit_config requires explicit fault confirmation")
    expected_path = (project_root / "infra" / "nginx" / "nginx.conf").resolve()
    if config_path.resolve() != expected_path:
        raise ValueError("edit_config can only modify infra/nginx/nginx.conf")
    check_bound(
        duration_seconds, minimum=1, maximum=MAX_DURATION_SECONDS, name="duration_seconds"
    )
    original = config_path.read_bytes()
    if original.count(ORIGINAL_DIRECTIVE) != 1:
        raise ValueError("expected exactly one known worker_connections directive")
    changed = original.replace(ORIGINAL_DIRECTIVE, CHANGED_DIRECTIVE, 1)
    reload_attempted = False
    try:
        config_path.write_bytes(changed)
        command(["docker", "compose", "exec", "-T", "nginx", "nginx", "-t"])
        reload_attempted = True
        command(["docker", "compose", "exec", "-T", "nginx", "nginx", "-s", "reload"])
        sleep(duration_seconds)
    finally:
        config_path.write_bytes(original)
        if reload_attempted:
            command(["docker", "compose", "exec", "-T", "nginx", "nginx", "-t"])
            command(["docker", "compose", "exec", "-T", "nginx", "nginx", "-s", "reload"])
