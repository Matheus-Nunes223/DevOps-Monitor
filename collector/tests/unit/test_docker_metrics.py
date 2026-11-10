from __future__ import annotations

import unittest

from monitor.probes.docker_metrics import DockerDatabaseStatsProbe, calculate_cpu_percent


def stats(cpu_total: int, system_total: int, memory: int, read: int, write: int) -> dict:
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": cpu_total, "percpu_usage": [cpu_total]},
            "system_cpu_usage": system_total,
            "online_cpus": 2,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": cpu_total - 10, "percpu_usage": [cpu_total - 10]},
            "system_cpu_usage": system_total - 100,
            "online_cpus": 2,
        },
        "memory_stats": {"usage": memory, "stats": {"inactive_file": 100}},
        "blkio_stats": {
            "io_service_bytes_recursive": [
                {"op": "Read", "value": read},
                {"op": "Write", "value": write},
            ]
        },
    }


class FakeClient:
    def __init__(self, sequence: list[dict]) -> None:
        self.sequence = iter(sequence)
        self.calls: list[dict] = []

    def stats(self, container: str, **kwargs: object) -> dict:
        self.calls.append({"container": container, **kwargs})
        return next(self.sequence)


class DockerStatsTests(unittest.TestCase):
    def test_cpu_percent_calculation(self) -> None:
        self.assertAlmostEqual(
            calculate_cpu_percent(
                {"cpu_usage": {"total_usage": 150}, "system_cpu_usage": 1100,
                 "online_cpus": 2},
                {"cpu_usage": {"total_usage": 100}, "system_cpu_usage": 1000},
            ),
            100.0,
        )

    def test_collects_one_shot_stats_and_rates(self) -> None:
        client = FakeClient(
            [stats(110, 1100, 1024, 100, 200), stats(160, 1200, 2048, 300, 500)]
        )
        ticks = iter((0.0, 10.0))
        probe = DockerDatabaseStatsProbe(client=client, clock=lambda: next(ticks))

        first = {metric.metric: metric.value for metric in probe.collect().metrics}
        second = {metric.metric: metric.value for metric in probe.collect().metrics}

        self.assertAlmostEqual(first["db.cpu_percent"], 20.0)
        self.assertAlmostEqual(second["db.cpu_percent"], 20.0)
        self.assertEqual(second["db.mem_bytes"], 1948.0)
        self.assertEqual(second["db.io_read_bps"], 20.0)
        self.assertEqual(second["db.io_write_bps"], 30.0)
        self.assertEqual(
            client.calls,
            [
                {"container": "devops-monitor-postgres", "stream": False},
                {"container": "devops-monitor-postgres", "stream": False},
            ],
        )

if __name__ == "__main__":
    unittest.main()
