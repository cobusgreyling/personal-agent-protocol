"""Northline Goods, in one process.

A local business for the reading model in this repository: discovery,
a guest page, an OAuth-shaped grant, an order API, and a company agent.
Field names are a teaching device for the 6 October 2026 announcement.
Tokens are opaque strings held in memory for the life of the process.
"""

from __future__ import annotations

import json
import secrets
import threading
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASIS = (
    "Reading model of Personal Agent Protocol as announced by Sierra on "
    "6 October 2026. Field names are not the unpublished v0.1 specification."
)
CUSTOMER_ID = "cus_northline_441"
SCOPES = {
    "read": ["orders:read"],
    "write": ["orders:read", "orders:write"],
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _one(query: dict, name: str) -> str | None:
    values = query.get(name)
    return values[0] if values else None


class Northline:
    def __init__(self) -> None:
        self.orders = {
            "NL-20418": {
                "status": "open",
                "address": {
                    "line1": "4 Loop Street",
                    "city": "Cape Town",
                    "postal_code": "8001",
                    "country": "ZA",
                },
            },
            "NL-18820": {
                "status": "open",
                "address": {
                    "line1": "4 Loop Street",
                    "city": "Cape Town",
                    "postal_code": "8001",
                    "country": "ZA",
                },
            },
            "NL-20990": {
                "status": "shipped",
                "address": {
                    "line1": "4 Loop Street",
                    "city": "Cape Town",
                    "postal_code": "8001",
                    "country": "ZA",
                },
            },
        }
        self.sessions: dict[str, dict] = {}
        self.codes: dict[str, dict] = {}
        self.tokens: dict[str, dict] = {}

    def discovery(self, base: str) -> dict:
        return {
            "illustration": True,
            "basis": BASIS,
            "business": {"name": "Northline Goods", "url": base},
            "sign_in": {
                "grant": "oauth",
                "authorization_endpoint": f"{base}/oauth/authorize",
                "token_endpoint": f"{base}/oauth/token",
                "access_the_customer_chooses": ["read", "write"],
            },
            "interfaces": [
                {
                    "route": "website",
                    "url": base,
                    "guest_allowed": True,
                    "pages": {
                        "returns_policy": f"{base}/returns",
                        "reroute_window": f"{base}/orders/{{order_id}}/reroute",
                    },
                },
                {
                    "route": "api",
                    "styles": ["openapi", "mcp"],
                    "openapi": f"{base}/openapi.json",
                    "preferred_for": ["order.delivery_address.update"],
                },
                {
                    "route": "agent",
                    "url": f"{base}/agent",
                    "preferred_for": ["warranty.claim", "delivery.already_shipped"],
                },
            ],
        }

    def openapi_document(self, base: str) -> dict:
        return {
            "openapi": "3.1.0",
            "info": {
                "title": "Northline Goods order API",
                "version": "0.0.0-illustration",
                "description": BASIS,
            },
            "servers": [{"url": base}],
            "paths": {
                "/orders/{order_id}": {
                    "get": {
                        "operationId": "getOrder",
                        "summary": "Read an order in this visit",
                        "security": [{"customerAgent": ["orders:read"]}],
                        "parameters": [
                            {"name": "order_id", "in": "path", "required": True},
                            {"name": "session_id", "in": "query", "required": True},
                        ],
                    }
                },
                "/orders/{order_id}/delivery-address": {
                    "patch": {
                        "operationId": "updateDeliveryAddress",
                        "summary": "Change the delivery address on an open order",
                        "security": [{"customerAgent": ["orders:write"]}],
                        "parameters": [{"name": "order_id", "in": "path", "required": True}],
                    }
                },
            },
        }

    def dispatch(self, method: str, path: str, query: dict, headers, raw: bytes, base: str):
        body = {}
        if raw:
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                return 400, {"error": "body must be json"}
            if not isinstance(body, dict):
                return 400, {"error": "body must be a json object"}

        if method == "GET" and path == "/.well-known/personal-agent.json":
            return 200, self.discovery(base)
        if method == "GET" and path == "/openapi.json":
            return 200, self.openapi_document(base)
        if method == "GET" and path == "/":
            return 200, {
                "business": "Northline Goods",
                "discovery": f"{base}/.well-known/personal-agent.json",
                "orders": list(self.orders),
            }
        if method == "POST" and path == "/sessions":
            return self._open_session(body)
        if method == "GET" and path.startswith("/sessions/"):
            return self._show_session(path.removeprefix("/sessions/"))
        if method == "GET" and path == "/returns":
            return self._returns(headers)
        if method == "GET" and path.startswith("/orders/") and path.endswith("/reroute"):
            return self._reroute(path.split("/")[2], query, headers)
        if method == "GET" and path.startswith("/orders/") and path.count("/") == 2:
            return self._get_order(path.split("/")[2], query, headers)
        if method == "GET" and path == "/oauth/authorize":
            return 200, {
                "grant": "oauth",
                "customer_chooses": ["read", "write"],
                "submit": "POST session_id, personal_agent, customer_id, and access.",
            }
        if method == "POST" and path == "/oauth/authorize":
            return self._authorize(body)
        if method == "POST" and path == "/oauth/token":
            return self._token(body)
        if method == "PATCH" and path.startswith("/orders/") and path.endswith("/delivery-address"):
            return self._update_address(path.split("/")[2], body, headers, base)
        if method == "POST" and path == "/agent":
            return self._agent(body, headers)
        return 404, {"error": "no such route"}

    def _open_session(self, body: dict):
        agent = body.get("personal_agent")
        if not agent:
            return 400, {"error": "personal_agent is required"}
        session_id = "ses_" + secrets.token_hex(3)
        self.sessions[session_id] = {
            "session_id": session_id,
            "business": "Northline Goods",
            "subject": "guest",
            "authentication": None,
            "access": "none",
            "channel": "website",
            "personal_agent": agent,
            "customer": None,
            "events": [],
            "turns": [],
        }
        return 201, self._public_session(session_id)

    def _show_session(self, session_id: str):
        session, err = self._session(session_id)
        if err:
            return err
        return 200, self._public_session(session["session_id"])

    def _public_session(self, session_id: str) -> dict:
        session = self.sessions[session_id]
        view = {
            "illustration": True,
            "session_id": session["session_id"],
            "business": session["business"],
            "subject": session["subject"],
            "authentication": session["authentication"],
            "access": session["access"],
            "channel": session["channel"],
            "events": session["events"],
            "turns": session["turns"],
        }
        return view

    def _returns(self, headers):
        agent = headers.get("X-Personal-Agent")
        if not agent:
            return 400, {"error": "X-Personal-Agent is required on website calls"}
        return 200, {"policy": "Returns accepted within 30 days.", "seen_agent": agent}

    def _reroute(self, order_id: str, query: dict, headers):
        agent = headers.get("X-Personal-Agent")
        if not agent:
            return 400, {"error": "X-Personal-Agent is required on website calls"}
        session, err = self._session(_one(query, "session_id"))
        if err:
            return err
        if session["personal_agent"] != agent:
            return 403, {"error": "this visit was opened by a different personal agent"}
        order = self.orders.get(order_id)
        if order is None:
            return 404, {"error": "unknown order"}
        reroutable = order["status"] == "open"
        session["channel"] = "website"
        session["events"].append(
            {
                "at": _now(),
                "type": "guest_question",
                "channel": "website",
                "intent": f"Can order {order_id} still be rerouted?",
                "result": "Yes. The order is open." if reroutable else "No. The parcel has left the depot.",
            }
        )
        detail = (
            "The order is open. The address is not included in a guest answer."
            if reroutable
            else "The parcel has left the depot. The address is not included in a guest answer."
        )
        return 200, {
            "session_id": session["session_id"],
            "order_id": order_id,
            "reroutable": reroutable,
            "detail": detail,
        }

    def _authorize(self, body: dict):
        session, err = self._session(body.get("session_id"))
        if err:
            return err
        access = body.get("access")
        if access not in SCOPES:
            return 400, {"error": "access must be read or write"}
        if body.get("personal_agent") != session["personal_agent"]:
            return 403, {"error": "the customer can only approve the agent that opened this visit"}
        if body.get("customer_id") != CUSTOMER_ID:
            return 403, {"error": "unknown customer"}
        code = "code_" + secrets.token_hex(8)
        self.codes[code] = {
            "session_id": session["session_id"],
            "personal_agent": session["personal_agent"],
            "customer_id": CUSTOMER_ID,
            "access": access,
            "scope": list(SCOPES[access]),
        }
        return 200, {"code": code, "session_id": session["session_id"], "access": access}

    def _token(self, body: dict):
        if body.get("grant_type") != "authorization_code":
            return 400, {"error": "grant_type must be authorization_code"}
        grant = self.codes.pop(body.get("code"), None)
        if grant is None:
            return 400, {"error": "unknown or spent code"}
        if body.get("client_id") != grant["personal_agent"]:
            self.codes[body.get("code")] = grant
            return 403, {"error": "client_id does not match the approved agent"}
        access_token = "tok_" + secrets.token_hex(16)
        self.tokens[access_token] = grant
        session = self.sessions[grant["session_id"]]
        session["authentication"] = "oauth"
        session["access"] = grant["access"]
        session["customer"] = grant["customer_id"]
        session["subject"] = {
            "customer": grant["customer_id"],
            "personal_agent": grant["personal_agent"],
        }
        session["events"].append(
            {
                "at": _now(),
                "type": "customer_granted_access",
                "access": grant["access"],
                "via": "sign_in_on_company_page",
            }
        )
        return 200, {
            "access_token": access_token,
            "token_type": "Bearer",
            "scope": " ".join(grant["scope"]),
            "session_id": grant["session_id"],
        }

    def _get_order(self, order_id: str, query: dict, headers):
        token, err = self._bearer(headers)
        if err:
            return err
        if "orders:read" not in token["scope"]:
            return 403, {"error": "orders:read required"}
        session, err = self._bound_session(token, _one(query, "session_id"))
        if err:
            return err
        order = self.orders.get(order_id)
        if order is None:
            return 404, {"error": "unknown order"}
        return 200, {
            "session_id": session["session_id"],
            "order_id": order_id,
            "status": order["status"],
            "address": order["address"],
        }

    def _update_address(self, order_id: str, body: dict, headers, base: str):
        token, err = self._bearer(headers)
        if err:
            return err
        if "orders:write" not in token["scope"]:
            return 403, {"error": "orders:write required"}
        session, err = self._bound_session(token, body.get("session_id"))
        if err:
            return err
        address = body.get("address") or {}
        if not all(address.get(key) for key in ("line1", "city", "postal_code", "country")):
            return 400, {"error": "address requires line1, city, postal_code, and country"}
        order = self.orders.get(order_id)
        if order is None:
            return 404, {"error": "unknown order"}
        if order["status"] != "open":
            session["channel"] = "api"
            session["events"].append(
                {
                    "at": _now(),
                    "type": "route_declined",
                    "by": "business",
                    "route": "api",
                    "reason": "The parcel has left the depot.",
                }
            )
            return 409, {
                "session_id": session["session_id"],
                "order_id": order_id,
                "status": "already_shipped",
                "route": "agent",
                "continue_at": f"{base}/agent",
            }
        order["address"] = {key: address[key] for key in ("line1", "city", "postal_code", "country")}
        now = _now()
        session["channel"] = "api"
        session["events"].extend(
            [
                {
                    "at": now,
                    "type": "route_selected",
                    "by": "business",
                    "route": "api",
                    "reason": "The order is still open. Northline serves this task on the API.",
                },
                {
                    "at": now,
                    "type": "task_completed",
                    "channel": "api",
                    "operation": "updateDeliveryAddress",
                    "order_id": order_id,
                    "result": "Delivery address updated.",
                },
            ]
        )
        return 200, {
            "session_id": session["session_id"],
            "order_id": order_id,
            "status": "updated",
            "route": "api",
        }

    def _agent(self, body: dict, headers):
        token, err = self._bearer(headers)
        if err:
            return err
        session, err = self._bound_session(token, body.get("session_id"))
        if err:
            return err
        text = (body.get("text") or "").strip()
        task = body.get("task")
        if not text or not task:
            return 400, {"error": "task and text are required"}
        session["channel"] = "agent"
        session["turns"].append({"speaker": "personal_agent", "text": text})
        replies = self._replies(session, task)
        session["turns"].extend(replies)
        session["events"].append(
            {
                "at": _now(),
                "type": "conversation",
                "channel": "agent",
                "task": task,
                "speakers": [turn["speaker"] for turn in replies],
            }
        )
        return 200, {"session_id": session["session_id"], "task": task, "turns": list(session["turns"])}

    def _replies(self, session: dict, task: str) -> list[dict]:
        guest = next((event for event in session["events"] if event["type"] == "guest_question"), None)
        prior = f" The visit already includes the guest answer: {guest['result']}" if guest else ""
        if task == "warranty.claim":
            return [
                {
                    "speaker": "company_agent",
                    "text": "The order qualifies for a replacement. The lid is a warehouse item. I can ship it today.",
                },
                {
                    "speaker": "person",
                    "text": (
                        "Hold the shipment. That lid is in a batch we are checking. "
                        "I will send a different batch, or a refund of the lid, by tomorrow at 16:00."
                    ),
                },
            ]
        if task == "delivery.already_shipped":
            return [
                {
                    "speaker": "company_agent",
                    "text": (
                        "The parcel has left the depot, so the order API will not take a new address. "
                        "I am keeping this session and asking a person to decide." + prior
                    ),
                },
                {
                    "speaker": "person",
                    "text": (
                        "I have the guest answer and the address the customer asked for. "
                        "I can intercept the parcel at the depot or leave it on the original address. "
                        "I will confirm which by tomorrow at 16:00."
                    ),
                },
            ]
        return [
            {
                "speaker": "company_agent",
                "text": "I am handing this to a person. The task is outside the routes Northline publishes for an automatic answer.",
            },
            {
                "speaker": "person",
                "text": "I have joined this session. Send the order id and what the customer wants done.",
            },
        ]

    def _bearer(self, headers):
        header = headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None, (401, {"error": "bearer token required"})
        token = self.tokens.get(header.removeprefix("Bearer ").strip())
        if token is None:
            return None, (401, {"error": "unknown token"})
        return token, None

    def _session(self, session_id: str | None):
        if not session_id or session_id not in self.sessions:
            return None, (404, {"error": "unknown session"})
        return self.sessions[session_id], None

    def _bound_session(self, token: dict, session_id: str | None):
        if session_id != token["session_id"]:
            return None, (403, {"error": "token is for a different visit"})
        return self._session(session_id)


def serve(app: Northline | None = None) -> tuple[ThreadingHTTPServer, str]:
    app = app or Northline()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_PATCH(self):
            self._handle("PATCH")

        def _handle(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            parsed = urlparse(self.path)
            host = self.headers.get("Host", "127.0.0.1")
            try:
                status, payload = app.dispatch(
                    method,
                    parsed.path,
                    parse_qs(parsed.query),
                    self.headers,
                    raw,
                    f"http://{host}",
                )
            except Exception:
                traceback.print_exc()
                status, payload = 500, {"error": "internal"}
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"
