"""Single command-line interface for all bounded lab scenarios."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from loadgen.scenarios.bruteforce import run_bruteforce
from loadgen.scenarios.core import DEFAULT_TARGET, make_http_client
from loadgen.scenarios.edit_config import run_edit_config
from loadgen.scenarios.normal import run_normal
from loadgen.scenarios.smtp_flood import run_smtp_flood
from loadgen.scenarios.spike import run_spike
from loadgen.scenarios.stop_service import ALLOWED_SERVICES, run_stop_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devops-loadgen",
        description="Bounded load/fault scenarios for the local DevOps Monitor lab.",
    )
    subparsers = parser.add_subparsers(dest="scenario", required=True)

    normal = subparsers.add_parser("normal", help="send steady GET traffic")
    normal.add_argument("--target", default=DEFAULT_TARGET)
    normal.add_argument("--requests", type=int, default=60)
    normal.add_argument("--rate", type=float, default=2.0, help="requests per second")
    normal.add_argument("--allow-remote-target", action="store_true")

    spike = subparsers.add_parser("spike", help="send a finite concurrent burst")
    spike.add_argument("--target", default=DEFAULT_TARGET)
    spike.add_argument("--requests", type=int, default=200)
    spike.add_argument("--concurrency", type=int, default=20)
    spike.add_argument("--allow-remote-target", action="store_true")

    brute = subparsers.add_parser("bruteforce", help="send invalid demo login attempts")
    brute.add_argument("--target", default=DEFAULT_TARGET)
    brute.add_argument("--attempts", type=int, default=20)
    brute.add_argument("--username", default="demo-user@devops.local")
    brute.add_argument("--delay", type=float, default=0.1)
    brute.add_argument("--allow-remote-target", action="store_true")

    stop = subparsers.add_parser("stop_service", help="stop then restart a monitored service")
    stop.add_argument("--service", choices=ALLOWED_SERVICES, default="nginx")
    stop.add_argument("--duration", type=int, default=10)
    stop.add_argument("--confirm-fault", action="store_true")

    edit = subparsers.add_parser("edit_config", help="temporarily alter and restore Nginx config")
    edit.add_argument("--duration", type=int, default=10)
    edit.add_argument("--confirm-fault", action="store_true")

    smtp = subparsers.add_parser("smtp_flood", help="send bounded mail into local MailHog")
    smtp.add_argument("--host", default="127.0.0.1")
    smtp.add_argument("--port", type=int, default=2525)
    smtp.add_argument("--messages", type=int, default=10)
    smtp.add_argument("--rate", type=float, default=2.0, help="messages per second")
    smtp.add_argument("--confirm-fault", action="store_true")
    smtp.add_argument("--allow-remote-target", action="store_true")
    return parser


def run(args: argparse.Namespace) -> str:
    if args.scenario in {"normal", "spike", "bruteforce"}:
        with make_http_client() as client:
            if args.scenario == "normal":
                sent = run_normal(
                    client,
                    args.target,
                    requests=args.requests,
                    rate_per_second=args.rate,
                    allow_remote=args.allow_remote_target,
                )
                return f"normal: {sent}/{args.requests} respostas bem-sucedidas"
            if args.scenario == "spike":
                sent = run_spike(
                    client,
                    args.target,
                    requests=args.requests,
                    concurrency=args.concurrency,
                    allow_remote=args.allow_remote_target,
                )
                return f"spike: {sent}/{args.requests} respostas bem-sucedidas"
            unauthorized = run_bruteforce(
                client,
                args.target,
                attempts=args.attempts,
                username=args.username,
                delay_seconds=args.delay,
                allow_remote=args.allow_remote_target,
            )
            return f"bruteforce: {unauthorized}/{args.attempts} respostas 401"

    if args.scenario == "stop_service":
        run_stop_service(
            args.service, duration_seconds=args.duration, confirm=args.confirm_fault
        )
        return f"stop_service: {args.service} interrompido e reiniciado"
    if args.scenario == "edit_config":
        run_edit_config(duration_seconds=args.duration, confirm=args.confirm_fault)
        return "edit_config: configuração alterada, validada, restaurada e recarregada"
    if args.scenario == "smtp_flood":
        sent = run_smtp_flood(
            host=args.host,
            port=args.port,
            messages=args.messages,
            messages_per_second=args.rate,
            confirm=args.confirm_fault,
            allow_remote=args.allow_remote_target,
        )
        return f"smtp_flood: {sent} mensagens entregues ao relay local"
    raise ValueError("unknown scenario")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        print(run(args))
    except Exception as error:
        print(f"devops-loadgen: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
