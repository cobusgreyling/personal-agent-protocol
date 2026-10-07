# A delivery address

One visit to a fictional shop, Northline Goods. Order `NL-20418` is open. The customer asks their personal agent two things: whether the order can still be rerouted, and, if it can, to send it to a new address.

The files linked below are a reading model of the 6 October 2026 announcement. The field names are not the specification.

Run the same visit locally:

```bash
python3 examples/code/demo.py
```

## 1. Discover the business

The agent fetches one document and learns where to sign in and which doors are open.

[examples/discovery/.well-known/personal-agent.json](../examples/discovery/.well-known/personal-agent.json)

Northline publishes all three routes. The document says open-order edits are served by the API, and that a parcel which has already left the depot is served by Northline's own agent. That preference is a teaching choice. The announcement says the business decides what it makes available.

## 2. Ask as a guest

"Can order NL-20418 still be rerouted?" is a question about an order, so a strict reading might require sign-in. Northline's reading model treats the reroute window as public: yes or no, with no address and no account detail. The agent asks on the website, as a guest.

[examples/session/guest.json](../examples/session/guest.json)

The answer is yes. The visit has an id, `ses_7f3a`, and no access to the account.

Which pages a guest may open is listed in [examples/routes/website.md](../examples/routes/website.md).

## 3. The customer grants write access

Changing the address touches the account. The customer signs in on Northline's page and chooses write access for this agent. The session is OAuth. `ses_7f3a` continues. The guest question stays part of the visit.

[examples/session/authorized.json](../examples/session/authorized.json)

## 4. Northline chooses the API

The order is still open, so the preferred route is the API. The agent sends one update: the session id, the order, and the new address. The token carries the write scope the customer granted.

[examples/routes/api/openapi.yaml](../examples/routes/api/openapi.yaml)

Northline applies its own rules, accepts the address, and the visit closes on that result.

## 5. The same visit, had it needed a conversation

If the parcel had already left the depot, the API would no longer be the right door. The agent would continue `ses_7f3a` with Northline's agent: the guest answer, the sign-in, and the requested address already in the thread. A person joins when the case needs a decision, and each reply names the speaker.

[examples/routes/agent/warranty.md](../examples/routes/agent/warranty.md)

The sample transcript uses a damaged-on-arrival claim, the announcement's kind of conversational task, and shows the same session discipline.
