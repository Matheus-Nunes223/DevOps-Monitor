"""Narrow Docker proxy for database stats and fixed Postfix read operations."""

from __future__ import annotations

import http.client
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

SOCKET_PATH = "/var/run/docker.sock"
ALLOWED_PATH = re.compile(
    r"^/v(?P<version>[0-9]+\.[0-9]+)/containers/devops-monitor-postgres/stats$"
)


def allowed_stats_path(path: str) -> bool:
    parsed = urlsplit(path)
    query = parse_qs(parsed.query)
    return bool(
        ALLOWED_PATH.fullmatch(parsed.path)
        and set(query) <= {"stream"}
        and len(query.get("stream", ["false"])) == 1
        and query.get("stream", ["false"])[0].lower() in {"false", "0"}
    )


def allowed_postfix_logs_path(path: str) -> bool:
    parsed = urlsplit(path)
    query = parse_qs(parsed.query)
    return bool(
        re.fullmatch(r"/v[0-9]+\.[0-9]+/containers/devops-monitor-postfix/logs", parsed.path)
        and set(query) == {"stdout", "stderr", "timestamps", "since", "follow", "tail"}
        and query["stdout"] == ["1"]
        and query["stderr"] == ["0"]
        and query["timestamps"] == ["1"]
        and len(query["since"]) == 1
        and query["since"][0].isdigit()
        and query["follow"] == ["False"]
        and query["tail"] == ["all"]
    )


class UnixSocketConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        import socket

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(8)
        self.sock.connect(SOCKET_PATH)


def docker_request(
    method: str, path: str, body: bytes | None = None
) -> tuple[int, bytes, str]:
    connection = UnixSocketConnection("docker")
    headers = {"Host": "docker"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        return response.status, payload, response.getheader("Content-Type", "application/json")
    finally:
        connection.close()


def demultiplex_stdout(payload: bytes) -> bytes:
    """Strip Docker's 8-byte stream headers and keep only stdout frames."""
    output = bytearray()
    offset = 0
    frames = 0
    while offset + 8 <= len(payload):
        stream = payload[offset]
        size = int.from_bytes(payload[offset + 4 : offset + 8], "big")
        start = offset + 8
        end = start + size
        if stream not in (1, 2) or end > len(payload):
            return payload
        if stream == 1:
            output.extend(payload[start:end])
        offset = end
        frames += 1
    if frames and offset == len(payload):
        return bytes(output)
    return payload


def postfix_queue_output() -> bytes:
    """Run one fixed, non-mutating command inside the fixed Postfix container."""
    version = "/v1.41"
    create_body = json.dumps(
        {
            "AttachStdout": True,
            "AttachStderr": True,
            "Cmd": ["postqueue", "-j"],
            "Tty": True,
            "User": "postfix",
        },
        separators=(",", ":"),
    ).encode()
    status, payload, _ = docker_request(
        "POST", f"{version}/containers/devops-monitor-postfix/exec", create_body
    )
    if status != 201:
        raise RuntimeError("Docker refused the fixed Postfix queue command")
    exec_id = json.loads(payload).get("Id")
    if not isinstance(exec_id, str) or not re.fullmatch(r"[a-fA-F0-9-]+", exec_id):
        raise RuntimeError("Docker returned an invalid exec identifier")
    start_body = b'{"Detach":false,"Tty":true}'
    status, output, _ = docker_request("POST", f"{version}/exec/{exec_id}/start", start_body)
    if status != 200:
        raise RuntimeError("Docker could not execute the fixed Postfix queue command")
    status, details, _ = docker_request("GET", f"{version}/exec/{exec_id}/json")
    if status != 200 or json.loads(details).get("ExitCode") != 0:
        raise RuntimeError("Postfix queue command failed")
    return output


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path == "/postfix-queue":
            try:
                body = postfix_queue_output()
            except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError):
                self.send_error(502)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/postfix-logs?"):
            query = parse_qs(urlsplit(self.path).query)
            since = query.get("since", ["0"])[0]
            if set(query) != {"since"} or not since.isdigit():
                self.send_error(403)
                return
            docker_path = (
                f"/v1.41/containers/devops-monitor-postfix/logs?"
                f"stdout=1&stderr=0&timestamps=1&since={since}&follow=False&tail=all"
            )
            if not allowed_postfix_logs_path(docker_path):
                self.send_error(403)
                return
            status, body, _ = docker_request("GET", docker_path)
            if status != 200:
                self.send_error(502)
                return
            body = demultiplex_stdout(body)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not allowed_stats_path(self.path):
            self.send_error(403)
            return
        upstream = UnixSocketConnection("docker")
        try:
            upstream.request("GET", self.path, headers={"Host": "docker"})
            response = upstream.getresponse()
            body = response.read()
        except OSError:
            self.send_error(502)
            return
        finally:
            upstream.close()
        self.send_response(response.status)
        self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 2375), Handler).serve_forever()
