import unittest

from virtual_society.observer import render_observer_html
from virtual_society.observer3d import render_observer3d_html


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
        self.assertIn('id="observerName"', html)
        self.assertIn("observerActorId", html)
        self.assertIn("actor_id", html)

    def test_3d_observer_renders_named_observer_controls(self) -> None:
        html = render_observer3d_html()

        self.assertIn('id="observerName"', html)
        self.assertIn("observerActorId", html)
        self.assertIn("actor_id", html)

    def test_3d_observer_consumes_world_client_frame(self) -> None:
        html = render_observer3d_html()

        self.assertIn("/client/world-frame", html)
        self.assertIn("latestFrame", html)
        self.assertIn("renderRoutes3d(frame.routes", html)


if __name__ == "__main__":
    unittest.main()
