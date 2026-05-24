import unittest

from virtual_society.observer import render_observer_html


class ObserverTests(unittest.TestCase):
    def test_observer_renders_historical_scars_panel(self) -> None:
        html = render_observer_html()

        self.assertIn("Historical Scars", html)
        self.assertIn('id="scars"', html)
        self.assertIn("renderScars(snapshot.world)", html)


if __name__ == "__main__":
    unittest.main()
