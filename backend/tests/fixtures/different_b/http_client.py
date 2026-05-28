"""Minimal HTTP client and request/response abstractions."""
import json
import socket
import urllib.parse
from typing import Any, Dict, Optional


DEFAULT_TIMEOUT = 30
MAX_REDIRECTS = 5
USER_AGENT = "CodeCompareClient/1.0"


def build_query_string(params: Dict[str, str]) -> str:
    return "&".join(
        f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}"
        for k, v in sorted(params.items())
    )


def parse_headers(raw: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return headers


def encode_json_body(payload: Any) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class HttpResponse:
    def __init__(self, status: int, headers: Dict[str, str], body: bytes):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        charset = self.headers.get("content-type", "utf-8")
        if "charset=" in charset:
            charset = charset.split("charset=")[-1].strip()
        else:
            charset = "utf-8"
        return self.body.decode(charset, errors="replace")

    def ok(self) -> bool:
        return 200 <= self.status < 300

    def __repr__(self) -> str:
        return f"HttpResponse(status={self.status}, bytes={len(self.body)})"


class RetryPolicy:
    def __init__(self, max_retries: int = 3, backoff: float = 0.5):
        self.max_retries = max_retries
        self.backoff = backoff
        self._attempt = 0

    def should_retry(self, status: int) -> bool:
        if self._attempt >= self.max_retries:
            return False
        return status in (429, 500, 502, 503, 504)

    def next_attempt(self) -> float:
        delay = self.backoff * (2 ** self._attempt)
        self._attempt += 1
        return delay

    def reset(self) -> None:
        self._attempt = 0


class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._pool: Dict[str, list] = {}
        self._count = 0

    def acquire(self, host: str, port: int) -> Optional[socket.socket]:
        key = f"{host}:{port}"
        if key in self._pool and self._pool[key]:
            return self._pool[key].pop()
        if self._count < self.max_connections:
            conn = socket.create_connection((host, port), timeout=DEFAULT_TIMEOUT)
            self._count += 1
            return conn
        return None

    def release(self, host: str, port: int, conn: socket.socket) -> None:
        key = f"{host}:{port}"
        if key not in self._pool:
            self._pool[key] = []
        self._pool[key].append(conn)

    def close_all(self) -> None:
        for sockets in self._pool.values():
            for s in sockets:
                try:
                    s.close()
                except OSError:
                    pass
        self._pool.clear()
        self._count = 0
