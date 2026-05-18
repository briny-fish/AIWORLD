import json
import tempfile
import unittest
from pathlib import Path

from virtual_society.interventions import Intervention, load_interventions


class InterventionTests(unittest.TestCase):
    def test_intervention_file_loads_json_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "interventions.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "day": 3,
                            "kind": "broadcast",
                            "reason": "test",
                            "params": {"tone": "hope", "strength": 0.1},
                        }
                    ]
                ),
                encoding="utf-8",
            )

            interventions = load_interventions(path)

        self.assertEqual(
            interventions,
            [
                Intervention(
                    day=3,
                    kind="broadcast",
                    reason="test",
                    params={"tone": "hope", "strength": 0.1},
                )
            ],
        )

    def test_intervention_day_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            Intervention.from_dict({"day": 0, "kind": "resource"})


if __name__ == "__main__":
    unittest.main()

