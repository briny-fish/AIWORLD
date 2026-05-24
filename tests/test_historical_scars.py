import unittest

from virtual_society import Simulation
from virtual_society.historical_scars import build_historical_scar_validation
from virtual_society.model import Organization


class HistoricalScarValidationTests(unittest.TestCase):
    def test_validation_reports_active_persistent_scars(self) -> None:
        simulation = Simulation(seed=7)
        simulation.world.relationship_crises["a1|a2"] = 3
        simulation.world.blocked_routes["commons|north_field"] = 0.75
        simulation.world.organization_fractures["common_council"] = 4
        simulation.world.organizations.append(
            Organization(
                id="common_council_splinter",
                name="Common Council Splinter",
                kind="council_splinter",
                members=["a1", "a2"],
            )
        )

        validation = build_historical_scar_validation(simulation.world)
        findings = {item["code"]: item for item in validation["findings"]}

        self.assertIn("passed", validation["summary"])
        self.assertEqual(validation["active_relationship_crises"], 1)
        self.assertEqual(validation["active_blocked_routes"], 1)
        self.assertEqual(validation["recorded_organization_fractures"], 1)
        self.assertEqual(findings["relationship_crises_persist"]["status"], "pass")
        self.assertEqual(findings["organization_fractures_persist"]["status"], "pass")
        self.assertEqual(findings["blocked_routes_affect_paths"]["status"], "pass")
        self.assertEqual(findings["repair_path_pending"]["status"], "info")

    def test_validation_uses_history_event_counts(self) -> None:
        simulation = Simulation(seed=7)
        history = {
            "snapshots": [
                {
                    "event_counts": {
                        "relationship_crisis": 3,
                        "reconciliation": 1,
                        "route_blocked": 2,
                        "route_reopened": 2,
                    },
                    "significant_events": [],
                }
            ]
        }

        validation = build_historical_scar_validation(simulation.world, history)

        self.assertEqual(validation["scar_event_counts"]["relationship_crisis"], 3)
        self.assertEqual(validation["scar_event_counts"]["route_reopened"], 2)
        self.assertIn("scars occurred", validation["summary"])


if __name__ == "__main__":
    unittest.main()
