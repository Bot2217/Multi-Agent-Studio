"""Local-only access for the engine.

The sidecar binds 127.0.0.1 and requires a per-launch bearer token. A browser
page that reaches the port through DNS rebinding still fails the Host and
Origin checks, and it does not have the token.
"""

from __future__ import annotations

import json
import re

_HOST = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(?::\d+)?$", re.I)
_ORIGIN = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\])(?::\d+)?$", re.I)


def host_ok(value: str) -> bool:
    return bool(_HOST.match((value or "").strip()))


def origin_ok(value: str) -> bool:
    return bool(_ORIGIN.match((value or "").strip()))


class LocalTrust:
    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope.get("type") not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers") or []
        }
        if not host_ok(headers.get("host", "")):
            await _reject(scope, send, 403, "bad_host")
            return
        origin = headers.get("origin")
        if origin and not origin_ok(origin):
            await _reject(scope, send, 403, "bad_origin")
            return
        if headers.get("authorization") != f"Bearer {self.token}":
            await _reject(scope, send, 401, "unauthorized")
            return
        await self.app(scope, receive, send)


async def _reject(scope, send, status: int, detail: str) -> None:
    if scope.get("type") == "websocket":
        await send({"type": "websocket.close", "code": 4401})
        return
    body = json.dumps({"detail": detail}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})
