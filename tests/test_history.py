import tempfile
import unittest
from pathlib import Path

from virtual_society import Simulation
from virtual_society.history import HistoryRecorder, write_snapshot_files


class HistoryTests(unittest.TestCase):
    def test_history_recorder_captures_periodic_snapshots(self) -> None:
        recorder = HistoryRecorder(seed=7, interval_days=10)
        simulation = Simulation(seed=7)

        metrics = simulation.run(30, after_step=recorder.capture)
        recorder.capture(simulation.world, metrics[-1], force=True)
        history = recorder.record(metrics)

        self.assertEqual([snapshot["day"] for snapshot in recorder.snapshots], [1, 10, 20, 30])
        self.assertEqual(history["snapshot_count"], 4)
        self.assertIn("average need", history["summary"])
        self.assertTrue(recorder.snapshots[-1]["organizations"])

    def test_history_snapshot_contains_counts_and_low_need_agents(self) -> None:
        recorder = HistoryRecorder(seed=7, interval_days=5)
        simulation = Simulation(seed=7)

        metrics = simulation.run(5, after_step=recorder.capture)
        recorder.capture(simulation.world, metrics[-1], force=True)

        snapshot = recorder.snapshots[-1]
        self.assertEqual(snapshot["day"], metrics[-1].day)
        self.assertIn("event_counts", snapshot)
        self.assertIn("plan_counts", snapshot)
        self.assertIn("summary", snapshot)
        self.assertIsInstance(snapshot["low_need_agents"], list)

    def test_write_snapshot_files_creates_one_file_per_snapshot(self) -> None:
        recorder = HistoryRecorder(seed=7, interval_days=3)
        simulation = Simulation(seed=7)
        metrics = simulation.run(6, after_step=recorder.capture)
        recorder.capture(simulation.world, metrics[-1], force=True)

        with tempfile.TemporaryDirectory() as directory:
            write_snapshot_files(directory, recorder.snapshots)

            files = sorted(path.name for path in Path(directory).glob("*.json"))

        self.assertEqual(files, ["day-0001.json", "day-0003.json", "day-0006.json"])


if __name__ == "__main__":
    unittest.main()
