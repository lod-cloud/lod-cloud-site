#!/usr/bin/env python3
"""Turn an "Add a dataset" / "Update a dataset" issue into a dataset file.

    scripts/issue_to_record.py --event "$GITHUB_EVENT_PATH" --report report.md \
        --message commit-message.txt [--github-output "$GITHUB_OUTPUT"]

Run by .github/workflows/submissions.yml when such an issue is opened or edited.
The issue body is data, never code: it is only split into fields and written out
as JSON. The record is written to data/datasets, and checked like a pull request
would be (schema, unique identifiers, link targets, strictly: no known-issues
allowance). The result is in the outputs:

    ok=true   the file was written; `file` and `identifier` name it, --message has
              the commit message
    ok=false  nothing was written; --report is a comment for the issue listing
              what to fix (editing the issue runs this again)

The fields are the labels of .github/ISSUE_TEMPLATE/*.yml (tests/test_issue_to_record.py
checks that they agree). In an update, a blank field means "unchanged", a filled-in
list replaces the old list.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domains  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Label in the issue form -> key. The issue body has "### <label>" before each answer.
FIELDS = {
    "Identifier": "identifier",
    "Identifier of the dataset to update": "identifier",
    "Title": "title",
    "Description (English)": "description",
    "Domain": "domain",
    "Website": "website",
    "Contact name": "contact_name",
    "Contact email": "contact_email",
    "License": "license",
    "Keywords": "keywords",
    "Namespace": "namespace",
    "Number of triples": "triples",
    "DOI": "doi",
    "Full downloads": "full_download",
    "Other downloads": "other_download",
    "Examples": "example",
    "SPARQL endpoints": "sparql",
    "Links to other datasets": "links",
}
# Label in the form -> key (scripts/domains.py)
DOMAINS = {label: key for key, label in domains.DOMAINS.items()}
# Key order of a new file (schema/README.md)
ORDER = ["identifier", "title", "description", "domain", "website", "contact_point", "license", "triples",
         "namespace", "doi", "image", "keywords", "links", "full_download", "other_download", "example", "sparql"]
RESOURCE_URL = {"full_download": "download_url", "other_download": "access_url",
                "example": "access_url", "sparql": "access_url"}
REQUIRED_FOR_ADD = {"title": "Title", "description": "Description (English)", "domain": "Domain",
                    "website": "Website", "contact_email": "Contact email"}
KINDS = {"add-dataset": "add", "update-dataset": "update"}


def parse_form(body):
    """{key: text} for the answers in a form-generated issue body; blank answers are left out."""
    answers, label, lines = {}, None, []

    def close():
        if label in FIELDS:
            text = "\n".join(lines).strip()
            if text and text != "_No response_":
                answers[FIELDS[label]] = text

    for line in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^### (.+?)\s*$", line)
        if m:
            close()
            label, lines = m.group(1), []
        else:
            lines.append(line)
    close()
    return answers


def split_lines(text):
    return [l.strip() for l in text.split("\n") if l.strip()]


def resources(text, url_field):
    out = []
    for line in split_lines(text):
        url, _, title = line.partition(" | ")
        item = {"title": title.strip()} if title.strip() else {}
        item[url_field] = url.strip()
        out.append(item)
    return out


def links(text, errors):
    out = []
    for line in split_lines(text):
        target, _, value = line.partition(" | ")
        item = {"target": target.strip()}
        if value.strip():
            number = value.strip().replace(",", "")
            if not number.isdigit() or int(number) < 1:
                errors.append("Links to other datasets: '%s' is not a whole number of links." % value.strip())
                continue
            item["value"] = int(number)
        out.append(item)
    return sorted(out, key=lambda l: l["target"])


def apply_answers(record, answers, errors):
    """Put the filled-in answers into the record (a dict, new or existing)."""
    for key in ("title", "website", "license", "namespace", "doi"):
        if key in answers:
            record[key] = answers[key]
    if "description" in answers:
        record["description"] = dict(record.get("description") or {}, en=answers["description"])
    if "domain" in answers:
        domain = DOMAINS.get(answers["domain"])
        if domain is None:
            errors.append("Domain: '%s' is not one of the domains." % answers["domain"])
        else:
            record["domain"] = domain
    if "contact_name" in answers or "contact_email" in answers:
        contact = dict(record.get("contact_point") or {})
        if "contact_name" in answers:
            contact["name"] = answers["contact_name"]
        if "contact_email" in answers:
            contact["email"] = answers["contact_email"]
        record["contact_point"] = {k: contact[k] for k in ("name", "email") if k in contact}
    if "triples" in answers:
        number = answers["triples"].replace(",", "").replace(" ", "")
        if number.isdigit():
            record["triples"] = int(number)
        else:
            errors.append("Number of triples: '%s' is not a whole number." % answers["triples"])
    if "keywords" in answers:
        keywords = []
        for k in answers["keywords"].split(","):
            if k.strip() and k.strip() not in keywords:
                keywords.append(k.strip())
        record["keywords"] = keywords
    if "links" in answers:
        record["links"] = links(answers["links"], errors)
    for key, field in RESOURCE_URL.items():
        if key in answers:
            record[key] = resources(answers[key], field)
    return record


def ordered(record):
    """Keys of the schema's order; any other key (from an old file) last."""
    rest = [k for k in record if k not in ORDER]
    return {k: record[k] for k in ORDER + rest if k in record}


def with_new_keys_last(existing, record):
    """Keep an existing file's key order so an update changes only what it changes."""
    first = {k: record[k] for k in existing if k in record}
    return first | {k: v for k, v in ordered(record).items() if k not in first}


def build(kind, answers, data_dir, schema):
    """Write the record into data_dir. Returns (path, record, errors); path is None on errors."""
    errors = []
    ident = answers.get("identifier", "")
    if not ident:
        return None, None, ["Identifier: required."]
    if not re.fullmatch(r"[^\s/\\?]+", ident) or ident in (".", ".."):
        return None, None, ["Identifier: must not contain spaces, '/', '\\' or '?'."]
    path = Path(data_dir) / validate.filename(ident)
    if kind == "add":
        if any(p.name.lower() == path.name.lower() for p in Path(data_dir).glob("*.json")):
            return None, None, ["Identifier: `%s` is already used (identifiers are compared ignoring case). "
                                "To change that dataset use the *Update a dataset* form." % ident]
        for key, label in REQUIRED_FOR_ADD.items():
            if key not in answers:
                errors.append("%s: required." % label)
        record = apply_answers({"identifier": ident}, answers, errors)
        record = ordered(record)
        original = None
    else:
        if not path.exists():
            return None, None, ["Identifier: there is no dataset `%s`. Check the spelling against the address of its page." % ident]
        original = path.read_text(encoding="utf-8")
        existing = json.loads(original)
        record = with_new_keys_last(existing, apply_answers(dict(existing), answers, errors))
        if record == existing:
            return None, None, ["Nothing to change: every field except the identifier is blank or the same as now."]
    if errors:
        return None, None, errors

    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    problems = validate.find_problems(data_dir, schema).get(path.name, [])
    if problems:
        if original is None:
            path.unlink()
        else:
            path.write_text(original, encoding="utf-8")
        return None, None, [readable(p) for p in problems]
    return path, record, []


def readable(problem):
    code, detail, message = problem
    if code == "schema":
        return "%s: %s" % (detail.split(":")[0], message)
    return message


def report_for(errors, kind):
    lines = ["Thanks for the submission. It could not be turned into a pull request yet:", ""]
    lines += ["- " + e for e in errors]
    lines += ["", "Please edit the issue to fix this; the check runs again when you save."]
    if kind == "update":
        lines += ["", "The checks cover the whole record, so a problem that was already there has to be fixed in the same "
                      "submission (for example by filling in a missing website, or by giving a corrected list of links). "
                      "If you are not sure how, say so in a comment and a maintainer will help."]
    return "\n".join(lines) + "\n"


def message_for(kind, record, number, issue):
    user = issue.get("user") or {}
    login = user.get("login", "")
    lines = ["%s dataset %s (#%s)" % ("Add" if kind == "add" else "Update", record["identifier"], number), ""]
    lines.append("Submitted in issue #%s." % number)
    if re.fullmatch(r"[A-Za-z0-9-]+(\[bot\])?", login) and isinstance(user.get("id"), int):
        lines += ["", "Co-authored-by: %s <%d+%s@users.noreply.github.com>" % (login, user["id"], login)]
    return "\n".join(lines) + "\n"


def output(path, **values):
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in values.items():
                f.write("%s=%s\n" % (k, str(v).replace("\n", " ")))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--event", required=True, help="the event JSON (GITHUB_EVENT_PATH)")
    ap.add_argument("--data", default=str(ROOT / "data" / "datasets"))
    ap.add_argument("--schema", default=str(ROOT / "schema" / "dataset.schema.json"))
    ap.add_argument("--report", required=True, help="where to write the comment for the issue, on a problem")
    ap.add_argument("--message", required=True, help="where to write the commit message, on success")
    ap.add_argument("--github-output")
    args = ap.parse_args(argv)

    issue = json.loads(Path(args.event).read_text(encoding="utf-8"))["issue"]
    labels = {l["name"] for l in issue.get("labels", [])}
    kinds = [KINDS[l] for l in labels if l in KINDS]
    if len(kinds) != 1:
        print("Not a submission issue (labels: %s)" % ", ".join(sorted(labels)), file=sys.stderr)
        output(args.github_output, ok="skip")
        return 0
    kind = kinds[0]
    path, record, errors = build(kind, parse_form(issue.get("body")), args.data, args.schema)
    if errors:
        Path(args.report).write_text(report_for(errors, kind), encoding="utf-8")
        print("\n".join(errors), file=sys.stderr)
        output(args.github_output, ok="false")
        return 0
    Path(args.message).write_text(message_for(kind, record, issue["number"], issue), encoding="utf-8")
    print("Wrote %s" % path, file=sys.stderr)
    output(args.github_output, ok="true", kind=kind, identifier=record["identifier"],
           file=os.path.relpath(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
