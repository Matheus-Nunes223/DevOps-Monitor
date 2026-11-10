"""Steady, rate-limited HTTP requests to the monitored demo app."""

from __future__ import annotations

import time
from collections.abc import Callable

from loadgen.scenarios.core import (
    DEFAULT_TARGET,
    MAX_HTTP_REQUESTS,
    check_bound,
    validate_http_target,
)


def run_normal(
    client: object,
    target: str = DEFAULT_TARGET,
    *,
    requests: int = 60,
    rate_per_second: float = 2.0,
    sleep: Callable[[float], object] = time.sleep,
    allow_remote: bool = False,
) -> int:
    base = validate_http_target(target, allow_remote)
    check_bound(requests, minimum=1, maximum=MAX_HTTP_REQUESTS, name="requests")
    if not 0.1 <= rate_per_second <= 20:
        raise ValueError("rate_per_second must be between 0.1 and 20")
    interval = 1 / rate_per_second
    successful = 0
    for index in range(requests):
        response = client.get(f"{base}/")  # type: ignore[attr-defined]
        successful += int(200 <= response.status_code < 400)
        if index + 1 < requests:
            sleep(interval)
    return successful
