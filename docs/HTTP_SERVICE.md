# Demo HTTP service

The HTTP entrypoint serves a dated, entirely synthetic catalog using MCP SDK
**1.28.0** Streamable HTTP at `/mcp`. It has no checkout, payment, reservation,
live stock lookup, or write tools. HTTP startup refuses an empty catalog or any
product with `is_demo=false`. Never mount a real merchant catalog into this
public demonstration service.

Install the project, then run locally:

```text
miseport-http --catalog examples/products.json --host 127.0.0.1 --port 8000
```

`GET /healthz` returns only `ready`, `demo`, `version`, and `count`. It does not
return a filesystem path. `POST /mcp` implements the existing seven read-only
tools, with JSON responses and stateless sessions. Clients must send MCP's
`Accept: application/json, text/event-stream` and appropriate protocol headers.
Browser CORS access is not enabled; an Origin allowlist is request validation,
not CORS authorization.

## Public binding

Public binding requires **both** explicit host and origin allowlists. These are
comma-separated values; whitespace around entries is removed. `Host` entries
are exact hostnames, optionally with a fixed port or `:*` for any numeric port.
`*`, `*.example.com`, schemes, paths, credentials, and malformed ports are
rejected. Origins are exact HTTP(S) origins with optional fixed port and no
trailing slash, path, credentials, or wildcards. An absent Origin is allowed
for native MCP clients. An unlisted Origin is rejected.

```text
miseport-http --catalog examples/products.json --host 0.0.0.0 --port 8000 --allowed-hosts demo.example.com,127.0.0.1:8000 --allowed-origins https://chatgpt.com
```

Replace these example domains with the actual service Host and client Origin.
Use only observed or documented client origins; do not widen the allowlist
to work around a failed connection. A deployment health probe also needs an
allowed Host header. Loopback defaults allow `127.0.0.1:*`, `localhost:*`, and
`[::1]:*`; default browser origins are `http://127.0.0.1` and `http://localhost`.
Specify an exact origin with port when needed.

| CLI | Environment | Default |
| --- | --- | --- |
| `--catalog` | `MISEPORT_CATALOG` | required |
| `--host` | `MISEPORT_HTTP_HOST` | `127.0.0.1` |
| `--port` | `MISEPORT_HTTP_PORT` | `8000` |
| `--allowed-hosts` | `MISEPORT_ALLOWED_HOSTS` | loopback only |
| `--allowed-origins` | `MISEPORT_ALLOWED_ORIGINS` | loopback only |

All requests, including health probes, are subject to a 64 KiB body limit,
15-second total request deadline, 120 requests per rolling minute per process,
and 16 concurrent requests per process. Limits return 413, 504, 429, or 503
respectively. Invalid Host returns 421; invalid Origin returns 403. No request
body or access log is recorded by this entrypoint. Limits do not coordinate
across replicas. This is an unauthenticated public demo, not a production
merchant gateway.

Terminate TLS at the hosting provider or a reverse proxy. Forward the original
Host, configure its exact public domain, and enforce additional edge limits if
needed. The application does not trust forwarded headers. Avoid streaming GET
connections; this deployment deliberately uses bounded stateless JSON requests.

## Container

```text
docker build -f Dockerfile.http -t miseport-http .
docker run --rm -p 8000:8000 -e MISEPORT_ALLOWED_HOSTS=localhost:8000,127.0.0.1:8000 -e MISEPORT_ALLOWED_ORIGINS=https://chatgpt.com miseport-http
```

The image runs as the non-root `miseport` user and defaults to port 8000 on
`0.0.0.0`. It intentionally cannot start without explicit allowlists. Set
`MISEPORT_HTTP_PORT` if a provider assigns another port; a provider's generic
`PORT` variable is not read automatically.

## SDK references and validation

Implementation was checked against the installed `mcp==1.28.0` sources and the
official tagged
[FastMCP server implementation](https://github.com/modelcontextprotocol/python-sdk/blob/v1.28.0/src/mcp/server/fastmcp/server.py)
and [transport security implementation](https://github.com/modelcontextprotocol/python-sdk/blob/v1.28.0/src/mcp/server/transport_security.py).
It sets `stateless_http=True`, `json_response=True`, and explicit
`TransportSecuritySettings` before building `streamable_http_app()`; the SDK's
ASGI lifespan owns its session manager. Additional ASGI middleware applies
bounded resource handling and validates all routes.

`tests/test_http.py` exercises the actual SDK ASGI app: initialization, seven
tool discovery, quoting, demo metadata, host/origin guards, strict startup,
body/rate/concurrency/deadline boundaries. These local checks do not establish
public availability, TLS correctness, Muse connection success, or discovery.
