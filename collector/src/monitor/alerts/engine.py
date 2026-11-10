"""Pure alert-rule evaluation with N-cycle hysteresis (US-13, RF-11/RF-12).

No I/O here: feed values in, get level transitions out. This keeps the rules
testable with plain value sequences.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from monitor.model import AlertRule, Level, Operator

LEVEL_ORDER: dict[Level, int] = {"green": 0, "yellow": 1, "red": 2}

MetricKey = tuple[str, str]  # (service_id, metric)


def worst_level(levels: Iterable[Level]) -> Level:
    result: Level = "green"
    for level in levels:
        if LEVEL_ORDER[level] > LEVEL_ORDER[result]:
            result = level
    return result


def violates(value: float, operator: Operator, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    if operator == "<":
        return value < threshold
    if operator == ">=":
        return value >= threshold
    raise ValueError(f"unsupported operator: {operator}")


def classify(value: float, rule: AlertRule) -> Level:
    """Raw (pre-hysteresis) level of one sample against one rule."""
    if violates(value, rule.operator, rule.crit_threshold):
        return "red"
    if violates(value, rule.operator, rule.warn_threshold):
        return "yellow"
    return "green"


@dataclass(frozen=True, slots=True)
class Transition:
    rule: AlertRule
    previous: Level
    current: Level
    value: float


@dataclass(slots=True)
class _RuleState:
    level: Level = "green"  # confirmed level
    candidate: Level = "green"  # level seen in the latest samples
    streak: int = 0  # consecutive samples at `candidate`


class AlertEngine:
    """Tracks one state machine per rule.

    A level only changes after `rule.consecutive_cycles` consecutive samples at the
    new level. A missing sample (value is None) neither confirms nor resets a streak:
    availability is covered by the `<svc>.up` rules instead.

    `<svc>.up` rules are the exception: their value already counts consecutive failed
    checks (warn = 1, crit = 2), so hysteresis is built in and no extra streak is needed.
    """

    def __init__(self, rules: Iterable[AlertRule]) -> None:
        self._rules: dict[int, AlertRule] = {rule.id: rule for rule in rules}
        self._states: dict[int, _RuleState] = {rule_id: _RuleState() for rule_id in self._rules}

    @property
    def rules(self) -> tuple[AlertRule, ...]:
        return tuple(self._rules.values())

    def restore(self, confirmed_levels: Mapping[int, Level]) -> None:
        """Rebuild state after a restart from the alerts that are still open."""
        for rule_id, level in confirmed_levels.items():
            rule = self._rules.get(rule_id)
            if rule is None:
                continue
            state = self._states[rule_id]
            state.level = level
            state.candidate = level
            state.streak = rule.consecutive_cycles

    def level_of(self, rule_id: int) -> Level:
        return self._states[rule_id].level

    def levels_by_service(self) -> dict[str, Level]:
        result: dict[str, Level] = {}
        for rule in self._rules.values():
            current = result.get(rule.service_id, "green")
            result[rule.service_id] = worst_level((current, self._states[rule.id].level))
        return result

    def evaluate(self, values: Mapping[MetricKey, float | None]) -> list[Transition]:
        transitions: list[Transition] = []
        for rule in self._rules.values():
            value = values.get((rule.service_id, rule.metric))
            if value is None:
                continue
            state = self._states[rule.id]
            raw = classify(value, rule)
            if raw == state.candidate:
                state.streak += 1
            else:
                state.candidate = raw
                state.streak = 1
            needed = 1 if rule.metric.endswith(".up") else rule.consecutive_cycles
            if state.streak >= needed and state.candidate != state.level:
                previous = state.level
                state.level = state.candidate
                transitions.append(Transition(rule, previous, state.level, value))
        return transitions
