from monitor.alerts.engine import AlertEngine, classify, violates, worst_level
from monitor.model import AlertRule

LAT = AlertRule(1, "web", "web.latency_p95_ms", ">", 500, 2000, 2)
UP = AlertRule(2, "web", "web.up", ">=", 1, 2, 2)
SMTP_DELIVERY = AlertRule(3, "smtp", "smtp.delivery_rate", "<", 0.95, 0.80, 2)


def feed(engine, service, metric, values):
    out = []
    for value in values:
        out.extend(engine.evaluate({(service, metric): value}))
    return out


def test_operators_and_classification():
    assert violates(5, ">", 4) and not violates(4, ">", 4)
    assert violates(4, ">=", 4) and violates(3, "<", 4)
    assert classify(100, LAT) == "green"
    assert classify(600, LAT) == "yellow"
    assert classify(2500, LAT) == "red"
    assert classify(0.9, SMTP_DELIVERY) == "yellow"
    assert classify(0.5, SMTP_DELIVERY) == "red"


def test_level_changes_only_after_two_consecutive_cycles():
    engine = AlertEngine([LAT])
    transitions = feed(engine, "web", "web.latency_p95_ms", [600, 100, 600, 600])
    assert [t.current for t in transitions] == ["yellow"]  # lone spike ignored
    assert transitions[0].previous == "green"


def test_yellow_to_red_to_green_cycle():
    engine = AlertEngine([LAT])
    transitions = feed(engine, "web", "web.latency_p95_ms", [600, 600, 2500, 2500, 100, 100])
    assert [(t.previous, t.current) for t in transitions] == [
        ("green", "yellow"),
        ("yellow", "red"),
        ("red", "green"),
    ]


def test_sequence_yellow_then_red_never_confirms_yellow():
    engine = AlertEngine([LAT])
    transitions = feed(engine, "web", "web.latency_p95_ms", [600, 2500, 2500])
    assert [(t.previous, t.current) for t in transitions] == [("green", "red")]


def test_missing_value_does_not_reset_or_confirm():
    engine = AlertEngine([LAT])
    transitions = feed(engine, "web", "web.latency_p95_ms", [600, None, 600])
    assert [t.current for t in transitions] == ["yellow"]


def test_up_rule_uses_failure_counter_without_extra_hysteresis():
    engine = AlertEngine([UP])
    transitions = feed(engine, "web", "web.up", [0, 1, 2, 0])
    assert [(t.previous, t.current) for t in transitions] == [
        ("green", "yellow"),
        ("yellow", "red"),
        ("red", "green"),
    ]


def test_restore_keeps_open_alert_level_without_new_transition():
    engine = AlertEngine([LAT])
    engine.restore({1: "red"})
    assert engine.level_of(1) == "red"
    assert feed(engine, "web", "web.latency_p95_ms", [2500]) == []


def test_service_level_is_worst_rule_level():
    engine = AlertEngine([LAT, UP])
    feed(engine, "web", "web.latency_p95_ms", [600, 600])
    assert engine.levels_by_service() == {"web": "yellow"}
    feed(engine, "web", "web.up", [2])
    assert engine.levels_by_service() == {"web": "red"}
    assert worst_level([]) == "green"
