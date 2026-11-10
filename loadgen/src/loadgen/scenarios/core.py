"""Shared limits, local-target validation, and lazy HTTP client creation."""

from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_TARGET = "http://127.0.0.1:8080"
MAX_HTTP_REQUESTS = 10_000
MAX_BRUTEFORCE_ATTEMPTS = 500
MAX_SMTP_MESSAGES = 1_000
MAX_DURATION_SECONDS = 60
MAX_CONCURRENCY = 100


def find_project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").is_file():
            return parent
    raise FileNotFoundError("could not find the DevOps Monitor docker-compose.yml")


def validate_http_target(target: str, allow_remote: bool = False) -> str:
    parsed = urlsplit(target)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("target must be an absolute HTTP or HTTPS URL")
    host = parsed.hostname.lower()
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host == "localhost"
    if not is_loopback and not allow_remote:
        raise ValueError("remote target refused; use --allow-remote-target to opt in")
    return target.rstrip("/")


def validate_smtp_host(host: str, allow_remote: bool = False) -> None:
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host.lower() == "localhost"
    if not is_loopback and not allow_remote:
        raise ValueError("remote SMTP host refused; use --allow-remote-target to opt in")


def check_bound(value: int, *, minimum: int, maximum: int, name: str) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def make_http_client():
    import httpx

    return httpx.Client(timeout=5.0, follow_redirects=False)
