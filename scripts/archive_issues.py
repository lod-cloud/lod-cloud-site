#!/usr/bin/env python3
"""Open an issue for each dataset that has become an archive candidate.

    scripts/archive_issues.py --state resources.json --repo lod-cloud/lod-cloud-site [--create]

A dataset is an archive candidate when all its links have been failing for a year
(scripts/availability.py, data/README.md "Unavailable datasets"). Whether to remove
it is a decision for a person, so each one gets an issue, titled
"Archive candidate: <identifier>" and labelled `archive-candidate`, where that is
decided and recorded.

- Without --create nothing is changed; the issues that would be opened are listed.
- At most --max-new are opened per run, so a year of datasets that all became
  candidates in the same week are worked through over several weeks.
- An issue is never opened twice: all issues with the label are looked at, closed
  ones included, so closing one ("keep it") is final. The title is what is matched.
- Titles and URLs come from pull requests, so they go in code spans (no mentions or
  autolinks), and contact details are never included: the repository is public.

Needs GITHUB_TOKEN with `issues: write` when creating.
"""
import argparse
import json
import os
import sys
import urllib.parse
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import availability  # noqa: E402
from validate import filename  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LABEL = "archive-candidate"
TITLE_PREFIX = "Archive candidate: "
SITE = "https://lod-cloud.net"


def code(text):
    """Inline code span (also stops @mentions and autolinks); backticks are replaced."""
    return "`" + " ".join(str(text).split()).replace("`", "'") + "`"


def title_for(record):
    return TITLE_PREFIX + record["identifier"]


def body_for(record, info, state, repo, branch="main"):
    identifier = record["identifier"]
    page = f"{SITE}/dataset/{urllib.parse.quote(identifier, safe='')}/"
    source = f"https://github.com/{repo}/blob/{branch}/data/datasets/{urllib.parse.quote(filename(identifier))}"
    edit = source.replace("/blob/", "/edit/")
    lines = [
        f"{code(record['title'])} ({code(identifier)}) has had no working download, SPARQL or example link "
        f"since **{info['since']}**" + (f"; one last responded on {info['last_verified']}." if info.get("last_verified") else "."),
        "",
        "It is still shown in the cloud, flagged as unavailable. This issue is to decide whether to archive it.",
        "",
        f"- Dataset page: {page}",
        f"- Record: {source}",
        "",
        "**Failing URLs**",
        "",
    ]
    for url in sorted(availability.dataset_urls(record)):
        s = state.get(url, {})
        shown = s.get("status", "not checked") + (f", last checked {s['last_checked']}" if s.get("last_checked") else "")
        lines.append(f"- {code(urllib.parse.quote(url, safe=':/?#[]@!$&()*+,;=%~'))}: {shown}")
    lines += [
        "",
        "**What to do**",
        "",
        f"- If the dataset has moved, [update the record]({edit}) with the new URLs. The flag clears when a URL responds.",
        "- If it is gone, remove the record in a pull request (the history keeps it) that says `Closes #<this issue>`.",
        "- If it should stay as it is, close this issue. It will not be opened again.",
        "",
        "_Opened by the Links workflow._",
    ]
    return "\n".join(lines) + "\n"


def candidates(records, state, today, unavailable_days=90, archive_days=365):
    found = availability.compute(records, state, today, unavailable_days, archive_days)
    by_id = {r["identifier"]: r for r in records}
    return [(by_id[i], v) for i, v in sorted(found.items(), key=lambda kv: (kv[1].get("since", ""), kv[0]))
            if v.get("state") == "archive"]


def plan(records, state, existing_titles, today, max_new, archive_days=365):
    """The (record, info) pairs to open issues for, oldest first, at most max_new."""
    todo = [(r, v) for r, v in candidates(records, state, today, archive_days=archive_days)
            if title_for(r) not in existing_titles]
    return todo[:max_new], max(0, len(todo) - max_new)


class GitHub:
    def __init__(self, repo, token):
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})

    def url(self, path):
        return f"https://api.github.com/repos/{self.repo}/{path}"

    def issue_titles(self):
        """Titles of every issue (open or closed, not pull requests) with the label."""
        titles, page = set(), 1
        while True:
            r = self.session.get(self.url("issues"), timeout=30,
                                 params={"labels": LABEL, "state": "all", "per_page": 100, "page": page})
            r.raise_for_status()
            batch = r.json()
            titles |= {i["title"] for i in batch if "pull_request" not in i}
            if len(batch) < 100:
                return titles
            page += 1

    def ensure_label(self):
        r = self.session.post(self.url("labels"), timeout=30, json={
            "name": LABEL, "color": "fbca04",
            "description": "A dataset whose links have been failing for a year"})
        if r.status_code not in (201, 422):  # 422: it exists
            r.raise_for_status()

    def create_issue(self, title, body):
        r = self.session.post(self.url("issues"), timeout=30, json={"title": title, "body": body, "labels": [LABEL]})
        r.raise_for_status()
        return r.json()["html_url"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--state", required=True)
    parser.add_argument("--data", default=str(ROOT / "data" / "datasets"))
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--branch", default="main", help="branch the record links point to")
    parser.add_argument("--max-new", type=int, default=10)
    parser.add_argument("--archive-days", type=int, default=365)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--create", action="store_true", help="open the issues (default: only list them)")
    args = parser.parse_args(argv)

    state_file = Path(args.state)
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(args.data).glob("*.json"))]
    if not candidates(records, state, args.today, archive_days=args.archive_days):
        print("No archive candidates.")
        return 0

    token = os.environ.get("GITHUB_TOKEN", "")
    if args.create and not token:
        sys.exit("GITHUB_TOKEN is not set")
    gh = GitHub(args.repo, token)
    existing = gh.issue_titles() if token else set()
    todo, left = plan(records, state, existing, args.today, args.max_new, args.archive_days)
    print(f"{len(todo)} issue(s) to open, {left} more waiting for later runs; {len(existing)} already exist.")
    if args.create and todo:
        gh.ensure_label()
    for record, info in todo:
        title = title_for(record)
        if args.create:
            print(f"Opened {gh.create_issue(title, body_for(record, info, state, args.repo, args.branch))}")
        else:
            print(f"Would open: {title} (unavailable since {info['since']})")
    return 0


if __name__ == "__main__":
    main()
