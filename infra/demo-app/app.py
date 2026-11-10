"""Small, dependency-free HTTP fixture for the monitored lab."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "DevOpsMonitorDemo/1.0"

    def do_GET(self):
        if self.path == "/health":
            self._send(200, "application/json; charset=utf-8", b'{"status":"ok"}')
            return
        if self.path == "/":
            page = ("<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
                    "<title>DevOps Monitor Demo</title><h1>DevOps Monitor</h1>"
                    "<p>Aplicação de laboratório para monitoramento.</p></html>")
            self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))
            return
        self._send(404, "application/json; charset=utf-8", b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/login":
            self._send(404, "application/json; charset=utf-8", b'{"error":"not found"}')
            return

        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            self._send(400, "application/json; charset=utf-8", b'{"error":"invalid length"}')
            return
        if length < 0 or length > 4096:
            self._send(413, "application/json; charset=utf-8", b'{"error":"body too large"}')
            return

        body = self.rfile.read(length).decode("utf-8", errors="replace")
        user = parse_qs(body, keep_blank_values=True).get("username", [""])[0][:128]
        # The header travels through Nginx's escape=json log format. JSON-escaping
        # here prevents CR/LF and quote characters from creating a second record.
        safe_user = json.dumps(user, ensure_ascii=True)[1:-1]
        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Demo-Login-User", safe_user)
        self.send_header("Content-Length", str(len(b'{"error":"invalid login"}')))
        self.end_headers()
        self.wfile.write(b'{"error":"invalid login"}')

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        # Keep application output quiet; Nginx owns the structured access log.
        return


def main():
    server = ThreadingHTTPServer((os.getenv("HOST", "0.0.0.0"), int(os.getenv("PORT", "8000"))), DemoHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
