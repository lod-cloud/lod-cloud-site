#!/usr/bin/env python3
"""Validate the dataset files in data/datasets.

    scripts/validate.py [--changed-from REF] [--strict FILE ...]
    scripts/validate.py --write-known-issues

Checks, per file: valid JSON, conforms to schema/dataset.schema.json, file name
matches the identifier. Across files: identifiers unique ignoring case, link
targets exist, no duplicate or self links.

Problems that already existed when the data was migrated are listed in
data/known-issues.json and do not fail the run, so they do not block unrelated
pull requests. Files named by --strict (or changed since --changed-from) get no
such allowance: every problem in them is an error. Exit status is 1 if there
are errors.
"""
import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "datasets"
DEFAULT_SCHEMA = ROOT / "schema" / "dataset.schema.json"
DEFAULT_KNOWN = ROOT / "data" / "known-issues.json"


def filename(identifier):
    """File name for an identifier; the rule is documented in schema/README.md."""
    out = []
    last = len(identifier) - 1
    for i, ch in enumerate(identifier):
        if re.fullmatch(r"[A-Za-z0-9_-]", ch) or (ch == "." and 0 < i < last):
            out.append(ch)
        else:
            out.append("".join("%%%02X" % b for b in ch.encode("utf-8")))
    return "".join(out) + ".json"


def schema_findings(validator, record):
    seen = {}
    for e in validator.iter_errors(record):
        where = ".".join(str(p) for p in e.absolute_path if not isinstance(p, int)) or "(record)"
        detail = "%s: %s" % (where, e.validator)
        if e.validator == "required":
            detail += ": " + ", ".join(
                p for p in e.validator_value if p not in e.instance)
        seen.setdefault(detail, e.message[:200])
    return [("schema", d, m) for d, m in seen.items()]


def find_problems(data_dir, schema_path):
    """Return {file name: [(code, detail, message)]} for every problem."""
    validator = Draft202012Validator(json.loads(Path(schema_path).read_text(encoding="utf-8")))
    problems = collections.defaultdict(list)
    records = {}
    for path in sorted(Path(data_dir).iterdir()):
        if path.name.startswith("."):
            continue
        if path.suffix != ".json" or not path.is_file():
            problems[path.name].append(("stray-file", "", "not a .json dataset file"))
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            problems[path.name].append(("json", "", "invalid JSON: %s" % e))
            continue
        problems[path.name].extend(schema_findings(validator, record))
        ident = record.get("identifier") if isinstance(record, dict) else None
        if isinstance(ident, str):
            if filename(ident) != path.name:
                problems[path.name].append(
                    ("filename", filename(ident), "file name does not match identifier, expected %s" % filename(ident)))
            records[path.name] = record

    by_lower = collections.defaultdict(list)
    for name, rec in records.items():
        if isinstance(rec.get("identifier"), str):
            by_lower[rec["identifier"].lower()].append(name)
    for lower, names in by_lower.items():
        if len(names) > 1:
            for name in names:
                problems[name].append(("duplicate-identifier", lower,
                                       "identifier is the same as %s ignoring case" % ", ".join(n for n in names if n != name)))

    known_ids = {rec["identifier"] for rec in records.values() if isinstance(rec.get("identifier"), str)}
    for name, rec in records.items():
        links = rec.get("links")
        if not isinstance(links, list):
            continue
        targets = collections.Counter(l.get("target") for l in links if isinstance(l, dict))
        for target, n in targets.items():
            if not isinstance(target, str):
                continue
            if target not in known_ids:
                problems[name].append(("link-target-missing", target, "link to unknown dataset '%s'" % target))
            if target == rec.get("identifier"):
                problems[name].append(("link-self", target, "dataset links to itself"))
            if n > 1:
                problems[name].append(("link-duplicate-target", target, "more than one link to '%s'" % target))
    return {k: v for k, v in problems.items() if v}


def key(code, detail):
    return "%s: %s" % (code, detail) if detail else code


def load_known(path):
    p = Path(path)
    if not p.exists():
        return {}
    return {name: set(keys) for name, keys in json.loads(p.read_text(encoding="utf-8")).items()}


def write_known(path, problems):
    known = {name: sorted({key(c, d) for c, d, _ in found}) for name, found in sorted(problems.items())}
    Path(path).write_text(json.dumps(known, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def changed_files(ref, data_dir):
    rel = Path(data_dir).resolve().relative_to(ROOT)
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", ref + "...HEAD", "--", str(rel)],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return {Path(line).name for line in out.splitlines() if line}


def evaluate(problems, known, strict):
    """Split problems into (errors, allowed, stale known-issue count)."""
    errors, allowed = [], 0
    found_keys = collections.defaultdict(set)
    for name, found in problems.items():
        for code, detail, message in found:
            k = key(code, detail)
            found_keys[name].add(k)
            if name not in strict and k in known.get(name, ()):
                allowed += 1
            else:
                errors.append((name, code, detail, message))
    stale = sum(len(keys - found_keys.get(name, set())) for name, keys in known.items())
    return errors, allowed, stale


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="directory of dataset files")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--known-issues", default=str(DEFAULT_KNOWN))
    ap.add_argument("--changed-from", metavar="REF", help="treat files changed since REF (git diff REF...HEAD) as strict")
    ap.add_argument("--strict", nargs="*", default=[], metavar="FILE", help="file names that get no known-issues allowance")
    ap.add_argument("--no-known-issues", action="store_true", help="ignore the known-issues list")
    ap.add_argument("--write-known-issues", action="store_true", help="record all current problems as known and exit")
    ap.add_argument("--format", choices=("text", "github"), default="text")
    args = ap.parse_args(argv)

    problems = find_problems(args.data, args.schema)
    if args.write_known_issues:
        write_known(args.known_issues, problems)
        print("Wrote %d files with %d known problems to %s" % (
            len(problems), sum(len(v) for v in problems.values()), args.known_issues))
        return 0

    strict = {Path(f).name for f in args.strict}
    if args.changed_from:
        strict |= changed_files(args.changed_from, args.data)
    known = {} if args.no_known_issues else load_known(args.known_issues)
    errors, allowed, stale = evaluate(problems, known, strict)

    for name, code, _detail, message in errors:
        if args.format == "github":
            path = Path(args.data).resolve().relative_to(ROOT) / name
            print("::error file=%s::%s: %s" % (path, code, message))
        else:
            print("%s: %s: %s" % (name, code, message))
    print("%d error(s), %d known problem(s) allowed, %d strict file(s)%s" % (
        len(errors), allowed, len(strict),
        "" if not stale else ", %d known issue(s) no longer occur (run --write-known-issues to prune)" % stale),
        file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
