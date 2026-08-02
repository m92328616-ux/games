"""
Tests for the desktop in-game death log (issue #32).

Covers the log helpers added to xpilot.NetworkClient:

* add_log inserts newest-first with a lifetime and caps the buffer.
* tick_log ages entries and removes expired ones.
* The buffer is bounded (LOG_MAX_ENTRIES) and thread-safe.
* _short_id formats/truncates connection ids for display.

Run with:  python -m unittest discover -s tests -p '*.py' -v
"""

import threading
import unittest

import xpilot


def make_client():
    """Build a NetworkClient pointed at a dead UDP port (no server needed)."""
    return xpilot.NetworkClient(
        "127.0.0.1", 9,
        player_ref=xpilot.Player(100, 100),
        bullets_ref=[],
        others_ref={},
        enemies_ref=[],
    )


class ShortIdTest(unittest.TestCase):

    def test_formats_common_cases(self):
        self.assertEqual(xpilot._short_id("abc12345"), "abc12345")
        self.assertEqual(xpilot._short_id(None), "?")
        self.assertEqual(xpilot._short_id(""), "?")

    def test_truncates_long_ids(self):
        self.assertEqual(xpilot._short_id("0123456789abcdef"), "01234567")
        self.assertEqual(len(xpilot._short_id("x" * 100)), 8)


class LogAddTest(unittest.TestCase):

    def setUp(self):
        self.client = make_client()

    def tearDown(self):
        self.client.close()

    def test_add_log_inserts_newest_first(self):
        self.client.add_log("first", xpilot.LOG_COLOR_JOIN)
        self.client.add_log("second", xpilot.LOG_COLOR_DEATH)
        entries = list(self.client.game_log)
        self.assertEqual(entries[0]["text"], "second")
        self.assertEqual(entries[1]["text"], "first")

    def test_add_log_stores_color_and_lifetime(self):
        self.client.add_log("hello", xpilot.LOG_COLOR_SELF)
        entry = self.client.game_log[0]
        self.assertEqual(entry["text"], "hello")
        self.assertEqual(entry["color"], xpilot.LOG_COLOR_SELF)
        self.assertEqual(entry["t"], xpilot.LOG_LIFETIME)

    def test_log_buffer_is_bounded(self):
        for i in range(xpilot.LOG_MAX_ENTRIES + 25):
            self.client.add_log(f"msg-{i}", xpilot.LOG_COLOR_JOIN)
        self.assertLessEqual(len(self.client.game_log), xpilot.LOG_MAX_ENTRIES)
        # Newest entries are kept.
        self.assertEqual(self.client.game_log[0]["text"], f"msg-{xpilot.LOG_MAX_ENTRIES + 24}")


class LogTickTest(unittest.TestCase):

    def setUp(self):
        self.client = make_client()

    def tearDown(self):
        self.client.close()

    def test_tick_log_removes_expired_entries(self):
        self.client.add_log("old", xpilot.LOG_COLOR_JOIN)
        self.client.add_log("new", xpilot.LOG_COLOR_DEATH)
        # Age everything past the lifetime.
        self.client.tick_log(xpilot.LOG_LIFETIME + 1)
        self.assertEqual(len(self.client.game_log), 0)

    def test_tick_log_keeps_fresh_entries(self):
        self.client.add_log("fresh", xpilot.LOG_COLOR_JOIN)
        self.client.tick_log(0.5)
        self.assertEqual(len(self.client.game_log), 1)
        self.assertEqual(self.client.game_log[0]["text"], "fresh")

    def test_tick_log_removes_only_expired(self):
        self.client.add_log("a", xpilot.LOG_COLOR_JOIN)
        self.client.game_log[0]["t"] = 0.2
        self.client.add_log("b", xpilot.LOG_COLOR_DEATH)
        self.client.tick_log(1.0)
        texts = [e["text"] for e in self.client.game_log]
        self.assertEqual(texts, ["b"])


class LogThreadSafetyTest(unittest.TestCase):

    def setUp(self):
        self.client = make_client()

    def tearDown(self):
        self.client.close()

    def test_concurrent_add_log_is_safe(self):
        errors = []

        def worker(n):
            try:
                for i in range(100):
                    self.client.add_log(f"t{n}-{i}", xpilot.LOG_COLOR_JOIN)
            except Exception as e:  # pragma: no cover - only on failure
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(self.client.game_log), xpilot.LOG_MAX_ENTRIES)


if __name__ == "__main__":
    unittest.main()
