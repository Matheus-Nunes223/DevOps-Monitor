from datetime import datetime, timedelta, timezone

from monitor.alerts.service import AlertService, UpTracker
from monitor.model import (
    ActiveCondition,
    AlertRule,
    CollectionBatch,
    Metric,
    OpenAlert,
    SecurityEvent,
    ServiceStatus,
)

T0 = datetime(2026, 11, 9, 20, 0, 0, tzinfo=timezone.utc)
RULES = [
    AlertRule(1, "web", "web.up", ">=", 1, 2, 2),
    AlertRule(2, "web", "web.latency_p95_ms", ">", 500, 2000, 2),
]


class FakeRepo:
    def __init__(self):
        self.alerts: dict[int, dict] = {}
        self.events: list[SecurityEvent] = []
        self.levels: dict[str, str] = {}
        self._id = 0

    def load_rules(self):
        return list(RULES)

    def fetch_open_alerts(self):
        return [
            OpenAlert(a["id"], a["rule_id"], a["service_id"], a["kind"], a["level"], a["message"],
                      a["value"], a["details"], a["opened_at"], a.get("last_notified_at"))
            for a in self.alerts.values() if a["status"] == "open"
        ]

    def open_alert(self, *, rule_id, service_id, kind, level, value, message, details, opened_at):
        self._id += 1
        self.alerts[self._id] = dict(id=self._id, rule_id=rule_id, service_id=service_id,
                                     kind=kind, level=level, value=value, message=message,
                                     details=dict(details), opened_at=opened_at, status="open")
        return self._id

    def resolve_alert(self, alert_id, resolved_at):
        self.alerts[alert_id]["status"] = "resolved"

    def mark_notified(self, alert_id, notified_at):
        self.alerts[alert_id]["last_notified_at"] = notified_at

    def set_service_level(self, service_id, level):
        self.levels[service_id] = level

    def insert_security_event(self, event):
        self.events.append(event)


class FakeNotifier:
    def __init__(self, ok=True):
        self.subjects: list[str] = []
        self.ok = ok

    def send(self, email):
        self.subjects.append(email.subject)
        return self.ok


def down(at):
    return CollectionBatch(statuses=(ServiceStatus("web", False, "protocol", None, "x", at),))


def up(at):
    return CollectionBatch(statuses=(ServiceStatus("web", True, "protocol", 3.0, None, at),))


def make(ok=True):
    repo, notifier = FakeRepo(), FakeNotifier(ok)
    return AlertService(repo, notifier, "http://p"), repo, notifier


def test_up_tracker_counts_consecutive_protocol_failures_only():
    tracker = UpTracker()
    icmp = CollectionBatch(statuses=(ServiceStatus("web", False, "icmp", None, "x", T0),))
    assert tracker.update(icmp) == {}
    assert tracker.update(down(T0)) == {("web", "web.up"): 1.0}
    assert tracker.update(down(T0)) == {("web", "web.up"): 2.0}
    assert tracker.update(up(T0)) == {("web", "web.up"): 0.0}


def test_web_down_and_back_sends_critical_then_resolved():
    service, repo, notifier = make()
    service.process_cycle(down(T0), now=T0)
    assert notifier.subjects == ["[ATENÇÃO] web com falhas de verificação"]
    service.process_cycle(down(T0), now=T0 + timedelta(seconds=15))
    assert notifier.subjects[-1] == "[CRÍTICO] web indisponível"
    assert repo.levels["web"] == "red"
    assert [a["status"] for a in repo.alerts.values()] == ["resolved", "open"]
    service.process_cycle(up(T0), now=T0 + timedelta(seconds=30))
    assert notifier.subjects[-1] == "[RESOLVIDO] web"
    assert repo.levels["web"] == "green"
    assert all(a["status"] == "resolved" for a in repo.alerts.values())


def test_red_alert_is_resent_every_ten_minutes_not_before():
    service, repo, notifier = make()
    service.process_cycle(down(T0), now=T0)
    service.process_cycle(down(T0), now=T0 + timedelta(seconds=15))
    sent = len(notifier.subjects)
    service.process_cycle(down(T0), now=T0 + timedelta(minutes=5))
    assert len(notifier.subjects) == sent
    service.process_cycle(down(T0), now=T0 + timedelta(minutes=11))
    assert notifier.subjects[-1].endswith("(lembrete)")


def test_failed_email_is_retried_next_cycle():
    service, repo, notifier = make(ok=False)
    service.process_cycle(down(T0), now=T0)
    first = len(notifier.subjects)
    service.process_cycle(down(T0), now=T0 + timedelta(seconds=15))
    assert len(notifier.subjects) > first  # still unnotified -> retried


def condition(key="bruteforce", event=True):
    return ActiveCondition(
        key=key, service_id="web", kind="bruteforce", level="red", message="brute",
        details={"ips": [{"ip": "1.1.1.1", "count": 12}]},
        event=SecurityEvent("web", "bruteforce", {"ips": []}, T0) if event else None,
    )


def test_security_condition_opens_alert_event_and_email_then_clears_after_two_cycles():
    service, repo, notifier = make()
    service.process_cycle(up(T0), [condition()], T0)
    assert len(repo.events) == 1
    opened = [a for a in repo.alerts.values() if a["kind"] == "bruteforce"]
    assert opened and opened[0]["details"]["key"] == "bruteforce"
    assert notifier.subjects[-1].startswith("[CRÍTICO] web: brute-force")
    assert repo.levels["web"] == "red"

    service.process_cycle(up(T0), [condition(event=False)], T0 + timedelta(seconds=15))
    assert len([a for a in repo.alerts.values() if a["kind"] == "bruteforce"]) == 1  # no duplicate

    service.process_cycle(up(T0), [], T0 + timedelta(seconds=30))
    assert opened[0]["status"] == "open"  # one quiet cycle is not enough
    service.process_cycle(up(T0), [], T0 + timedelta(seconds=45))
    assert opened[0]["status"] == "resolved"
    assert notifier.subjects[-1].startswith("[RESOLVIDO] web")
    assert repo.levels["web"] == "green"


def test_detector_that_did_not_run_never_resolves_its_alert():
    service, repo, _ = make()
    cond = ActiveCondition("config:nginx.conf", "web", "config_change", "yellow", "cfg",
                           {"path": "nginx.conf"})
    service.process_cycle(up(T0), [cond], T0)
    for i in range(1, 5):  # config watcher failed: not in evaluated kinds
        service.process_cycle(up(T0), [], T0 + timedelta(seconds=15 * i), evaluated_kinds=("ddos",))
    assert any(a["kind"] == "config_change" and a["status"] == "open" for a in repo.alerts.values())


def test_sync_conditions_limited_to_scanned_services():
    service, repo, _ = make()
    cve = ActiveCondition("cve:web", "web", "cve", "yellow", "cve", {})
    service.sync_conditions([cve], kinds=("cve",), now=T0)
    service.sync_conditions([], kinds=("cve",), services=("db",), now=T0)  # web not scanned
    assert any(a["kind"] == "cve" and a["status"] == "open" for a in repo.alerts.values())
    service.sync_conditions([], kinds=("cve",), services=("web",), now=T0)
    assert all(a["status"] == "resolved" for a in repo.alerts.values() if a["kind"] == "cve")


def test_labeled_metrics_do_not_feed_rules():
    service, repo, notifier = make()
    batch = CollectionBatch(metrics=(
        Metric("web", "web.latency_p95_ms", 3000, {}, T0),
        Metric("web", "web.status_count", 9999, {"code": "500"}, T0),
    ))
    service.process_cycle(batch, now=T0)
    service.process_cycle(batch, now=T0 + timedelta(seconds=15))
    assert repo.levels["web"] == "red"
