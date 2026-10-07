"""A personal agent that follows the doors Northline publishes.

URLs come from the discovery document and from the OpenAPI document it
points at. The customer grant is a separate function: the agent receives
a code, and does not choose its own access.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

CUSTOMER_ID = "cus_northline_441"
HARBOUR = {
    "line1": "18 Harbour Road",
    "city": "Cape Town",
    "postal_code": "8001",
    "country": "ZA",
}


def request(method: str, url: str, body: dict | None = None, headers: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw.decode(errors="replace")}
        return exc.code, payload


def customer_grants_access(
    authorization_endpoint: str,
    *,
    session_id: str,
    personal_agent: str,
    access: str,
    customer_id: str = CUSTOMER_ID,
) -> str:
    """The customer, on the company's page, chooses read or write."""
    status, body = request(
        "POST",
        authorization_endpoint,
        {
            "session_id": session_id,
            "personal_agent": personal_agent,
            "customer_id": customer_id,
            "access": access,
        },
    )
    if status != 200:
        raise RuntimeError(f"customer grant failed: {status} {body}")
    return body["code"]


class PersonalAgent:
    def __init__(self, origin: str, agent_id: str = "personal_agent_example"):
        self.origin = origin.rstrip("/")
        self.agent_id = agent_id
        self.discovery: dict | None = None
        self.session_id: str | None = None
        self.token: str | None = None
        self.scope: str | None = None

    def discover(self) -> dict:
        status, body = request("GET", f"{self.origin}/.well-known/personal-agent.json")
        if status != 200:
            raise RuntimeError(body)
        self.discovery = body
        return body

    def interface(self, route: str) -> dict:
        for item in self.discovery["interfaces"]:
            if item["route"] == route:
                return item
        raise LookupError(route)

    def route_for(self, task: str) -> str | None:
        for item in self.discovery["interfaces"]:
            if task in item.get("preferred_for", []):
                return item["route"]
        return None

    def open_visit(self) -> dict:
        status, body = request("POST", f"{self.origin}/sessions", {"personal_agent": self.agent_id})
        if status != 201:
            raise RuntimeError(body)
        self.session_id = body["session_id"]
        return body

    def _seen(self) -> dict:
        return {"X-Personal-Agent": self.agent_id}

    def read_returns_policy(self) -> dict:
        url = self.interface("website")["pages"]["returns_policy"]
        status, body = request("GET", url, headers=self._seen())
        if status != 200:
            raise RuntimeError(body)
        return body

    def ask_reroute(self, order_id: str) -> dict:
        template = self.interface("website")["pages"]["reroute_window"]
        url = template.format(order_id=order_id) + f"?session_id={self.session_id}"
        status, body = request("GET", url, headers=self._seen())
        if status != 200:
            raise RuntimeError(body)
        return body

    def exchange(self, code: str) -> dict:
        status, body = request(
            "POST",
            self.discovery["sign_in"]["token_endpoint"],
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.agent_id,
            },
        )
        if status != 200:
            raise RuntimeError(body)
        self.token = body["access_token"]
        self.scope = body["scope"]
        return body

    def _operation(self, operation_id: str):
        status, spec = request("GET", self.interface("api")["openapi"])
        if status != 200:
            raise RuntimeError(spec)
        for path, methods in spec["paths"].items():
            for method, operation in methods.items():
                if isinstance(operation, dict) and operation.get("operationId") == operation_id:
                    return spec["servers"][0]["url"], method.upper(), path
        raise LookupError(operation_id)

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def read_order(self, order_id: str):
        server, method, path = self._operation("getOrder")
        url = server + path.format(order_id=order_id) + f"?session_id={self.session_id}"
        return request(method, url, headers=self._auth())

    def update_address(self, order_id: str, address: dict):
        server, method, path = self._operation("updateDeliveryAddress")
        url = server + path.format(order_id=order_id)
        return request(
            method,
            url,
            {"session_id": self.session_id, "address": address},
            headers=self._auth(),
        )

    def tell_company_agent(self, task: str, text: str, continue_at: str | None = None):
        url = continue_at or self.interface("agent")["url"]
        return request(
            "POST",
            url,
            {"session_id": self.session_id, "task": task, "text": text},
            headers=self._auth(),
        )

    def session(self) -> dict:
        status, body = request("GET", f"{self.origin}/sessions/{self.session_id}")
        if status != 200:
            raise RuntimeError(body)
        return body


def grant(agent: PersonalAgent, access: str) -> dict:
    code = customer_grants_access(
        agent.discovery["sign_in"]["authorization_endpoint"],
        session_id=agent.session_id,
        personal_agent=agent.agent_id,
        access=access,
    )
    return agent.exchange(code)
