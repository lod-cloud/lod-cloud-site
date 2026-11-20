import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import archive_issues as ai  # noqa: E402

TODAY = "2026-11-19"


def record(identifier, url="http://a.example/x", title=None):
    return {"identifier": identifier, "title": title or identifier.upper(),
            "full_download": [{"download_url": url}],
            "contact_point": {"email": "private@example.org"}}


def failing(since):
    return {"status": "FAIL (404)", "http": 404, "failures": 9, "failing_since": since, "last_checked": "2026-11-16"}


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.records = [record("old", "http://a/1"), record("older", "http://a/2"),
                        record("recent", "http://a/3"), record("fine", "http://a/4")]
        self.state = {"http://a/1": failing("2025-06-01"), "http://a/2": failing("2024-01-01"),
                      "http://a/3": failing("2026-06-01"), "http://a/4": {"status": "OK", "last_ok": "2026-11-10"}}

    def test_only_year_old_failures_oldest_first(self):
        todo, left = ai.plan(self.records, self.state, set(), TODAY, 10)
        self.assertEqual([r["identifier"] for r, _ in todo], ["older", "old"])
        self.assertEqual(left, 0)

    def test_cap_and_existing_issues(self):
        todo, left = ai.plan(self.records, self.state, set(), TODAY, 1)
        self.assertEqual(([r["identifier"] for r, _ in todo], left), (["older"], 1))
        todo, left = ai.plan(self.records, self.state, {"Archive candidate: older"}, TODAY, 10)
        self.assertEqual([r["identifier"] for r, _ in todo], ["old"])


class BodyTest(unittest.TestCase):
    def test_body_has_no_contact_details_and_neutralises_markup(self):
        r = record("a@b", "http://a/x`y", title="Evil @everyone `x`")
        state = {"http://a/x`y": failing("2025-01-01")}
        body = ai.body_for(r, {"since": "2025-01-01", "last_verified": "2024-12-01"}, state, "o/r")
        self.assertNotIn("private@example.org", body)
        self.assertIn("`Evil @everyone 'x'`", body)
        self.assertIn("since **2025-01-01**; one last responded on 2024-12-01", body)
        self.assertIn("FAIL (404), last checked 2026-11-16", body)
        self.assertIn("https://github.com/o/r/blob/main/data/datasets/a%2540b.json", body)
        self.assertNotIn("x`y", body)


class MainTest(unittest.TestCase):
    def run_main(self, args, existing=()):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "data").mkdir()
            (d / "data" / "old.json").write_text(json.dumps(record("old")))
            (d / "state.json").write_text(json.dumps({"http://a.example/x": failing("2025-01-01")}))
            with mock.patch.object(ai.GitHub, "issue_titles", return_value=set(existing)), \
                    mock.patch.object(ai.GitHub, "ensure_label") as label, \
                    mock.patch.object(ai.GitHub, "create_issue", return_value="http://issue/1") as create:
                ai.main(["--state", str(d / "state.json"), "--data", str(d / "data"), "--repo", "o/r",
                         "--today", TODAY] + args)
            return label, create

    def test_lists_without_creating_by_default(self):
        with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "t"}):
            label, create = self.run_main([])
        create.assert_not_called()

    def test_creates_when_asked_and_not_twice(self):
        with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "t"}):
            label, create = self.run_main(["--create"])
            self.assertEqual(create.call_count, 1)
            self.assertEqual(create.call_args[0][0], "Archive candidate: old")
            label, create = self.run_main(["--create"], existing=["Archive candidate: old"])
            create.assert_not_called()
