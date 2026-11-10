"""E-mail delivery of alerts over a dedicated SMTP connection.

This deliberately does NOT use the monitored Postfix: the alert channel must keep
working when the SMTP service under observation is down.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from monitor.alerts.templates import RenderedEmail
from monitor.model import AlertLevel

LOGGER = logging.getLogger(__name__)

RESEND_INTERVAL: dict[AlertLevel, timedelta] = {
    "red": timedelta(minutes=10),
    "yellow": timedelta(minutes=30),
}


def resend_due(level: AlertLevel, last_notified_at: datetime | None, now: datetime) -> bool:
    if last_notified_at is None:
        return True
    return now - last_notified_at >= RESEND_INTERVAL[level]


class Notifier(Protocol):
    def send(self, email: RenderedEmail) -> bool:
        """Return True only when the message was accepted by the SMTP server."""
        ...


class EmailNotifier:
    def __init__(
        self,
        host: str,
        port: int,
        recipients: str,
        sender: str,
        user: str = "",
        password: str = "",
        timeout_seconds: int = 10,
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        self._host = host
        self._port = port
        self._recipients = [item.strip() for item in recipients.split(",") if item.strip()]
        self._sender = sender
        self._user = user
        self._password = password
        self._timeout = timeout_seconds
        self._factory = smtp_factory

    def send(self, email: RenderedEmail) -> bool:
        if not self._recipients:
            LOGGER.warning("alert e-mail skipped: ALERT_EMAIL_TO is empty")
            return False
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message["Subject"] = email.subject
        message.set_content(email.body)
        try:
            with self._factory(self._host, self._port, timeout=self._timeout) as smtp:
                if self._user:
                    smtp.starttls()
                    smtp.login(self._user, self._password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            LOGGER.error(
                "alert e-mail failed",
                extra={"error_type": type(error).__name__},
            )
            return False
        return True
