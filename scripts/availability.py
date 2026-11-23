#!/usr/bin/env python3
"""Work out which datasets are unavailable, from the link status.

    scripts/availability.py --state resources.json --out site/_data/availability.json

The state file is the one check_links.py keeps (data/README.md, "Link status").
A dataset is never removed for being unavailable; it is flagged instead, and the
site shows the flag (dataset page, domain page). Only datasets worth saying
something about are written, keyed by identifier:

    state          "unavailable"  every resource has been failing for --unavailable-days
                   "archive"      ... for --archive-days: a candidate for archiving
    since          date the resources stopped working
    last_verified  most recent date any of its resources was OK (if ever)

A dataset that is OK, or that has a resource that is not a web URL or has not been
checked yet, is not flagged. A dataset that has only just started failing is not
flagged either, so one blocked runner, or one bad week, does not mark it. For the
same reason a resource that has never worked counts from the first check, not from
the beginning of time: nothing is flagged until it has been monitored that long.

A missing state file is an empty state, so the site builds before the first check.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_links  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def dataset_urls(record):
    """The distinct resource URLs of one dataset record."""
    urls = set()
    for kind, (field, _) in check_links.RESOURCES.items():
        for resource in record.get(kind, []):
            url = (resource.get(field) or "").strip()
            if url:
                urls.add(url)
    return urls


def assess(urls, state, today, unavailable_days, archive_days):
    """{"state", "since", "last_verified"} for one dataset, or None to say nothing."""
    records = [state.get(u) for u in urls]
    if not records:
        return None
    last_ok = max((r["last_ok"] for r in records if r and r.get("last_ok")), default=None)
    verified = {"last_verified": last_ok} if last_ok else {}
    failing = [r for r in records if r and r["status"].startswith("FAIL") and r.get("failing_since")]
    if len(failing) < len(records):  # something works, is not a web URL, or has not been checked
        return verified or None
    since = max(r["failing_since"] for r in failing)
    days = (date.fromisoformat(today) - date.fromisoformat(since)).days
    if days >= archive_days:
        return {"state": "archive", "since": since, **verified}
    if days >= unavailable_days:
        return {"state": "unavailable", "since": since, **verified}
    return verified or None


def compute(records, state, today, unavailable_days=90, archive_days=365):
    result = {}
    for record in records:
        found = assess(dataset_urls(record), state, today, unavailable_days, archive_days)
        if found:
            result[record["identifier"]] = found
    return result


def summary(records, result):
    flagged = sorted((v["since"], r["identifier"], r["title"]) for r in records
                     for v in [result.get(r["identifier"], {})] if v.get("state"))
    archive = {i for i, v in result.items() if v.get("state") == "archive"}
    lines = ["## Unavailable datasets", "",
             f"{len(flagged)} of {len(records)} datasets are flagged as unavailable, "
             f"{len(archive)} of them long enough to be archive candidates.", ""]
    if flagged:
        lines += ["| Dataset | Unavailable since | |", "|---|---|---|"]
        for since, identifier, title in flagged:
            lines.append(f"| {title} (`{identifier}`) | {since} | {'archive candidate' if identifier in archive else ''} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--state", required=True, help="resources.json from check_links.py (may be missing)")
    parser.add_argument("--data", default=str(ROOT / "data" / "datasets"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--unavailable-days", type=int, default=90)
    parser.add_argument("--archive-days", type=int, default=365)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--summary", help="append a markdown summary to this file")
    args = parser.parse_args(argv)

    state_file = Path(args.state)
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(args.data).glob("*.json"))]
    result = compute(records, state, args.today, args.unavailable_days, args.archive_days)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    flagged = sum(1 for v in result.values() if v.get("state"))
    print(f"{len(result)} of {len(records)} datasets have link status; {flagged} flagged as unavailable"
          + ("" if state_file.exists() else " (no state file yet)"))
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(summary(records, result))


if __name__ == "__main__":
    main()
