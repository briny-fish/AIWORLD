import unittest

from virtual_society import Simulation
from virtual_society.model import Action
from virtual_society.openai_provider import OpenAICognition, _extract_output_text


class OpenAIProviderTests(unittest.TestCase):
    def test_openai_provider_parses_structured_response(self) -> None:
        payloads = []

        def fake_post(payload):
            payloads.append(payload)
            return {
                "output_text": (
                    '{"action":"farm","priority":0.8,'
                    '"reason":"shared food stores are low",'
                    '"target_id":null,"horizon_days":1}'
                )
            }

        simulation = Simulation(seed=7)
        provider = OpenAICognition(api_key="test", http_post=fake_post)

        plan = provider.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(plan.action, Action.FARM)
        self.assertEqual(plan.priority, 0.8)
        self.assertEqual(payloads[0]["text"]["format"]["type"], "json_schema")

    def test_extract_output_text_handles_nested_responses_output(self) -> None:
        text = _extract_output_text(
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": (
                                    '{"action":"rest","priority":0.4,'
                                    '"reason":"energy is low",'
                                    '"target_id":null,"horizon_days":1}'
                                ),
                            }
                        ]
                    }
                ]
            }
        )

        self.assertIn('"action":"rest"', text)


if __name__ == "__main__":
    unittest.main()
