"""Bounded, demo-only Streamable HTTP service for MCP SDK 1.28.0."""
import argparse
import asyncio
from collections import deque
import ipaddress
import os
import re
import time
from urllib.parse import urlsplit

from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from . import __version__
from .importers import load_catalog
from .server import create_server


def _host_pattern(value: str) -> str:
    value = value.strip().lower()
    candidate = value[:-2] + ":1" if value.endswith(":*") else value
    try:
        parts = urlsplit("//" + candidate)
        port = parts.port
        hostname = parts.hostname
        if (not hostname or parts.username or parts.password or parts.path or parts.query
                or parts.fragment or "*" in candidate or any(c.isspace() for c in candidate)
                or "\\" in candidate or candidate.endswith(":")):
            raise ValueError
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", hostname):
                raise ValueError
            if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
                   for label in hostname.split(".")):
                raise ValueError
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
    except ValueError as exc:
        raise ValueError("allowed hosts must be exact hosts, optionally :port or :*") from exc
    return value


def _origin(value: str) -> str:
    value = value.strip().lower()
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.path or parts.query or parts.fragment:
        raise ValueError("allowed origins must be exact HTTP(S) origins without a path")
    # Origins deliberately require exact ports; no origin wildcards.
    if "*" in value:
        raise ValueError("origin wildcards are not allowed")
    _host_pattern(parts.netloc)
    return value


def _matches_host(value: str, patterns: list[str]) -> bool:
    try:
        value = _host_pattern(value)
        if "*" in value:
            return False
        parts = urlsplit("//" + value)
        for pattern in patterns:
            if value == pattern:
                return True
            if pattern.endswith(":*"):
                allowed = urlsplit("//" + pattern[:-2])
                if parts.hostname == allowed.hostname and parts.port is not None:
                    return True
    except ValueError:
        pass
    return False


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ServiceLimits:
    """ASGI guard: bounded buffering, global per-process rate and concurrency."""

    def __init__(self, app, hosts, origins, *, body_limit=65536, timeout=15.0,
                 requests_per_minute=120, max_concurrency=16):
        if body_limit < 1 or timeout <= 0 or requests_per_minute < 1 or max_concurrency < 1:
            raise ValueError("service limits must be positive")
        self.app, self.hosts, self.origins = app, hosts, origins
        self.body_limit, self.timeout = body_limit, timeout
        self.rate, self.max_concurrency = requests_per_minute, max_concurrency
        self.requests = deque()
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def reject(status, message):
            await JSONResponse({"error": message}, status_code=status,
                               headers={"Cache-Control": "no-store"})(scope, receive, send)

        headers = {}
        for name, value in scope.get("headers", []):
            name = name.lower()
            if name in headers and name in {b"host", b"origin", b"content-length"}:
                return await reject(400, "duplicate request header")
            headers[name] = value.decode("latin-1")
        if not _matches_host(headers.get(b"host", ""), self.hosts):
            return await reject(421, "invalid Host")
        origin = headers.get(b"origin")
        if origin is not None and origin.lower() not in self.origins:
            return await reject(403, "invalid Origin")
        length = headers.get(b"content-length")
        if length is not None:
            if not length.isascii() or not length.isdigit() or len(length) > 20:
                return await reject(400, "invalid Content-Length")
            if int(length) > self.body_limit:
                return await reject(413, "request body too large")
        now = time.monotonic()
        while self.requests and self.requests[0] <= now - 60:
            self.requests.popleft()
        if len(self.requests) >= self.rate:
            return await reject(429, "request rate limit reached")
        if self.active >= self.max_concurrency:
            return await reject(503, "request concurrency limit reached")
        self.requests.append(now)
        self.active += 1
        started = False
        complete = False

        async def tracked_send(message):
            nonlocal started, complete
            if message["type"] == "http.response.start":
                started = True
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                complete = True
            await send(message)

        async def bounded_request():
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > self.body_limit:
                    return await reject(413, "request body too large")
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay, tracked_send)

        try:
            await asyncio.wait_for(bounded_request(), timeout=self.timeout)
        except asyncio.TimeoutError:
            if not started:
                await reject(504, "request deadline exceeded")
            elif not complete:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
        finally:
            self.active -= 1


def create_app(path, *, host="127.0.0.1", allowed_hosts=None, allowed_origins=None, **limits):
    """Build one immutable demo snapshot and its MCP ASGI lifespan."""
    if not _loopback(host) and (not allowed_hosts or not allowed_origins):
        raise ValueError("public binding requires explicit allowed hosts AND origins")
    hosts = [_host_pattern(value) for value in (allowed_hosts or ["127.0.0.1:*", "localhost:*", "[::1]:*"])]
    origins = [_origin(value) for value in (allowed_origins or ["http://127.0.0.1", "http://localhost"])]
    catalog = load_catalog(path)
    if not catalog.products or not all(product.is_demo is True for product in catalog.products):
        raise ValueError("HTTP service requires a nonempty, entirely synthetic demo catalog")
    server = create_server(catalog, transport="streamable-http")
    server.settings.stateless_http = True
    server.settings.json_response = True
    server.settings.streamable_http_path = "/mcp"
    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts, allowed_origins=origins)

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(request):
        return JSONResponse({"ready": True, "demo": True, "version": __version__,
                             "count": len(catalog.products)}, headers={"Cache-Control": "no-store"})

    return ServiceLimits(server.streamable_http_app(), hosts, origins, **limits)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="miseport-http")
    parser.add_argument("--catalog", default=os.environ.get("MISEPORT_CATALOG"))
    parser.add_argument("--host", default=os.environ.get("MISEPORT_HTTP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=os.environ.get("MISEPORT_HTTP_PORT", "8000"))
    parser.add_argument("--allowed-hosts", default=os.environ.get("MISEPORT_ALLOWED_HOSTS", ""))
    parser.add_argument("--allowed-origins", default=os.environ.get("MISEPORT_ALLOWED_ORIGINS", ""))
    args = parser.parse_args(argv)
    if not args.catalog:
        parser.error("provide --catalog or MISEPORT_CATALOG")
    if not 1 <= args.port <= 65535:
        parser.error("port must be in 1..65535")
    try:
        app = create_app(args.catalog, host=args.host,
                         allowed_hosts=[v.strip() for v in args.allowed_hosts.split(",") if v.strip()],
                         allowed_origins=[v.strip() for v in args.allowed_origins.split(",") if v.strip()])
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, proxy_headers=False,
                timeout_keep_alive=5, timeout_graceful_shutdown=20, access_log=False)


if __name__ == "__main__":
    main()
