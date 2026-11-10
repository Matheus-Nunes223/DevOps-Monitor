import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from monitor.calc import AccessLogEntry
from monitor.logtail import LogTail
from monitor.security.bruteforce import BruteForceDetector, LoginFailure, login_failures
from monitor.security.config_watch import ConfigWatcher, make_diff, sha256_text
from monitor.security.monitor import SecurityMonitor
from monitor.security.traffic import TrafficDetector

T0 = datetime(2026, 11, 9, 20, 0, 0, tzinfo=timezone.utc)


def at(n):
    return T0 + timedelta(seconds=15 * n)


# ---- traffic ---------------------------------------------------------------------
def warmed(detector=None, rps=2.0, n=20):
    detector = detector or TrafficDetector()
    for i in range(n):
        assert detector.observe(rps + (i % 3) * 0.1, Counter(), at(i)) is None
    return detector


def test_no_alert_during_warmup_or_normal_traffic():
    detector = TrafficDetector()
    assert detector.observe(500, Counter(), at(0)) is None  # not enough history yet
    warmed()


def test_spike_raises_red_with_top5_ips():
    detector = warmed()
    ips = Counter({f"10.0.0.{i}": 100 - i for i in range(8)})
    cond = detector.observe(60.0, ips, at(30))
    assert cond is not None and cond.level == "red" and cond.kind == "ddos"
    assert [i["ip"] for i in cond.details["top_ips"]] == [f"10.0.0.{i}" for i in range(5)]
    assert cond.event is not None


def test_sustained_spike_is_not_absorbed_and_event_fires_once():
    detector = warmed()
    first = detector.observe(60.0, Counter(), at(30))
    second = detector.observe(60.0, Counter(), at(31))
    assert first.event is not None
    assert second is not None and second.event is None  # still flagged, no duplicate event
    assert detector.observe(2.0, Counter(), at(32)) is None  # back to normal


def test_idle_traffic_noise_below_floor_is_ignored():
    detector = warmed(rps=0.05)
    assert detector.observe(3.0, Counter(), at(30)) is None  # 60x mean but < min_rps


def test_ratio_rule_catches_spike_on_flat_baseline():
    detector = warmed(rps=2.0)  # tiny variance
    detector2 = TrafficDetector()
    for i in range(20):
        detector2.observe(2.0, Counter(), at(i))  # stdev == 0 -> z undefined
    cond = detector2.observe(11.0, Counter(), at(30))
    assert cond is not None and cond.details["reason"] == "ratio"
    assert detector.observe(11.0, Counter(), at(30)) is not None


# ---- brute force -----------------------------------------------------------------
def fails(n, ip="172.28.0.1", user="admin"):
    return [LoginFailure(ip, user) for _ in range(n)]


def test_login_failures_filters_method_path_and_status():
    entries = [
        AccessLogEntry("1.1.1.1", 401, 1, "/login", "POST", "root"),
        AccessLogEntry("1.1.1.1", 401, 1, "/login?x=1", "POST", "root"),
        AccessLogEntry("1.1.1.1", 200, 1, "/login", "POST", "root"),
        AccessLogEntry("1.1.1.1", 401, 1, "/other", "POST", "root"),
        AccessLogEntry("1.1.1.1", 401, 1, "/login", "GET", "root"),
    ]
    assert len(login_failures(entries)) == 2


def test_ip_threshold_of_ten_in_five_minutes():
    detector = BruteForceDetector()
    assert detector.observe(at(0), fails(9, user="")) is None
    cond = detector.observe(at(1), fails(1, user=""))
    assert cond is not None and cond.level == "red" and cond.event is not None
    assert cond.details["ips"] == [{"ip": "172.28.0.1", "count": 10}]


def test_account_threshold_across_many_ips():
    detector = BruteForceDetector()
    cond = None
    for i in range(5):
        cond = detector.observe(at(i), fails(1, ip=f"9.9.9.{i}", user="admin"))
    assert cond is not None and cond.details["accounts"] == [{"user": "admin", "count": 5}]


def test_window_expires_and_alert_condition_clears():
    detector = BruteForceDetector()
    assert detector.observe(at(0), fails(12)) is not None
    assert detector.observe(at(10), []) is not None  # still within 5 min
    assert detector.observe(at(21), []) is None  # > 300 s later


def test_new_offender_creates_new_event_but_repeat_does_not():
    detector = BruteForceDetector()
    assert detector.observe(at(0), fails(12)).event is not None
    assert detector.observe(at(1), fails(1)).event is None
    assert detector.observe(at(2), fails(12, ip="8.8.8.8", user="")).event is not None


# ---- config watch -----------------------------------------------------------------
class FakeRepo:
    def __init__(self):
        self.baselines: dict[str, tuple[str, str]] = {}

    def load_baseline_contents(self):
        return dict(self.baselines)

    def insert_baseline(self, path, service_id, sha256, content):
        self.baselines[path] = (sha256, content)


def test_first_sight_initialises_baseline_without_alert(tmp_path: Path):
    file = tmp_path / "nginx.conf"
    file.write_text("worker_connections 1024;\n")
    repo = FakeRepo()
    watcher = ConfigWatcher({"nginx.conf": file}, repo)
    assert watcher.check(T0) == []
    assert repo.baselines["nginx.conf"][0] == sha256_text("worker_connections 1024;\n")


def test_change_raises_yellow_with_diff_then_clears_when_reverted(tmp_path: Path):
    file = tmp_path / "nginx.conf"
    file.write_text("a\nworker_connections 1024;\n")
    repo = FakeRepo()
    watcher = ConfigWatcher({"nginx.conf": file}, repo)
    watcher.check(T0)
    file.write_text("a\nworker_connections 1023;\n")
    cond = watcher.check(at(1))[0]
    assert cond.level == "yellow" and cond.message == "config alterada: nginx.conf"
    assert "-worker_connections 1024;" in cond.details["diff"]
    assert "+worker_connections 1023;" in cond.details["diff"]
    assert cond.details["path"] == "nginx.conf" and cond.event is not None
    assert watcher.check(at(2))[0].event is None  # same hash: no duplicate event
    file.write_text("a\nworker_connections 1024;\n")
    assert watcher.check(at(3)) == []


def test_accepting_new_baseline_stops_the_condition(tmp_path: Path):
    file = tmp_path / "Corefile"
    file.write_text("x\n")
    repo = FakeRepo()
    watcher = ConfigWatcher({"Corefile": file}, repo)
    watcher.check(T0)
    file.write_text("y\n")
    cond = watcher.check(at(1))[0]
    repo.baselines["Corefile"] = (cond.details["current_sha256"], cond.details["current_content"])
    assert watcher.check(at(2)) == []


def test_unreadable_file_is_skipped(tmp_path: Path):
    watcher = ConfigWatcher({"main.cf": tmp_path / "missing"}, FakeRepo())
    assert watcher.check(T0) == []


def test_diff_is_truncated():
    assert len(make_diff("f", "a\n" * 10, "b\n" * 5000)) < 4100


# ---- monitor (log -> detectors) ---------------------------------------------------------
def line(ip="172.28.0.1", status=200, method="GET", uri="/", user=""):
    return json.dumps({"time": "t", "remote_addr": ip, "status": status, "request_time": 0.01,
                       "request_uri": uri, "request_method": method, "user": user}) + "\n"


def test_security_monitor_end_to_end_bruteforce(tmp_path: Path):
    log = tmp_path / "access.log"
    log.write_text("")
    clock = iter(range(0, 1000, 15))
    monitor = SecurityMonitor(LogTail(log), TrafficDetector(), BruteForceDetector(), None,
                              clock=lambda: float(next(clock)))
    with log.open("a") as fh:
        fh.write("".join(line(status=401, method="POST", uri="/login", user="admin")
                         for _ in range(12)))
        fh.write("not json\n")
    report = monitor.collect(at(1))
    assert [c.kind for c in report.conditions] == ["bruteforce"]
    assert set(report.evaluated) == {"ddos", "bruteforce"}


def test_failing_detector_is_isolated_and_not_marked_evaluated(tmp_path: Path):
    class Boom:
        def check(self, now):
            raise RuntimeError("db down")

    log = tmp_path / "access.log"
    log.write_text("")
    monitor = SecurityMonitor(LogTail(log), TrafficDetector(), BruteForceDetector(), Boom(),  # type: ignore[arg-type]
                              clock=lambda: 1.0)
    report = monitor.collect(T0)
    assert "config_change" not in report.evaluated and "bruteforce" in report.evaluated
