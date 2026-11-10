import unittest

from monitor.main import build_scheduler


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append((func, trigger, kwargs))


class FakeApplication:
    def run_cycle(self):
        pass


class SchedulerTests(unittest.TestCase):
    def test_cycle_is_interval_scheduled_without_overlap(self):
        scheduler = FakeScheduler()
        result = build_scheduler(FakeApplication(), 15, scheduler)

        self.assertIs(result, scheduler)
        self.assertEqual(len(scheduler.jobs), 1)
        _, trigger, options = scheduler.jobs[0]
        self.assertEqual(trigger, "interval")
        self.assertEqual(options["seconds"], 15)
        self.assertEqual(options["max_instances"], 1)
        self.assertTrue(options["coalesce"])


if __name__ == "__main__":
    unittest.main()
