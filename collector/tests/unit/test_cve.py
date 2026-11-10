from datetime import datetime, timezone

from monitor.security.cve import (
    CPE_TEMPLATES,
    Cve,
    CveScanner,
    NvdClient,
    parse_coredns_version,
    parse_nginx_version,
    parse_nvd_response,
    parse_postfix_version,
    parse_postgres_version,
)

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)

NVD = {
    "resultsPerPage": 2, "totalResults": 2,
    "vulnerabilities": [
        {"cve": {"id": "CVE-2024-0001", "published": "2024-01-01T00:00:00.000",
                 "descriptions": [{"lang": "es", "value": "x"}, {"lang": "en", "value": "Bad bug"}],
                 "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}]}}},
        {"cve": {"id": "CVE-2024-0002", "descriptions": [], "metrics": {}}},
    ],
}


def test_version_parsers():
    assert parse_nginx_version("nginx/1.27.3") == "1.27.3"
    assert parse_nginx_version("Apache") is None
    assert parse_postgres_version("PostgreSQL 16.4 (Debian 16.4-1) on x86_64") == "16.4"
    assert parse_coredns_version('coredns_build_info{revision="x",version="1.11.1"} 1') == "1.11.1"
    assert parse_postfix_version("220 postfix.lab.local ESMTP Postfix 3.9.1") == "3.9.1"
    assert parse_postfix_version("220 host ESMTP Postfix (Debian)") is None


def test_parse_nvd_response_prefers_v31_and_english_summary():
    cves = parse_nvd_response(NVD)
    assert cves[0] == Cve("CVE-2024-0001", 9.8, "Bad bug", "2024-01-01T00:00:00.000")
    assert cves[1].cvss is None


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        import json
        return json.dumps(self._body).encode()


def test_nvd_client_sends_api_key_and_respects_rate_limit():
    requests, sleeps = [], []

    def fake_open(request, timeout):
        requests.append(request)
        return FakeResponse(NVD)

    client = NvdClient("KEY", fake_open, sleeps.append)
    client.cves_for("cpe:2.3:a:f5:nginx:1.0.0:*:*:*:*:*:*:*")
    client.cves_for("cpe:2.3:a:f5:nginx:1.0.1:*:*:*:*:*:*:*")
    assert requests[0].get_header("Apikey") == "KEY"
    assert "cpeName=cpe%3A2.3%3Aa%3Af5%3Anginx" in requests[0].full_url
    assert sleeps == [0.7]  # first call free, second waits
    anonymous = NvdClient("", fake_open, sleeps.append)
    anonymous.cves_for("x")
    anonymous.cves_for("y")
    assert sleeps[-1] == 6.5


class FakeStore:
    def __init__(self):
        self.rows = {}

    def replace_vulnerabilities(self, service_id, version, rows):
        self.rows[service_id] = (version, list(rows))


class FakeAlerts:
    def __init__(self):
        self.calls = []

    def sync_conditions(self, conditions, kinds, clear_after=1, services=None, now=None):
        self.calls.append((list(conditions), tuple(kinds), list(services or [])))


class FakeNvd:
    def __init__(self, cves=None, fail=False):
        self.cves, self.fail, self.asked = cves or [], fail, []

    def cves_for(self, cpe):
        if self.fail:
            raise OSError("nvd down")
        self.asked.append(cpe)
        return self.cves


def test_scanner_alerts_yellow_for_cvss_7_plus_and_stores_all():
    store, alerts = FakeStore(), FakeAlerts()
    nvd = FakeNvd([Cve("CVE-A", 9.8, "s", None), Cve("CVE-B", 5.0, "s", None)])
    CveScanner({"web": lambda: "1.27.3"}, nvd, store, alerts).run(NOW)  # type: ignore[arg-type]
    assert nvd.asked == [CPE_TEMPLATES["web"].format(v="1.27.3")]
    assert len(store.rows["web"][1]) == 2
    conditions, kinds, services = alerts.calls[0]
    assert conditions[0].level == "yellow" and conditions[0].details["count"] == 1
    assert kinds == ("cve",) and services == ["web"]


def test_scanner_only_medium_cves_means_no_alert():
    alerts = FakeAlerts()
    nvd = FakeNvd([Cve("CVE-B", 6.9, "s", None)])
    CveScanner({"web": lambda: "1.0.0"}, nvd, FakeStore(), alerts).run(NOW)  # type: ignore[arg-type]
    assert alerts.calls[0][0] == []


def test_nvd_failure_does_not_resolve_existing_alerts():
    alerts = FakeAlerts()
    CveScanner({"web": lambda: "1.0.0"}, FakeNvd(fail=True), FakeStore(), alerts).run(NOW)  # type: ignore[arg-type]
    assert alerts.calls == []  # nothing scanned -> alerts untouched


def test_undetected_version_is_skipped():
    alerts = FakeAlerts()
    CveScanner({"smtp": lambda: None}, FakeNvd(), FakeStore(), alerts).run(NOW)  # type: ignore[arg-type]
    assert alerts.calls == []
