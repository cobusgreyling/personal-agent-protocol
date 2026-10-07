"""Change one delivery address. From the repo root: python3 quickstart.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "examples" / "code"))

from agent import HARBOUR, PersonalAgent, grant
from northline import serve


def main() -> None:
    server, origin = serve()
    try:
        agent = PersonalAgent(origin)
        agent.discover()
        print(f"1. discover   {origin}/.well-known/personal-agent.json")

        agent.open_visit()
        print(f"2. session    {agent.session_id}  guest")

        reroute = agent.ask_reroute("NL-20418")
        print(f"3. guest ask  reroutable={str(reroute['reroutable']).lower()}")

        issued = grant(agent, "write")
        print(f"4. customer   granted {issued['scope']}")

        status, result = agent.update_address("NL-20418", HARBOUR)
        _, order = agent.read_order("NL-20418")
        print(f"5. api        {status} {result['status']} via {result['route']}")
        print(f"   address    {order['address']['line1']}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
