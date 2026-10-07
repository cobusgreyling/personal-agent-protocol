# Website route

Northline's ordinary pages. The personal agent is identified as an agent. A guest may read what any visitor may read. The account waits for the customer.

This list is a reading model of the website route in the 6 October 2026 announcement. It is not a browser protocol.

| Page | Guest | After the customer grants access |
| --- | --- | --- |
| Product and stock | Yes | Yes |
| Returns policy | Yes | Yes |
| Whether an open order can still be rerouted, yes or no | Yes. No address, no account detail. | Yes |
| The order itself | No | Read, or write, as the customer chose |
| Change the delivery address | No | Write, if the customer granted it |
| Warranty claim | No | Handed to the company agent |

In the walkthrough, the guest question in step 2 is the third row. The address change itself leaves this route and continues on the API, inside the same session.

The running example serves the returns policy at `/returns` and the reroute window at `/orders/{order_id}/reroute`. Both identify the caller from `X-Personal-Agent`. The order itself is `GET /orders/{order_id}` after the customer grants access.
