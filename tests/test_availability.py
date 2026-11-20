import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import availability as av  # noqa: E402


def fail(since, last_ok=None):
    r = {"status": "FAIL (404)", "failures": 5, "failing_since": since}
    if last_ok:
        r["last_ok"] = last_ok
    return r


OK = {"status": "OK", "failures": 0, "last_ok": "2026-11-10"}
TODAY = "2026-11-19"


class AssessTest(unittest.TestCase):
    def assess(self, urls, state):
        return av.assess(urls, state, TODAY, 90, 365)

    def test_failing_long_enough_is_unavailable(self):
        r = self.assess({"a"}, {"a": fail("2026-06-01", "2026-05-20")})
        self.assertEqual(r, {"state": "unavailable", "since": "2026-06-01", "last_verified": "2026-05-20"})

    def test_failing_for_a_year_is_an_archive_candidate(self):
        self.assertEqual(self.assess({"a"}, {"a": fail("2025-10-01")})["state"], "archive")

    def test_recent_failure_is_not_flagged(self):
        self.assertIsNone(self.assess({"a"}, {"a": fail("2026-11-01")}))
        self.assertEqual(self.assess({"a"}, {"a": fail("2026-11-01", "2026-10-25")}),
                         {"last_verified": "2026-10-25"})

    def test_one_working_resource_is_enough(self):
        r = self.assess({"a", "b"}, {"a": fail("2025-01-01"), "b": OK})
        self.assertEqual(r, {"last_verified": "2026-11-10"})

    def test_unchecked_or_skipped_resources_prevent_the_flag(self):
        self.assertIsNone(self.assess({"a", "b"}, {"a": fail("2025-01-01")}))
        skipped = {"status": "SKIPPED (not http)", "failures": 0}
        self.assertIsNone(self.assess({"a", "b"}, {"a": fail("2025-01-01"), "b": skipped}))

    def test_since_is_when_the_last_resource_stopped_working(self):
        r = self.assess({"a", "b"}, {"a": fail("2025-12-01"), "b": fail("2026-06-01")})
        self.assertEqual(r["since"], "2026-06-01")

    def test_no_resources_says_nothing(self):
        self.assertIsNone(self.assess(set(), {}))


class MainTest(unittest.TestCase):
    def test_writes_flags_for_datasets_and_tolerates_a_missing_state_file(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "data").mkdir()
            (d / "data" / "x.json").write_text(json.dumps(
                {"identifier": "x", "title": "X", "full_download": [{"download_url": "http://a/x"}]}))
            (d / "data" / "y.json").write_text(json.dumps({"identifier": "y", "title": "Y"}))
            out = d / "out" / "availability.json"
            av.main(["--state", str(d / "none.json"), "--data", str(d / "data"), "--out", str(out)])
            self.assertEqual(json.loads(out.read_text()), {})
            (d / "state.json").write_text(json.dumps({"http://a/x": fail("2026-01-01")}))
            av.main(["--state", str(d / "state.json"), "--data", str(d / "data"), "--out", str(out),
                     "--today", TODAY, "--summary", str(d / "summary.md")])
            self.assertEqual(json.loads(out.read_text()), {"x": {"state": "unavailable", "since": "2026-01-01"}})
            self.assertIn("| X (`x`) | 2026-01-01 |", (d / "summary.md").read_text())
