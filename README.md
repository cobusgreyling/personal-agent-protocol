![Personal Agent Protocol](assets/header.png)

# Personal Agent Protocol

Quick start for a personal agent talking to a business. Python 3.11 or newer. The standard library is enough.

This is a running model of the visit announced on 6 October 2026. Version 0.1 of the specification is not published yet. The field names belong to the sample shop, Northline Goods.

```bash
python3 quickstart.py
```

That command starts the shop, then does five things:

1. Discover the business at `/.well-known/personal-agent.json`.
2. Open a guest session.
3. Ask whether order `NL-20418` can still be rerouted. The answer leaves the street out.
4. The customer grants write access. The agent exchanges the code for a bearer token.
5. `PATCH` the delivery address. The guest question and the change are one session.

You should see the address become `18 Harbour Road`.

## Use the client

`examples/code/agent.py` follows the URLs in the discovery document. `grant` is the customer, on the company's page. The agent only receives the code.

```python
from agent import HARBOUR, PersonalAgent, grant
from northline import serve

server, origin = serve()
agent = PersonalAgent(origin)
agent.discover()
agent.open_visit()
agent.ask_reroute("NL-20418")
grant(agent, "write")          # customer chooses "read" or "write"
agent.update_address("NL-20418", HARBOUR)
server.shutdown()
```

Run that from `examples/code`, or run `python3 quickstart.py` from the repo root.

A read grant can see the order. It cannot change the address. If the parcel has already left, the API returns `409` and `continue_at`. Post that same session to the company agent.

## The other three visits

```bash
python3 examples/code/demo.py
python3 examples/code/test_visit.py
```

| Visit | What you see |
| --- | --- |
| `NL-18820`, read grant | The agent can read 4 Loop Street. The address change is refused. |
| `NL-20990`, already shipped | The API returns 409. The company agent continues the session. A person joins, and the reply names the speaker. |
| Warranty on `NL-20418` | Discovery sends the task straight to the company agent. |

`python3 examples/code/demo.py --serve` leaves the shop up. Call `$ORIGIN/.well-known/personal-agent.json`.

## Where to look

| Path | What it is |
| --- | --- |
| `quickstart.py` | The one-visit command above. |
| `examples/code/` | The shop, the personal agent, the four-visit demo, the tests. |
| `examples/discovery/.well-known/personal-agent.json` | The document an agent fetches first. |
| `examples/routes/api/openapi.yaml` | The order call the API route uses. |
| `docs/walkthrough.md` | The same address change, step by step. |
| `docs/model.md` | What the announcement fixes in place, and what these files invent. |
| `blog/personal-agent-protocol.md` | The essay. |

Tokens are random strings kept in memory until the process stops. They follow the shape of an OAuth authorization-code grant so the visit can be run.
