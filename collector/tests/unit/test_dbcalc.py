from __future__ import annotations

import unittest

from monitor.dbcalc import CounterSnapshot, counter_rates, growth_gb_per_day


class DatabaseCalculationTests(unittest.TestCase):
    def test_calculates_rates_from_monotonic_counter_deltas(self) -> None:
        before = CounterSnapshot(
            commits=120, rollbacks=10, deadlocks=4, statements=900, slow_calls=30
        )
        after = CounterSnapshot(
            commits=180, rollbacks=15, deadlocks=6, statements=1050, slow_calls=36
        )

        rates = counter_rates(before, after, elapsed_seconds=30)

        self.assertAlmostEqual(rates.qps, 5.0)
        self.assertAlmostEqual(rates.rollback_rate, 5 / 65)
        self.assertAlmostEqual(rates.xact_failure_rate, 2 / 65)
        self.assertAlmostEqual(rates.slow_queries_per_min, 12.0)

    def test_counter_reset_returns_missing_rates(self) -> None:
        before = CounterSnapshot(
            commits=100, rollbacks=4, deadlocks=2, statements=90, slow_calls=9
        )
        after = CounterSnapshot(
            commits=2, rollbacks=0, deadlocks=0, statements=1, slow_calls=0
        )

        rates = counter_rates(before, after, elapsed_seconds=15)

        self.assertIsNone(rates.qps)
        self.assertIsNone(rates.rollback_rate)

    def test_zero_duration_has_missing_rates(self) -> None:
        snapshot = CounterSnapshot(1, 0, 0, 1, 0)
        self.assertIsNone(counter_rates(snapshot, snapshot, elapsed_seconds=0).qps)

    def test_linear_growth_uses_gigabytes_per_day(self) -> None:
        self.assertAlmostEqual(
            growth_gb_per_day([(0, 0), (86400, 1024**3)]),
            1.0,
        )

    def test_growth_needs_two_distinct_time_samples(self) -> None:
        self.assertIsNone(growth_gb_per_day([(10, 100), (10, 200)]))
        self.assertIsNone(growth_gb_per_day([(10, 100)]))


if __name__ == "__main__":
    unittest.main()
