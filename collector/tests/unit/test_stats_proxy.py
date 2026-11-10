from __future__ import annotations

import json
import unittest
from unittest.mock import call, patch

from infra.docker_stats_proxy.server import (
    allowed_postfix_logs_path,
    allowed_stats_path,
    postfix_queue_output,
)


class StatsProxyAllowlistTests(unittest.TestCase):
    def test_allows_only_fixed_container_non_stream_stats_get_path(self) -> None:
        self.assertTrue(
            allowed_stats_path("/v1.41/containers/devops-monitor-postgres/stats?stream=false")
        )
        self.assertTrue(allowed_stats_path("/v1.41/containers/devops-monitor-postgres/stats"))

    def test_rejects_other_docker_api_operations(self) -> None:
        rejected = (
            "/v1.41/containers/json",
            "/v1.41/containers/devops-monitor-postgres/json",
            "/v1.41/containers/devops-monitor-postgres/archive?path=/",
            "/v1.41/containers/devops-monitor-postgres/stats?stream=true",
            "/v1.41/containers/devops-monitor-postgres/stats?stream=false&stream=true",
            "/v1.41/containers/other/stats?stream=false",
            "/containers/devops-monitor-postgres/stats?stream=false",
        )
        for path in rejected:
            with self.subTest(path=path):
                self.assertFalse(allowed_stats_path(path))

    def test_postfix_logs_route_is_fixed_to_stdout_and_container(self) -> None:
        allowed = (
            "/v1.41/containers/devops-monitor-postfix/logs?stdout=1&stderr=0"
            "&timestamps=1&since=123&follow=False&tail=all"
        )
        self.assertTrue(allowed_postfix_logs_path(allowed))
        rejected = (
            allowed.replace("stderr=0", "stderr=1"),
            allowed.replace("since=123", "since=../../etc/passwd"),
            allowed.replace("devops-monitor-postfix", "other-container"),
            allowed.replace("tail=all", "tail=all&details=true"),
        )
        for path in rejected:
            with self.subTest(path=path):
                self.assertFalse(allowed_postfix_logs_path(path))

    def test_queue_exec_uses_only_fixed_non_mutating_command(self) -> None:
        responses = [
            (201, b'{"Id":"abc123"}', "application/json"),
            (200, b"{\"queue_id\":\"Q1\"}\n", "application/json"),
            (200, b'{"ExitCode":0}', "application/json"),
        ]
        with patch(
            "infra.docker_stats_proxy.server.docker_request", side_effect=responses
        ) as request:
            self.assertEqual(postfix_queue_output(), b'{"queue_id":"Q1"}\n')

        create_call = request.call_args_list[0]
        self.assertEqual(
            create_call.args[:2],
            ("POST", "/v1.41/containers/devops-monitor-postfix/exec"),
        )
        self.assertEqual(
            request.call_args_list[1],
            call("POST", "/v1.41/exec/abc123/start", b'{"Detach":false,"Tty":true}'),
        )
        self.assertEqual(request.call_args_list[2], call("GET", "/v1.41/exec/abc123/json"))
        create_payload = json.loads(create_call.args[2])
        self.assertEqual(create_payload["Cmd"], ["postqueue", "-j"])
        self.assertEqual(create_payload["User"], "postfix")
        self.assertEqual(create_payload["Tty"], True)


if __name__ == "__main__":
    unittest.main()
