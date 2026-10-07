"""Run the Northline visit from the announcement.

    python3 examples/code/demo.py
    python3 examples/code/demo.py --serve
"""

from __future__ import annotations

import sys
import threading

from agent import HARBOUR, PersonalAgent, grant
from northline import serve


def line(text: str = "") -> None:
    print(text)


def begin(origin: str, order_id: str) -> tuple[PersonalAgent, dict]:
    agent = PersonalAgent(origin)
    discovery = agent.discover()
    routes = ", ".join(item["route"] for item in discovery["interfaces"])
    agent.open_visit()
    policy = agent.read_returns_policy()
    reroute = agent.ask_reroute(order_id)
    line(f"  discovered routes: {routes}")
    line(f"  session {agent.session_id} opened as a guest")
    line(f"  returns policy: {policy['policy']}")
    line(f"  reroutable: {'yes' if reroute['reroutable'] else 'no'} — {reroute['detail']}")
    return agent, reroute


def open_order(origin: str) -> None:
    line("1. Open order NL-20418, customer grants write")
    agent, _ = begin(origin, "NL-20418")
    route = agent.route_for("order.delivery_address.update")
    line(f"  business prefers this task on the {route}")
    issued = grant(agent, "write")
    line(f"  customer granted {issued['scope']}")
    status, body = agent.update_address("NL-20418", HARBOUR)
    line(f"  API {status}: {body['status']} via {body['route']}")
    visit = agent.session()
    names = ", ".join(event["type"] for event in visit["events"])
    _, order = agent.read_order("NL-20418")
    line(f"  one visit, events: {names}")
    line(f"  address is now {order['address']['line1']}")


def read_only(origin: str) -> None:
    line("2. Open order NL-18820, customer grants read")
    agent, _ = begin(origin, "NL-18820")
    issued = grant(agent, "read")
    line(f"  customer granted {issued['scope']}")
    status, order = agent.read_order("NL-18820")
    line(f"  read {status}: order {order['order_id']} is {order['status']}, {order['address']['line1']}")
    status, body = agent.update_address("NL-18820", HARBOUR)
    line(f"  API {status}: {body['error']}")
    _, order = agent.read_order("NL-18820")
    line(f"  address remains {order['address']['line1']}")


def shipped(origin: str) -> None:
    line("3. Order NL-20990 has left the depot")
    agent, _ = begin(origin, "NL-20990")
    grant(agent, "write")
    line("  customer granted write, and the agent still tries the API")
    status, body = agent.update_address("NL-20990", HARBOUR)
    line(f"  API {status}: {body['status']}, continue at the {body['route']}")
    text = "Please send NL-20990 to 18 Harbour Road. The customer asked before it left."
    status, conversation = agent.tell_company_agent(
        "delivery.already_shipped",
        text,
        continue_at=body["continue_at"],
    )
    line(f"  company agent {status}, same session {conversation['session_id']}")
    for turn in conversation["turns"]:
        if turn["speaker"] == "personal_agent":
            continue
        line(f"  {turn['speaker']}: {turn['text']}")


def warranty(origin: str) -> None:
    line("4. Warranty claim, a conversation from the start")
    agent = PersonalAgent(origin)
    agent.discover()
    agent.open_visit()
    route = agent.route_for("warranty.claim")
    line(f"  session {agent.session_id}")
    line(f"  business prefers this task on the {route}")
    grant(agent, "write")
    status, conversation = agent.tell_company_agent(
        "warranty.claim",
        "Order NL-20418 arrived with a cracked lid. The customer wants a replacement, shipped to the address on the order.",
    )
    line(f"  company agent {status}")
    for turn in conversation["turns"]:
        if turn["speaker"] == "personal_agent":
            continue
        line(f"  {turn['speaker']}: {turn['text']}")


def run_demo(origin: str) -> None:
    line(f"Northline Goods  {origin}")
    line()
    open_order(origin)
    line()
    read_only(origin)
    line()
    shipped(origin)
    line()
    warranty(origin)


def main(argv: list[str]) -> None:
    server, origin = serve()
    if "--serve" in argv:
        line(f"Northline Goods  {origin}")
        line(f"discovery        {origin}/.well-known/personal-agent.json")
        line("stop with Ctrl-C")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            line()
        finally:
            server.shutdown()
            server.server_close()
        return
    try:
        run_demo(origin)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main(sys.argv[1:])
