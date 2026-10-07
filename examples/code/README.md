# Run the visit

A local Northline Goods and a personal agent. Python 3.11 or newer, standard library only. The agent reads the discovery document, then uses the sign-in endpoints, the page URLs, the OpenAPI operation, and the company-agent URL it finds there.

The token step follows the shape of an OAuth authorization-code grant: the customer chooses `read` or `write` on the company's page, the agent exchanges the code, and later calls carry that token. Tokens are random strings kept in memory until the process stops.

```bash
python3 examples/code/demo.py
python3 examples/code/test_visit.py
```

The demo runs four visits.

1. Order `NL-20418` is open. The guest asks whether it can be rerouted, and the answer leaves the address out. The customer grants write. The business prefers this task on the API, and the address becomes 18 Harbour Road. The guest question and the change share one session.
2. Order `NL-18820` is open. The customer grants read. The agent can see the order. The address change is refused, and the street stays 4 Loop Street.
3. Order `NL-20990` has already left the depot. The API answers 409 and names the company-agent URL. The agent continues that same session there. A person joins, and the reply says who is speaking.
4. A cracked lid on `NL-20418` is a warranty claim. Discovery sends that task straight to the company agent. The transcript matches [the warranty sample](../routes/agent/warranty.md).

Leave the shop up and call it yourself:

```bash
python3 examples/code/demo.py --serve
```

Then, with the printed origin:

```bash
curl -s $ORIGIN/.well-known/personal-agent.json
```

| File | Role |
| --- | --- |
| `northline.py` | The business: discovery, pages, the grant, the order API, the company agent. |
| `agent.py` | The personal agent, plus `customer_grants_access`, which is the customer's action. |
| `demo.py` | Runs the four visits and prints each step. |
| `test_visit.py` | The same visits, asserted over HTTP. |
