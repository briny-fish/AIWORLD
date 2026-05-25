import unittest
import tempfile

from virtual_society import Simulation
from virtual_society.llm_cache import LLMCallCache
from virtual_society.model import Action
from virtual_society.openai_provider import (
    OpenAICognition,
    _extract_output_text,
    _resolve_responses_url,
)


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

    def test_openai_provider_includes_reasoning_effort(self) -> None:
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
        provider = OpenAICognition(
            api_key="test",
            reasoning_effort="low",
            http_post=fake_post,
        )

        provider.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(payloads[0]["reasoning"]["effort"], "low")

    def test_openai_provider_reads_and_writes_cache(self) -> None:
        calls = 0

        def fake_post(payload):
            nonlocal calls
            calls += 1
            return {
                "output_text": (
                    '{"action":"farm","priority":0.8,'
                    '"reason":"shared food stores are low",'
                    '"target_id":null,"horizon_days":1}'
                )
            }

        simulation = Simulation(seed=7)
        with tempfile.TemporaryDirectory() as directory:
            cache = LLMCallCache(directory, provider="openai-compatible")
            provider = OpenAICognition(api_key="test", cache=cache, http_post=fake_post)
            first = provider.propose_plan(simulation.world.agents[0], simulation.world)
            second = provider.propose_plan(simulation.world.agents[0], simulation.world)

        self.assertEqual(first.action, Action.FARM)
        self.assertEqual(second.action, Action.FARM)
        self.assertEqual(calls, 1)

    def test_resolve_responses_url_accepts_base_or_full_endpoint(self) -> None:
        self.assertEqual(
            _resolve_responses_url("https://dragoncode.codes/v1"),
            "https://dragoncode.codes/v1/responses",
        )
        self.assertEqual(
            _resolve_responses_url("https://dragoncode.codes/v1/responses"),
            "https://dragoncode.codes/v1/responses",
        )
        self.assertEqual(
            _resolve_responses_url("https://dragoncode.codes"),
            "https://dragoncode.codes/v1/responses",
        )

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
