import json
import io
import unittest
from email.message import Message

from app import DemoHandler


class DemoAppTests(unittest.TestCase):
    def request(self, method, path, body=None, headers=None):
        handler = DemoHandler.__new__(DemoHandler)
        handler.path = path
        handler.headers = Message()
        for key, value in (headers or {}).items():
            handler.headers[key] = value
        handler.rfile = io.BytesIO((body or "").encode("utf-8"))
        if body is not None:
            handler.headers["Content-Length"] = str(len(body.encode("utf-8")))
        handler.wfile = io.BytesIO()
        handler.response_headers = {}
        handler.send_response = lambda status: setattr(handler, "status", status)
        handler.send_header = lambda key, value: handler.response_headers.__setitem__(key, value)
        handler.end_headers = lambda: None
        getattr(handler, f"do_{method}")()
        return handler.status, handler.response_headers, handler.wfile.getvalue()

    def test_home_returns_demo_page(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers).get("Content-Type", ""))
        self.assertIn(b"DevOps Monitor", body)

    def test_health_endpoint_is_ok(self):
        status, _, body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_login_is_fixture_and_records_attempted_user_in_header(self):
        status, headers, _ = self.request(
            "POST", "/login", "username=alice&password=wrong",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(dict(headers).get("X-Demo-Login-User"), "alice")

    def test_login_user_header_is_safe_for_json_access_log(self):
        status, headers, _ = self.request(
            "POST", "/login", "username=%22%5Cr%5Cnadmin&password=x",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(dict(headers).get("X-Demo-Login-User"), r'\"\\r\\nadmin')

    def test_unknown_route_is_not_found(self):
        status, _, _ = self.request("GET", "/missing")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
