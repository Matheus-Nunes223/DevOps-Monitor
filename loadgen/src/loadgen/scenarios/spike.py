"""Finite concurrent burst against the monitored HTTP service."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from loadgen.scenarios.core import (
    DEFAULT_TARGET,
    MAX_CONCURRENCY,
    MAX_HTTP_REQUESTS,
    check_bound,
    validate_http_target,
)


def run_spike(
    client: object,
    target: str = DEFAULT_TARGET,
    *,
    requests: int = 200,
    concurrency: int = 20,
    allow_remote: bool = False,
) -> int:
    base = validate_http_target(target, allow_remote)
    check_bound(requests, minimum=1, maximum=MAX_HTTP_REQUESTS, name="requests")
    check_bound(concurrency, minimum=1, maximum=MAX_CONCURRENCY, name="concurrency")

    def send_one(_: int) -> int:
        response = client.get(f"{base}/")  # type: ignore[attr-defined]
        return int(200 <= response.status_code < 400)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        return sum(executor.map(send_one, range(requests)))
