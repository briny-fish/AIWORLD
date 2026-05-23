from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from virtual_society import LLMCallCache


class LLMCallCacheTests(unittest.TestCase):
    def test_write_then_read_returns_cached_response(self) -> None:
        with TemporaryDirectory() as directory:
            cache = LLMCallCache(directory)

            path = cache.write(
                "cognition",
                "gpt-test",
                "low",
                "prompt",
                '{"action":"farm"}',
            )
            response = cache.read("cognition", "gpt-test", "low", "prompt")

            self.assertTrue(path.exists())
            self.assertEqual(response, '{"action":"farm"}')
            self.assertEqual(cache.stats.writes, 1)
            self.assertEqual(cache.stats.hits, 1)

    def test_cache_key_separates_surface_model_effort_and_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            cache = LLMCallCache(directory)
            cache.write("cognition", "gpt-a", "low", "prompt", "one")

            self.assertIsNone(cache.read("dialogue", "gpt-a", "low", "prompt"))
            self.assertIsNone(cache.read("cognition", "gpt-b", "low", "prompt"))
            self.assertIsNone(cache.read("cognition", "gpt-a", "medium", "prompt"))
            self.assertIsNone(cache.read("cognition", "gpt-a", "low", "other"))
            self.assertEqual(cache.stats.misses, 4)

    def test_read_only_mode_replays_existing_records_but_rejects_writes(self) -> None:
        with TemporaryDirectory() as directory:
            writer = LLMCallCache(directory)
            writer.write("reflection", "gpt-test", "low", "prompt", "cached")
            reader = LLMCallCache(directory, mode="read-only")

            self.assertEqual(reader.read("reflection", "gpt-test", "low", "prompt"), "cached")
            with self.assertRaises(ValueError):
                reader.write("reflection", "gpt-test", "low", "prompt", "new")

    def test_refresh_mode_ignores_existing_records_and_overwrites(self) -> None:
        with TemporaryDirectory() as directory:
            writer = LLMCallCache(directory)
            writer.write("cognition", "gpt-test", "low", "prompt", "old")
            refresher = LLMCallCache(directory, mode="refresh")

            self.assertIsNone(refresher.read("cognition", "gpt-test", "low", "prompt"))
            refreshed_path = refresher.write(
                "cognition",
                "gpt-test",
                "low",
                "prompt",
                "new",
            )

            self.assertEqual(Path(refreshed_path).read_text(encoding="utf-8").count("new"), 1)
            self.assertEqual(
                LLMCallCache(directory).read("cognition", "gpt-test", "low", "prompt"),
                "new",
            )


if __name__ == "__main__":
    unittest.main()
