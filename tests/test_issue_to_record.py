import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import issue_to_record as itr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "dataset.schema.json"


def form(**answers):
    """An issue body as GitHub writes it for a form."""
    labels = {v: k for k, v in itr.FIELDS.items() if k != "Identifier of the dataset to update"}
    out = []
    for key, label in labels.items():
        out.append("### %s\n\n%s\n" % (label, answers.get(key, "_No response_")))
    out.append("### Public data\n\n- [X] I understand\n")
    return "\n".join(out)


def add(**kw):
    base = dict(identifier="my-data", title="My Data", description="A dataset.\nOn two lines.",
                domain="Life Sciences", website="https://example.org/",
                contact_email="me@example.org")
    return form(**{**base, **kw})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.put({"identifier": "other", "title": "Other", "description": {"en": "x"}, "domain": "media",
                  "website": "https://o.example/", "contact_point": {"email": "o@o.example"}})

    def put(self, record):
        (self.data / (record["identifier"] + ".json")).write_text(json.dumps(record, indent=2) + "\n")

    def build(self, kind, body):
        return itr.build(kind, itr.parse_form(body), self.data, SCHEMA)


class ParseTest(unittest.TestCase):
    def test_blank_answers_are_left_out_and_unknown_headings_ignored(self):
        a = itr.parse_form(add(keywords="a, b"))
        self.assertEqual(a["identifier"], "my-data")
        self.assertEqual(a["keywords"], "a, b")
        self.assertNotIn("license", a)
        self.assertNotIn("Public data", a)
        self.assertEqual(a["description"], "A dataset.\nOn two lines.")

    def test_crlf_and_no_body(self):
        self.assertEqual(itr.parse_form("### Title\r\n\r\nX\r\n"), {"title": "X"})
        self.assertEqual(itr.parse_form(None), {})


class AddTest(Base):
    def test_a_minimal_dataset(self):
        path, record, errors = self.build("add", add())
        self.assertEqual(errors, [])
        self.assertEqual(path.name, "my-data.json")
        self.assertEqual(list(record), ["identifier", "title", "description", "domain", "website", "contact_point"])
        self.assertEqual(json.loads(path.read_text())["contact_point"], {"email": "me@example.org"})
        self.assertTrue(path.read_text().endswith("}\n"))

    def test_all_fields(self):
        body = add(contact_name="Me", license="https://creativecommons.org/licenses/by/4.0/", keywords="a, b, a ,",
                   namespace="https://example.org/ns/", triples="1,234", doi="10.1234/abc",
                   full_download="https://example.org/d.nt.gz | Dump\nhttps://example.org/e.nt.gz",
                   other_download="https://example.org/o", example="https://example.org/ex.ttl",
                   sparql="https://example.org/sparql", links="other | 1,200\n")
        path, record, errors = self.build("add", body)
        self.assertEqual(errors, [])
        self.assertEqual(record["keywords"], ["a", "b"])
        self.assertEqual(record["triples"], 1234)
        self.assertEqual(record["full_download"], [{"title": "Dump", "download_url": "https://example.org/d.nt.gz"},
                                                   {"download_url": "https://example.org/e.nt.gz"}])
        self.assertEqual(record["sparql"], [{"access_url": "https://example.org/sparql"}])
        self.assertEqual(record["links"], [{"target": "other", "value": 1200}])
        self.assertEqual(record["contact_point"], {"name": "Me", "email": "me@example.org"})

    def test_problems_are_listed_and_nothing_is_left_behind(self):
        body = add(website="not a url", triples="many", links="nowhere", domain="Moon")
        path, record, errors = self.build("add", body)
        self.assertIsNone(path)
        self.assertTrue(any("Domain" in e for e in errors) and any("triples" in e for e in errors), errors)
        path, record, errors = self.build("add", add(website="not a url", links="nowhere"))
        self.assertTrue(any("website" in e for e in errors) and any("nowhere" in e for e in errors), errors)
        self.assertEqual(sorted(p.name for p in self.data.iterdir()), ["other.json"])

    def test_identifier_in_use_ignoring_case_and_bad_identifiers(self):
        self.assertIn("already used", self.build("add", add(identifier="OTHER"))[2][0])
        self.assertIn("must not contain", self.build("add", add(identifier="a/b"))[2][0])
        self.assertIn("required", self.build("add", add(identifier=""))[2][0].lower())

    def test_required_fields(self):
        _, _, errors = self.build("add", add(title="", contact_email=""))
        self.assertEqual(errors, ["Title: required.", "Contact email: required."])

    def test_unusual_identifier_gets_the_encoded_file_name(self):
        path, _, errors = self.build("add", add(identifier="ISSN:1234"))
        self.assertEqual((errors, path.name), ([], "ISSN%3A1234.json"))


class UpdateTest(Base):
    def setUp(self):
        super().setUp()
        self.put({"identifier": "old", "title": "Old", "description": {"en": "d", "de": "d-de"}, "domain": "media",
                  "triples": 5, "website": "https://old.example/", "contact_point": {"name": "N", "email": "n@n.example"},
                  "keywords": ["x"], "sparql": [{"access_url": "https://old.example/sparql"}]})

    def test_only_filled_in_fields_change_and_key_order_is_kept(self):
        path, record, errors = self.build("update", form(identifier="old", title="New", contact_email="z@z.example",
                                                         license="https://l.example/"))
        self.assertEqual(errors, [])
        self.assertEqual(record["title"], "New")
        self.assertEqual(record["description"], {"en": "d", "de": "d-de"})
        self.assertEqual(record["contact_point"], {"name": "N", "email": "z@z.example"})
        self.assertEqual(list(record), ["identifier", "title", "description", "domain", "triples", "website",
                                        "contact_point", "keywords", "sparql", "license"])

    def test_lists_are_replaced_and_description_keeps_other_languages(self):
        _, record, errors = self.build("update", form(identifier="old", keywords="y, z", description="new en",
                                                      sparql="https://new.example/sparql"))
        self.assertEqual(errors, [])
        self.assertEqual((record["keywords"], record["sparql"]), (["y", "z"], [{"access_url": "https://new.example/sparql"}]))
        self.assertEqual(record["description"], {"en": "new en", "de": "d-de"})

    def test_unknown_dataset_nothing_to_change_and_bad_value_leave_the_file_alone(self):
        before = (self.data / "old.json").read_text()
        self.assertIn("no dataset", self.build("update", form(identifier="nope", title="x"))[2][0])
        self.assertIn("Nothing to change", self.build("update", form(identifier="old"))[2][0])
        self.assertIn("Nothing to change", self.build("update", form(identifier="old", title="Old"))[2][0])
        _, _, errors = self.build("update", form(identifier="old", website="nope"))
        self.assertTrue(errors)
        self.assertEqual((self.data / "old.json").read_text(), before)


class MainTest(Base):
    def run_main(self, labels, body, number=7, user=None):
        event = {"issue": {"number": number, "body": body, "labels": [{"name": l} for l in labels],
                           "user": user or {"login": "someone", "id": 42}}}
        ev, out = self.data.parent / "event.json", self.data.parent / "out.txt"
        ev.write_text(json.dumps(event))
        out.write_text("")
        report, message = self.data.parent / "report.md", self.data.parent / "message.txt"
        itr.main(["--event", str(ev), "--data", str(self.data), "--report", str(report), "--message", str(message),
                  "--github-output", str(out)])
        values = dict(l.split("=", 1) for l in out.read_text().splitlines())
        return values, report, message

    def test_success_outputs_and_commit_message(self):
        values, report, message = self.run_main(["add-dataset"], add())
        self.assertEqual((values["ok"], values["identifier"], values["kind"]), ("true", "my-data", "add"))
        self.assertTrue(values["file"].endswith("my-data.json"))
        text = message.read_text()
        self.assertTrue(text.startswith("Add dataset my-data (#7)"))
        self.assertIn("Co-authored-by: someone <42+someone@users.noreply.github.com>", text)

    def test_failure_writes_a_report(self):
        values, report, _ = self.run_main(["add-dataset"], add(website="x"))
        self.assertEqual(values["ok"], "false")
        self.assertIn("website", report.read_text())

    def test_other_issues_are_skipped_and_a_hostile_login_is_not_used(self):
        self.assertEqual(self.run_main(["bug"], add())[0]["ok"], "skip")
        self.assertEqual(self.run_main(["add-dataset", "update-dataset"], add())[0]["ok"], "skip")
        _, _, message = self.run_main(["add-dataset"], add(identifier="b"), user={"login": "x\nSigned-off-by: y", "id": 1})
        self.assertNotIn("Signed-off-by", message.read_text())


class TemplatesTest(unittest.TestCase):
    """The labels in the issue forms are what parse_form looks for."""

    def labels(self, name):
        doc = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / name).read_text())
        return doc, [b["attributes"]["label"] for b in doc["body"] if b["type"] != "markdown"]

    def test_labels_and_kinds_match(self):
        for name, kind in (("add-dataset.yml", "add-dataset"), ("update-dataset.yml", "update-dataset")):
            doc, labels = self.labels(name)
            self.assertEqual(doc["labels"], [kind])
            unknown = [l for l in labels if l not in itr.FIELDS and l != "Public data"]
            self.assertEqual(unknown, [], name)
            self.assertEqual(sorted(set(itr.FIELDS[l] for l in labels if l in itr.FIELDS)),
                             sorted(set(itr.FIELDS.values())), name)

    def test_domain_options_are_the_known_domains(self):
        doc, _ = self.labels("add-dataset.yml")
        domain = next(b for b in doc["body"] if b.get("id") == "domain")
        self.assertEqual(domain["attributes"]["options"], list(itr.DOMAINS))
