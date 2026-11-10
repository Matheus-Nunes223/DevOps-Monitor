from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from loadgen.scenarios.bruteforce import run_bruteforce
from loadgen.scenarios.core import validate_http_target
from loadgen.scenarios.edit_config import run_edit_config
from loadgen.scenarios.normal import run_normal
from loadgen.scenarios.smtp_flood import run_smtp_flood
from loadgen.scenarios.spike import run_spike
from loadgen.scenarios.stop_service import run_stop_service


class FakeResponse:
    status_code = 401


class FakeHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        return FakeResponse()

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        return FakeResponse()


class FakeSmtp:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    def __enter__(self) -> FakeSmtp:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def send_message(self, message: Any) -> None:
        self.messages.append(message)


class LoadgenTests(unittest.TestCase):
    def test_http_target_is_local_unless_remote_opt_in(self) -> None:
        with self.assertRaises(ValueError):
            validate_http_target("https://example.com")
        self.assertEqual(
            validate_http_target("https://example.com", allow_remote=True),
            "https://example.com",
        )

    def test_normal_and_spike_emit_the_requested_finite_load(self) -> None:
        client = FakeHttp()
        run_normal(
            client,
            "http://127.0.0.1:8080",
            requests=3,
            rate_per_second=20,
            sleep=lambda _: None,
        )
        run_spike(client, "http://127.0.0.1:8080", requests=5, concurrency=2)
        self.assertEqual(len(client.calls), 8)
        self.assertTrue(all(method == "GET" for method, _, _ in client.calls))

    def test_bruteforce_uses_synthetic_identity_and_invalid_login_route(self) -> None:
        client = FakeHttp()
        run_bruteforce(
            client,
            "http://127.0.0.1:8080",
            attempts=4,
            username="demo-user@devops.local",
            sleep=lambda _: None,
        )
        self.assertEqual(len(client.calls), 4)
        self.assertTrue(
            all(
                call[0] == "POST" and call[1].endswith("/login")
                for call in client.calls
            )
        )
        self.assertTrue(
            all(call[2]["data"]["username"] == "demo-user@devops.local" for call in client.calls)
        )

    def test_stop_service_restores_only_a_previously_running_service(self) -> None:
        commands: list[list[str]] = []

        def command(args: list[str]) -> str:
            commands.append(args)
            return "container-id" if "ps" in args else ""

        run_stop_service(
            "nginx", duration_seconds=2, confirm=True, command=command, sleep=lambda _: None
        )
        self.assertEqual(commands[-2:], [["docker", "compose", "stop", "nginx"],
                                         ["docker", "compose", "start", "nginx"]])

    def test_stop_service_refuses_confirmation_missing_or_previously_stopped(self) -> None:
        calls: list[list[str]] = []
        with self.assertRaises(PermissionError):
            run_stop_service("nginx", command=lambda args: calls.append(args) or "")
        with self.assertRaises(RuntimeError):
            run_stop_service(
                "nginx",
                confirm=True,
                command=lambda args: calls.append(args) or "",
            )
        self.assertEqual(len(calls), 1)

    def test_stop_service_attempts_restart_when_stop_command_errors(self) -> None:
        commands: list[list[str]] = []

        def command(args: list[str]) -> str:
            commands.append(args)
            if args[2] == "ps":
                return "container-id"
            if args[2] == "stop":
                raise RuntimeError("stop failed")
            return ""

        with self.assertRaises(RuntimeError):
            run_stop_service("nginx", confirm=True, command=command)
        self.assertEqual(commands[-1], ["docker", "compose", "start", "nginx"])

    def test_edit_config_restores_file_even_when_reload_fails(self) -> None:
        original = b"worker_connections 1024;\n"
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            config = project_root / "infra" / "nginx" / "nginx.conf"
            config.parent.mkdir(parents=True)
            config.write_bytes(original)
            calls = 0

            def command(_args: list[str]) -> str:
                nonlocal calls
                calls += 1
                if calls == 1:
                    self.assertEqual(config.read_bytes(), b"worker_connections 1023;\n")
                    return ""
                if calls == 2:
                    raise RuntimeError("simulated reload failure")
                self.assertEqual(config.read_bytes(), original)
                return ""

            with self.assertRaises(RuntimeError):
                run_edit_config(config, project_root=project_root, confirm=True, command=command)
            self.assertEqual(config.read_bytes(), original)
            self.assertEqual(calls, 4)

    def test_smtp_flood_is_finite_and_requires_explicit_confirmation(self) -> None:
        smtp = FakeSmtp()
        with self.assertRaises(PermissionError):
            run_smtp_flood(smtp, messages=2, confirm=False, sleep=lambda _: None)
        run_smtp_flood(smtp, messages=3, confirm=True, sleep=lambda _: None)
        self.assertEqual(len(smtp.messages), 3)
        self.assertEqual(len({message["Message-ID"] for message in smtp.messages}), 3)


if __name__ == "__main__":
    unittest.main()
