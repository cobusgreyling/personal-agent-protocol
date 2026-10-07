"""The visit, over HTTP, against a Northline on a free port."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent import HARBOUR, PersonalAgent, customer_grants_access, grant, request
from northline import serve

ROOT = Path(__file__).resolve().parents[2]


class VisitTest(unittest.TestCase):
    def setUp(self):
        self.server, self.origin = serve()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_discovery_matches_the_illustration(self):
        static = json.loads((ROOT / "examples/discovery/.well-known/personal-agent.json").read_text())
        status, live = request("GET", f"{self.origin}/.well-known/personal-agent.json")
        self.assertEqual(status, 200)
        self.assertEqual(set(static), set(live))
        self.assertEqual(
            [item["route"] for item in static["interfaces"]],
            [item["route"] for item in live["interfaces"]],
        )
        self.assertTrue(live["sign_in"]["authorization_endpoint"].startswith(self.origin))
        spec_status, spec = request("GET", live["interfaces"][1]["openapi"])
        self.assertEqual(spec_status, 200)
        self.assertEqual(spec["paths"]["/orders/{order_id}/delivery-address"]["patch"]["operationId"], "updateDeliveryAddress")
        yaml_text = (ROOT / "examples/routes/api/openapi.yaml").read_text()
        self.assertIn("operationId: updateDeliveryAddress", yaml_text)
        self.assertIn("operationId: getOrder", yaml_text)

    def test_open_order_stays_one_session_and_hides_the_address_from_a_guest(self):
        agent = PersonalAgent(self.origin)
        agent.discover()
        agent.open_visit()
        policy = agent.read_returns_policy()
        self.assertEqual(policy["seen_agent"], agent.agent_id)
        reroute = agent.ask_reroute("NL-20418")
        self.assertTrue(reroute["reroutable"])
        self.assertNotIn("Loop Street", json.dumps(reroute))
        self.assertEqual(agent.route_for("order.delivery_address.update"), "api")

        guest = agent.session()
        self.assertEqual(guest["access"], "none")
        self.assertEqual(guest["events"][0]["type"], "guest_question")

        issued = grant(agent, "write")
        self.assertIn("orders:write", issued["scope"])
        status, body = agent.update_address("NL-20418", HARBOUR)
        self.assertEqual(status, 200)
        self.assertEqual(body["route"], "api")

        visit = agent.session()
        self.assertEqual(visit["session_id"], guest["session_id"])
        self.assertEqual(visit["subject"]["customer"], "cus_northline_441")
        self.assertEqual(
            [event["type"] for event in visit["events"]],
            ["guest_question", "customer_granted_access", "route_selected", "task_completed"],
        )
        status, order = agent.read_order("NL-20418")
        self.assertEqual(status, 200)
        self.assertEqual(order["address"]["line1"], "18 Harbour Road")

    def test_read_access_can_see_the_order_and_cannot_change_it(self):
        agent = PersonalAgent(self.origin)
        agent.discover()
        agent.open_visit()
        agent.ask_reroute("NL-20418")
        grant(agent, "read")
        status, order = agent.read_order("NL-20418")
        self.assertEqual(status, 200)
        self.assertEqual(order["address"]["line1"], "4 Loop Street")
        status, body = agent.update_address("NL-20418", HARBOUR)
        self.assertEqual(status, 403)
        self.assertIn("orders:write", body["error"])
        status, order = agent.read_order("NL-20418")
        self.assertEqual(order["address"]["line1"], "4 Loop Street")

    def test_guest_and_missing_token_cannot_patch(self):
        status, body = request(
            "PATCH",
            f"{self.origin}/orders/NL-20418/delivery-address",
            {"session_id": "ses_missing", "address": HARBOUR},
        )
        self.assertEqual(status, 401)
        self.assertIn("bearer", body["error"])

    def test_shipped_order_continues_on_the_company_agent(self):
        agent = PersonalAgent(self.origin)
        agent.discover()
        agent.open_visit()
        reroute = agent.ask_reroute("NL-20990")
        self.assertFalse(reroute["reroutable"])
        self.assertNotIn("Loop Street", json.dumps(reroute))
        grant(agent, "write")
        status, declined = agent.update_address("NL-20990", HARBOUR)
        self.assertEqual(status, 409)
        self.assertEqual(declined["route"], "agent")
        self.assertTrue(declined["continue_at"].startswith(self.origin))

        status, conversation = agent.tell_company_agent(
            "delivery.already_shipped",
            "Please send NL-20990 to 18 Harbour Road.",
            continue_at=declined["continue_at"],
        )
        self.assertEqual(status, 200)
        self.assertEqual(conversation["session_id"], agent.session_id)
        speakers = [turn["speaker"] for turn in conversation["turns"]]
        self.assertEqual(speakers, ["personal_agent", "company_agent", "person"])
        spoken = " ".join(turn["text"] for turn in conversation["turns"])
        self.assertIn("guest answer", spoken)
        visit = agent.session()
        self.assertEqual(visit["channel"], "agent")
        self.assertIn("route_declined", [event["type"] for event in visit["events"]])

    def test_warranty_names_the_speaker(self):
        agent = PersonalAgent(self.origin)
        agent.discover()
        self.assertEqual(agent.route_for("warranty.claim"), "agent")
        agent.open_visit()
        grant(agent, "write")
        status, conversation = agent.tell_company_agent(
            "warranty.claim",
            "Order NL-20418 arrived with a cracked lid. The customer wants a replacement.",
        )
        self.assertEqual(status, 200)
        person = conversation["turns"][-1]
        self.assertEqual(person["speaker"], "person")
        self.assertIn("Hold the shipment", person["text"])

    def test_a_token_cannot_act_in_another_visit(self):
        first = PersonalAgent(self.origin)
        first.discover()
        first.open_visit()
        grant(first, "write")
        second = PersonalAgent(self.origin)
        second.discover()
        second.open_visit()
        second.token = first.token
        status, body = second.update_address("NL-20418", HARBOUR)
        self.assertEqual(status, 403)
        self.assertIn("different visit", body["error"])

    def test_a_code_is_single_use_and_bound_to_the_agent(self):
        agent = PersonalAgent(self.origin)
        agent.discover()
        agent.open_visit()
        code = customer_grants_access(
            agent.discovery["sign_in"]["authorization_endpoint"],
            session_id=agent.session_id,
            personal_agent=agent.agent_id,
            access="write",
        )
        status, _ = request(
            "POST",
            agent.discovery["sign_in"]["token_endpoint"],
            {"grant_type": "authorization_code", "code": code, "client_id": "someone_else"},
        )
        self.assertEqual(status, 403)
        agent.exchange(code)
        status, body = request(
            "POST",
            agent.discovery["sign_in"]["token_endpoint"],
            {"grant_type": "authorization_code", "code": code, "client_id": agent.agent_id},
        )
        self.assertEqual(status, 400)
        self.assertIn("spent", body["error"])


if __name__ == "__main__":
    unittest.main()
