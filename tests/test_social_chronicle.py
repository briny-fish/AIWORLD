import unittest

from virtual_society.social_chronicle import build_social_chronicle


class SocialChronicleTests(unittest.TestCase):
    def test_chronicle_turns_snapshot_events_into_story_entries(self) -> None:
        history = {
            "snapshots": [
                {
                    "day": 7,
                    "metrics": {
                        "average_need": 0.51,
                        "average_trust": 0.55,
                        "institutional_cohesion": 0.49,
                        "crisis_events": 2,
                    },
                    "trends": {"average_need": -0.08},
                    "event_counts": {
                        "organization_fracture": 1,
                        "route_blocked": 2,
                    },
                    "relationship_crises": {},
                    "blocked_routes": {"commons|north_field": 0.7},
                    "organization_fractures": {"common_council": 7},
                    "significant_events": [
                        {
                            "kind": "organization_fracture",
                            "description": "Common Council fractured; Ari and Bo formed a splinter.",
                        },
                        {
                            "kind": "route_blocked",
                            "description": "Route commons|north_field became blocked.",
                        },
                    ],
                }
            ]
        }

        chronicle = build_social_chronicle(
            history,
            [{"code": "shock_trace_active", "severity": "info", "description": "traceable"}],
        )

        self.assertIn("1 entries", chronicle["summary"])
        self.assertIn("shock_trace_active", chronicle["summary"])
        self.assertEqual(chronicle["entries"][0]["title"], "Institutional fracture")
        self.assertIn("organization fractures", chronicle["entries"][0]["summary"])
        self.assertIn("Common Council fractured", chronicle["entries"][0]["evidence"][-2])

    def test_empty_history_returns_empty_chronicle(self) -> None:
        chronicle = build_social_chronicle(None)

        self.assertEqual(chronicle["entries"], [])
        self.assertIn("No history snapshots", chronicle["summary"])


if __name__ == "__main__":
    unittest.main()
