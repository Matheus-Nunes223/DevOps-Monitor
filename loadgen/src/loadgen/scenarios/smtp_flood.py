"""Bounded SMTP messages relayed into the local MailHog instance."""

from __future__ import annotations

import smtplib
import time
import uuid
from collections.abc import Callable
from email.message import EmailMessage

from loadgen.scenarios.core import MAX_SMTP_MESSAGES, check_bound, validate_smtp_host


def run_smtp_flood(
    smtp: object | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 2525,
    messages: int = 10,
    messages_per_second: float = 2.0,
    confirm: bool = False,
    allow_remote: bool = False,
    sender: str = "loadgen@devops.local",
    recipient: str = "loadgen@devops.local",
    smtp_factory: Callable[..., object] = smtplib.SMTP,
    sleep: Callable[[float], object] = time.sleep,
) -> int:
    if not confirm:
        raise PermissionError("smtp_flood requires explicit fault confirmation")
    validate_smtp_host(host, allow_remote)
    check_bound(messages, minimum=1, maximum=MAX_SMTP_MESSAGES, name="messages")
    if not 0.1 <= messages_per_second <= 5:
        raise ValueError("messages_per_second must be between 0.1 and 5")
    if not 1 <= port <= 65535:
        raise ValueError("port must be a valid TCP port")
    client_context = smtp if smtp is not None else smtp_factory(host, port, timeout=5)
    sent = 0
    with client_context as client:  # type: ignore[attr-defined]
        for index in range(messages):
            token = uuid.uuid4().hex
            message = EmailMessage()
            message["From"] = sender
            message["To"] = recipient
            message["Subject"] = f"DevOps Monitor loadgen {index + 1} {token}"
            message["Message-ID"] = f"<loadgen-{token}@devops.local>"
            message.set_content(f"Synthetic load scenario message {index + 1}; token={token}")
            client.send_message(message)
            sent += 1
            if index + 1 < messages:
                sleep(1 / messages_per_second)
    return sent
