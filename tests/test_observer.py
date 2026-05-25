import unittest

from virtual_society.observer import render_observer_html


class ObserverTests(unittest.TestCase):
    def test_observer_renders_historical_scars_panel(self) -> None:
        html = render_observer_html()

        self.assertIn("Historical Scars", html)
        self.assertIn('id="scars"', html)
        self.assertIn("renderScars(snapshot.world)", html)

    def test_observer_renders_intent_controls(self) -> None:
        html = render_observer_html()

        self.assertIn('id="intent"', html)
        self.assertIn('value="repair_routes"', html)
        self.assertIn('id="intentTarget"', html)
        self.assertIn('id="sendIntent"', html)
        self.assertIn("sendObserverIntent", html)


if __name__ == "__main__":
    unittest.main()
