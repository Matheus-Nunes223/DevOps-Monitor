import smtplib
from datetime import datetime, timedelta, timezone

from monitor.alerts.notifier import EmailNotifier, resend_due
from monitor.alerts.templates import RenderedEmail, format_value, render_open, render_resolved

NOW = datetime(2026, 11, 9, 20, 0, tzinfo=timezone.utc)


def test_subjects_follow_the_spec():
    down = render_open(service_id="web", kind="availability", level="red", message="m",
                       metric="web.up", value=2, dashboard_url="http://x", opened_at="t")
    warn = render_open(service_id="db", kind="threshold", level="yellow", message="m",
                       metric="db.connections_ratio", value=0.78, dashboard_url="http://x",
                       opened_at="t")
    ok = render_resolved(service_id="web", kind="availability", message="m",
                         dashboard_url="http://x", resolved_at="t")
    assert down.subject == "[CRÍTICO] web indisponível"
    assert warn.subject == "[ATENÇÃO] db conexões em 78%"
    assert ok.subject == "[RESOLVIDO] web"


def test_body_has_dashboard_and_runbook_links():
    email = render_open(service_id="dns", kind="threshold", level="red", message="lento",
                        metric="dns.resolve_ms", value=620, dashboard_url="http://p:3000/",
                        opened_at="2026-11-09 20:00:00")
    assert "http://p:3000/services/dns" in email.body
    assert "docs/runbooks/dns.md" in email.body
    assert "620 ms" in email.body or "lento" in email.body


def test_security_subject_and_reminder_marker():
    email = render_open(service_id="web", kind="bruteforce", level="red", message="m",
                        metric=None, value=None, dashboard_url="http://x", opened_at="t",
                        reminder=True)
    assert email.subject == "[CRÍTICO] web: brute-force de login (lembrete)"


def test_format_value():
    assert format_value("web.error_5xx_rate", 0.123) == "12%"
    assert format_value("dns.resolve_ms", 120.4) == "120 ms"
    assert format_value("smtp.queue_length", 50) == "50"


def test_resend_intervals():
    assert resend_due("red", None, NOW)
    assert not resend_due("red", NOW - timedelta(minutes=9), NOW)
    assert resend_due("red", NOW - timedelta(minutes=10), NOW)
    assert not resend_due("yellow", NOW - timedelta(minutes=29), NOW)
    assert resend_due("yellow", NOW - timedelta(minutes=30), NOW)


class FakeSmtp:
    sent: list = []
    fail = False

    def __init__(self, host, port, timeout=10):
        if FakeSmtp.fail:
            raise smtplib.SMTPConnectError(421, "down")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def send_message(self, message):
        FakeSmtp.sent.append(message)


def test_notifier_sends_utf8_message_to_all_recipients():
    FakeSmtp.sent, FakeSmtp.fail = [], False
    notifier = EmailNotifier("mailhog", 1025, "a@x.com, b@x.com", "alertas@x.com",
                             smtp_factory=FakeSmtp)
    assert notifier.send(RenderedEmail("[CRÍTICO] web indisponível", "corpo\n"))
    message = FakeSmtp.sent[0]
    assert message["To"] == "a@x.com, b@x.com"
    assert message["Subject"] == "[CRÍTICO] web indisponível"


def test_notifier_reports_failure_instead_of_raising():
    FakeSmtp.fail = True
    notifier = EmailNotifier("mailhog", 1025, "a@x.com", "s@x.com", smtp_factory=FakeSmtp)
    assert notifier.send(RenderedEmail("s", "b")) is False
    FakeSmtp.fail = False


def test_notifier_without_recipient_is_disabled():
    notifier = EmailNotifier("mailhog", 1025, "", "s@x.com", smtp_factory=FakeSmtp)
    assert notifier.send(RenderedEmail("s", "b")) is False
