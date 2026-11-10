"""Known-vulnerability monitoring per service (US-18, RF-17).

Detects each service's version, asks the NVD API 2.0 for CVEs of that exact CPE and
stores them in `vulnerabilities`. CVSS >= 7.0 raises a yellow alert per service.

NOTE: confirm each CPE vendor/product in the NVD CPE dictionary before the demo
(e.g. nginx is listed as `f5:nginx` in current NVD data).
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from monitor.alerts.service import AlertService
from monitor.model import ActiveCondition, ServiceId

LOGGER = logging.getLogger(__name__)

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CVSS_ALERT_THRESHOLD = 7.0
CPE_TEMPLATES: dict[ServiceId, str] = {
    "web": "cpe:2.3:a:f5:nginx:{v}:*:*:*:*:*:*:*",
    "db": "cpe:2.3:a:postgresql:postgresql:{v}:*:*:*:*:*:*:*",
    "dns": "cpe:2.3:a:coredns:coredns:{v}:*:*:*:*:*:*:*",
    "smtp": "cpe:2.3:a:postfix:postfix:{v}:*:*:*:*:*:*:*",
}


# -- version parsers (pure) -------------------------------------------------------------
def parse_nginx_version(server_header: str) -> str | None:
    match = re.search(r"nginx/(\d+\.\d+\.\d+)", server_header)
    return match.group(1) if match else None


def parse_postgres_version(version_text: str) -> str | None:
    match = re.search(r"PostgreSQL (\d+\.\d+)", version_text)
    return match.group(1) if match else None


def parse_coredns_version(metrics_text: str) -> str | None:
    match = re.search(r'coredns_build_info\{[^}]*version="([^"]+)"', metrics_text)
    return match.group(1).lstrip("v") if match else None


def parse_postfix_version(banner: str) -> str | None:
    match = re.search(r"Postfix (\d+\.\d+\.\d+)", banner)
    return match.group(1) if match else None


# -- NVD parsing (pure) -----------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Cve:
    cve_id: str
    cvss: float | None
    summary: str
    published_at: str | None


def parse_nvd_response(payload: Mapping[str, Any]) -> list[Cve]:
    result: list[Cve] = []
    for item in payload.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id")
        if not isinstance(cve_id, str):
            continue
        metrics = cve.get("metrics", {})
        score: float | None = None
        for key in ("cvssMetricV31", "cvssMetricV30"):
            entries = metrics.get(key) or []
            if entries:
                score = float(entries[0]["cvssData"]["baseScore"])
                break
        summary = next(
            (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), ""
        )
        result.append(Cve(cve_id, score, summary[:500], cve.get("published")))
    return result


class NvdClient:
    """Rate limit: 5 requests / 30 s without API key, 50 / 30 s with one."""

    def __init__(
        self,
        api_key: str = "",
        urlopen_fn: Callable[..., Any] = urlopen,
        sleep: Callable[[float], object] = time.sleep,
        timeout_seconds: int = 30,
    ) -> None:
        self._key = api_key
        self._urlopen = urlopen_fn
        self._sleep = sleep
        self._timeout = timeout_seconds
        self._interval = 0.7 if api_key else 6.5
        self._first = True

    def cves_for(self, cpe: str) -> list[Cve]:
        found: list[Cve] = []
        start = 0
        while True:
            if not self._first:
                self._sleep(self._interval)
            self._first = False
            query = urlencode({"cpeName": cpe, "resultsPerPage": 200, "startIndex": start})
            request = Request(f"{NVD_URL}?{query}")
            if self._key:
                request.add_header("apiKey", self._key)
            with self._urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read())
            found.extend(parse_nvd_response(payload))
            start += int(payload.get("resultsPerPage", 0))
            if start >= int(payload.get("totalResults", 0)) or not payload.get("resultsPerPage"):
                return found


class CveScanner:
    def __init__(
        self,
        detectors: Mapping[ServiceId, Callable[[], str | None]],
        nvd: NvdClient,
        store: Any,
        alerts: AlertService,
    ) -> None:
        self._detectors = detectors
        self._nvd = nvd
        self._store = store
        self._alerts = alerts

    def run(self, now: datetime | None = None) -> None:
        conditions: list[ActiveCondition] = []
        scanned: list[ServiceId] = []
        for service_id, detect in self._detectors.items():
            try:
                version = detect()
                if version is None:
                    LOGGER.warning(
                        "service version not detected", extra={"probe": f"cve:{service_id}"}
                    )
                    continue
                cves = self._nvd.cves_for(CPE_TEMPLATES[service_id].format(v=version))
                self._store.replace_vulnerabilities(
                    service_id,
                    version,
                    [
                        {"cve_id": c.cve_id, "cvss": c.cvss, "summary": c.summary,
                         "published_at": c.published_at}
                        for c in cves
                    ],
                )
            except (HTTPError, URLError, OSError, ValueError, KeyError) as error:
                LOGGER.error(
                    "cve scan failed",
                    extra={"probe": f"cve:{service_id}", "error_type": type(error).__name__},
                )
                continue
            scanned.append(service_id)
            condition = self._condition(service_id, version, cves)
            if condition is not None:
                conditions.append(condition)
        if scanned:
            self._alerts.sync_conditions(
                conditions, kinds=("cve",), clear_after=1, services=scanned, now=now
            )

    @staticmethod
    def _condition(service_id: ServiceId, version: str, cves: list[Cve]) -> ActiveCondition | None:
        high = sorted(
            (c for c in cves if c.cvss is not None and c.cvss >= CVSS_ALERT_THRESHOLD),
            key=lambda c: -(c.cvss or 0),
        )
        if not high:
            return None
        top = [{"cve": c.cve_id, "cvss": c.cvss} for c in high[:5]]
        return ActiveCondition(
            key=f"cve:{service_id}",
            service_id=service_id,
            kind="cve",
            level="yellow",
            message=(
                f"{len(high)} CVE(s) com CVSS ≥ 7,0 em {service_id} {version} "
                f"(maior: {high[0].cve_id}, {high[0].cvss})"
            ),
            details={"version": version, "count": len(high), "top": top},
        )


# -- live version detection (I/O) -----------------------------------------------------------
def detect_web_version(url: str, timeout: int = 5) -> str | None:
    request = Request(url, method="HEAD")
    try:
        with urlopen(request, timeout=timeout) as response:
            return parse_nginx_version(response.headers.get("Server", ""))
    except HTTPError as error:
        return parse_nginx_version(error.headers.get("Server", ""))


def detect_db_version(database_url: str) -> str | None:
    import psycopg

    with psycopg.connect(database_url, connect_timeout=5) as conn:
        row = conn.execute("select version()").fetchone()
    return parse_postgres_version(str(row[0])) if row else None


def detect_dns_version(metrics_url: str, timeout: int = 5) -> str | None:
    with urlopen(metrics_url, timeout=timeout) as response:
        return parse_coredns_version(response.read().decode("utf-8", errors="replace"))


def detect_smtp_version(host: str, port: int, fallback: str = "", timeout: int = 5) -> str | None:
    """The 220 greeting only shows the version if `smtpd_banner` includes $mail_version."""
    import smtplib

    smtp = smtplib.SMTP(timeout=timeout)
    try:
        _, message = smtp.connect(host, port)
    finally:
        smtp.close()
    greeting = message.decode("utf-8", errors="replace")
    return parse_postfix_version(greeting) or (fallback or None)
