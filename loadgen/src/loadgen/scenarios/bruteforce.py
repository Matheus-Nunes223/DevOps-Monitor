"""Bounded invalid login attempts with a synthetic account identity."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable

from loadgen.scenarios.core import (
    DEFAULT_TARGET,
    MAX_BRUTEFORCE_ATTEMPTS,
    check_bound,
    validate_http_target,
)


def run_bruteforce(
    client: object,
    target: str = DEFAULT_TARGET,
    *,
    attempts: int = 20,
    username: str = "demo-user@devops.local",
    delay_seconds: float = 0.1,
    sleep: Callable[[float], object] = time.sleep,
    allow_remote: bool = False,
) -> int:
    base = validate_http_target(target, allow_remote)
    check_bound(attempts, minimum=1, maximum=MAX_BRUTEFORCE_ATTEMPTS, name="attempts")
    if not 0 <= delay_seconds <= 10:
        raise ValueError("delay_seconds must be between 0 and 10")
    if not username.endswith(("@devops.local", "@example.test", "@invalid")):
        raise ValueError("bruteforce scenario only accepts a synthetic username domain")
    if len(username) > 64:
        raise ValueError("synthetic username cannot exceed 64 characters")
    unauthorized = 0
    for index in range(attempts):
        response = client.post(  # type: ignore[attr-defined]
            f"{base}/login",
            data={"username": username, "password": f"invalid-{index}-{secrets.token_hex(4)}"},
        )
        unauthorized += int(response.status_code == 401)
        if index + 1 < attempts and delay_seconds:
            sleep(delay_seconds)
    return unauthorized
