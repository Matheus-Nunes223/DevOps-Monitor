from __future__ import annotations

import json
import unittest
from email.message import EmailMessage
from urllib.parse import parse_qs, urlsplit

from monitor.probes.smtp import (
    PostfixLogProbe,
    PostfixQueueReader,
    SmtpDeliveryProbe,
    parse_postfix_log,
    parse_postfix_timestamp,
    parse_postqueue_json,
)


class PostfixParserTests(unittest.TestCase):
    def test_classifies_delivery_reject_timeout_and_queue_arrival(self) -> None:
        sent = parse_postfix_log(
            "postfix/smtp[12]: A1B2: to=<a@example.test>, status=sent (250 ok)"
        )
        rejected = parse_postfix_log("postfix/smtpd[12]: NOQUEUE: reject: RCPT from bad")
        timed_out = parse_postfix_log(
            "postfix/smtp[12]: C3D4: to=<b@example.test>, status=deferred (connect timed out)"
        )
        monitor = parse_postfix_log(
            "postfix/smtp[12]: C3D4: to=<probe@devops.local>, status=sent (250 ok)"
        )
        accepted = parse_postfix_log("postfix/qmgr[12]: E5F6: from=<sender@example.test>, size=50")

        self.assertEqual(sent.status, "sent")
        self.assertTrue(rejected.rejected)
        self.assertTrue(timed_out.timed_out)
        self.assertTrue(monitor.is_probe)
        self.assertTrue(accepted.accepted)

    def test_queue_parser_handles_json_lines_and_empty_queue(self) -> None:
        queue = "\n".join(
            json.dumps({"queue_id": queue_id, "recipients": []})
            for queue_id in ("A1B2", "C3D4")
        )
        self.assertEqual(parse_postqueue_json(queue), 2)
        self.assertEqual(parse_postqueue_json("\n"), 0)

    def test_queue_reader_fetches_json_from_restricted_proxy_endpoint(self) -> None:
        requested: list[tuple[str, int]] = []

        def open_queue(url: str, timeout: int) -> FakeResponse:
            requested.append((url, timeout))
            return FakeResponse(b'{"queue_id":"A1"}\n')

        self.assertEqual(PostfixQueueReader(urlopen_fn=open_queue).queue_length(), 1)
        self.assertEqual(
            requested,
            [("http://docker-stats-proxy:2375/postfix-queue", 3)],
        )

    def test_queue_parser_rejects_malformed_lines(self) -> None:
        with self.assertRaises(ValueError):
            parse_postqueue_json('{"queue_id":\n')

    def test_log_probe_calculates_delivery_failure_and_volume_metrics(self) -> None:
        lines = (
            "postfix/qmgr[1]: A1: from=<sender@test>, size=100, nrcpt=1",
            "postfix/qmgr[1]: B2: from=<sender@test>, size=200, nrcpt=1",
            "postfix/smtp[1]: A1: to=<dest@test>, status=sent (250 ok)",
            "postfix/smtp[1]: B2: to=<dest@test>, status=deferred (connect timed out)",
            "postfix/smtpd[1]: NOQUEUE: reject: RCPT from bad",
            "postfix/qmgr[1]: C3: from=<monitor@devops.local>, size=50, nrcpt=1",
            "postfix/smtp[1]: C3: to=<probe@devops.local>, status=sent (250 ok)",
        )
        ticks = iter((0.0, 60.0))
        result_metrics = PostfixLogProbe(
            lambda: lines, clock=lambda: next(ticks)
        ).collect().metrics
        result = {
            metric.metric: metric.value
            for metric in result_metrics
        }
        self.assertAlmostEqual(result["smtp.delivery_rate"], 0.5)
        self.assertAlmostEqual(result["smtp.reject_rate"], 1 / 3)
        self.assertAlmostEqual(result["smtp.timeout_rate"], 1 / 3)
        self.assertAlmostEqual(result["smtp.volume_per_min"], 2.0)
        self.assertAlmostEqual(result["smtp.volume_per_hour"], 120.0)

    def test_strips_timestamp_from_docker_log_line(self) -> None:
        line = "2026-11-09T12:00:00.123456789Z postfix/smtp[8]: A1: status=sent"
        self.assertEqual(parse_postfix_timestamp(line), "postfix/smtp[8]: A1: status=sent")


class FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class FakeSmtp:
    def __init__(self) -> None:
        self.message: EmailMessage | None = None

    def __enter__(self) -> FakeSmtp:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


class SmtpProbeTests(unittest.TestCase):
    def test_sends_unique_message_and_measures_mailhog_arrival(self) -> None:
        smtp = FakeSmtp()
        ticks = iter((0.0, 0.1, 0.4))
        urls: list[str] = []

        def search(url: str, **_kwargs: object) -> FakeResponse:
            urls.append(url)
            return FakeResponse(b'{"total":1,"items":[{}]}')

        probe = SmtpDeliveryProbe(
            "postfix",
            25,
            "http://mailhog:8025",
            "monitor@devops.local",
            "probe@devops.local",
            smtp_factory=lambda *_args, **_kwargs: smtp,
            urlopen_fn=search,
            clock=lambda: next(ticks),
            sleep=lambda _seconds: None,
        )

        result = probe.collect()

        self.assertAlmostEqual(result.metrics[0].value or 0.0, 400.0)
        self.assertIsNotNone(smtp.message)
        assert smtp.message is not None
        self.assertIn("devops-monitor-", smtp.message["Message-ID"] or "")
        self.assertEqual(parse_qs(urlsplit(urls[0]).query)["kind"], ["containing"])
        token = parse_qs(urlsplit(urls[0]).query)["query"][0]
        self.assertIn(token, smtp.message.get_content())


if __name__ == "__main__":
    unittest.main()
