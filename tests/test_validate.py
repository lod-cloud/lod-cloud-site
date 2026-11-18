import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = json.loads((ROOT / "schema" / "examples" / "valid.json").read_text(encoding="utf-8"))


def record(identifier, **changes):
    r = copy.deepcopy(EXAMPLE)
    r["identifier"] = identifier
    r.pop("links", None)
    r.update(changes)
    return r


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def put(self, rec, name=None):
        name = name or validate.filename(rec["identifier"])
        (self.dir / name).write_text(json.dumps(rec), encoding="utf-8")
        return name

    def run_validate(self, *extra):
        argv = ["--data", str(self.dir), "--known-issues", str(self.dir / ".known.json"), *extra]
        return validate.main(argv)

    def codes(self):
        found = validate.find_problems(self.dir, validate.DEFAULT_SCHEMA)
        return {(n, c, d) for n, v in found.items() for c, d, _ in v}

    def test_example_and_clean_data_pass(self):
        self.put(record("a"))
        self.put(record("b", links=[{"target": "a", "value": 3}]))
        self.assertEqual(self.codes(), set())
        self.assertEqual(self.run_validate(), 0)

    def test_schema_violation(self):
        r = record("a")
        del r["domain"]
        self.put(r)
        self.assertEqual(self.codes(), {("a.json", "schema", "(record): required: domain")})
        self.assertEqual(self.run_validate(), 1)

    def test_filename_must_match_identifier(self):
        self.put(record("a"), name="other.json")
        self.assertIn(("other.json", "filename", "a.json"), self.codes())

    def test_invalid_json_and_stray_file(self):
        (self.dir / "x.json").write_text("{", encoding="utf-8")
        (self.dir / "notes.txt").write_text("hi", encoding="utf-8")
        self.assertEqual({c for _, c, _ in self.codes()}, {"json", "stray-file"})

    def test_identifiers_unique_ignoring_case(self):
        self.put(record("Foo"))
        self.put(record("foo"))
        self.assertEqual({c for _, c, _ in self.codes()}, {"duplicate-identifier"})
        self.assertEqual(len(self.codes()), 2)

    def test_links(self):
        self.put(record("a", links=[{"target": "a"}, {"target": "missing"}, {"target": "b"}, {"target": "b"}]))
        self.put(record("b"))
        self.assertEqual(self.codes(), {
            ("a.json", "link-self", "a"),
            ("a.json", "link-target-missing", "missing"),
            ("a.json", "link-duplicate-target", "b")})

    def test_known_issues_allow_old_problems_but_not_new_ones(self):
        r = record("a")
        del r["domain"]
        self.put(r)
        self.assertEqual(self.run_validate("--write-known-issues"), 0)
        self.assertEqual(self.run_validate(), 0)
        self.put(record("b", links=[{"target": "nope"}]))
        self.assertEqual(self.run_validate(), 1)

    def test_strict_files_get_no_allowance(self):
        r = record("a")
        del r["domain"]
        self.put(r)
        self.run_validate("--write-known-issues")
        self.assertEqual(self.run_validate("--strict", "a.json"), 1)
        self.assertEqual(self.run_validate("--no-known-issues"), 1)

    def test_deleting_a_dataset_breaks_links_to_it(self):
        self.put(record("a"))
        self.put(record("b", links=[{"target": "a"}]))
        self.run_validate("--write-known-issues")
        (self.dir / "a.json").unlink()
        self.assertEqual(self.run_validate(), 1)

    def test_filename_rule(self):
        self.assertEqual(validate.filename("plain-id_1.2"), "plain-id_1.2.json")
        self.assertEqual(validate.filename("Qualité_de_l'air"), "Qualit%C3%A9_de_l%27air.json")
        self.assertEqual(validate.filename("ISSN:_0080-3626."), "ISSN%3A_0080-3626%2E.json")
        self.assertEqual(validate.filename(".hidden"), "%2Ehidden.json")
        self.assertEqual(validate.filename("100%"), "100%25.json")


if __name__ == "__main__":
    unittest.main()
