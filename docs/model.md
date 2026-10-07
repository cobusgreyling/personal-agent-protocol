# The model

This page separates what the 6 October 2026 announcement says from the teaching layer added in this repository.

Personal Agent Protocol is an open standard Meta and Sierra are developing with Genesys, Instinct, Rocket, Shopify, Stripe, and Walmart. It defines how a personal agent, acting for a customer, interacts with a business. Sierra describes the first job as authentication, customer control, and visibility for the company, through the company's website, its APIs, or an agent of its own.

Version 0.1 of the specification has not been published. Nothing below is that specification.

## Actors

| Actor | Role in the announcement |
| --- | --- |
| Customer | Decides what access the personal agent receives, including read-only or write. Signs in on the company's page, or has already granted credentials. |
| Personal agent | Acts for one customer. Discovers the business, opens the session, and completes the task by the route the business offers. |
| Business | Decides what to publish, what an agent may do, and which route serves the customer. Sees that an agent is acting. |
| Company agent | Handles work that needs a conversation, such as a warranty claim. |
| Person at the business | Joins the same conversation when the case needs judgment. NiCE's public description says each reply identifies whether an agent or a person is speaking. |

## What the announcement fixes in place

From Sierra, 6 October 2026:

- The visit starts on the website, where the personal agent discovers what the company offers and how to reach it.
- The agent begins a session on the user's behalf.
- A guest session can cover a public question, such as product availability or a returns policy.
- Account work waits for sign-in on the company's page, or for credentials the customer has already set up with the personal agent.
- The session is built on OAuth.
- The customer chooses read-only or write access.
- The session carries across channels. A question from before sign-in and a change made afterward are one visit.
- The business offers one or more routes:
  - **Website.** The company's ordinary pages.
  - **API.** Interfaces built on standards such as MCP and OpenAPI.
  - **Company agent.** A conversation for tasks that need one.
- Later extensions named in the same post: finer permissions on specific actions, push notification to the personal agent, and payments in which the agent completes a purchase without receiving the card number.

From NiCE's description of the same effort, reported on 7 October 2026:

- The business publishes one document the agent can read in a single request, listing sign-in endpoints and interfaces.
- Each personal agent receives its own token for each customer, scoped to what the company allows, and that token is usable across APIs, web pages, and conversation.
- A person can join the conversation with the context already in hand, and replies identify the speaker.

## The teaching layer in this repository

The announcement does not name a URL, a JSON shape, a token claim, or an event format. The examples invent those, for one fictional merchant, so the visit can be read end to end.

| File | Standing |
| --- | --- |
| `examples/discovery/.well-known/personal-agent.json` | An invented document an agent could fetch: sign-in, and the three interfaces. The path is a teaching choice. |
| `examples/session/guest.json` | A public question inside a new visit. Sample data. |
| `examples/session/authorized.json` | The same visit after the customer grants write access, leaving by the API. Sample data. |
| `examples/routes/website.md` | Which pages a guest may use, and which wait for the account. |
| `examples/routes/api/openapi.yaml` | The address change as one call, carrying the session. OpenAPI here is one way to show the API route Sierra described. |
| `examples/routes/agent/warranty.md` | A conversation in the same kind of visit, with a person joining. |
| `examples/code/` | A local Northline and a personal agent that run the visit over HTTP. |

The story those files share: an order at Northline Goods, a guest question about rerouting, then a change of delivery address. The worked sequence is in [the walkthrough](walkthrough.md).

## Open until version 0.1

The announcement leaves these to the specification:

- The discovery address, media type, and required fields.
- How an agent is identified while it uses ordinary web pages.
- The OAuth details: grant type, scopes, and how a guest becomes the signed-in customer inside one session.
- How a business advertises which route it prefers for a given task.
- The message format between a personal agent and a company agent.
- How a reply records whether the speaker is an agent or a person.
- What the payments extension and the push channel look like.

When the specification is published, revise this page first, then the examples.
