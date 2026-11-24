#!/usr/bin/env python3
"""Check a built site has every per-dataset page and file in the expected place.

    scripts/check_site_paths.py _site

The dataset pages and edit redirects come from the Jekyll plugin and the json,
api and rdf files from scripts/export_site_data.py. Each has its own copy of
the rule that turns an identifier into a path; this fails if they disagree, or
if anything is missing.
"""
import json
import re
import sys
from pathlib import Path

from export_site_data import JSONLD_ID, ROOT, dataset_path, dataset_uri, load_records

JSONLD = re.compile(r'<script type="application/ld\+json" id="%s">(.*?)</script>' % JSONLD_ID, re.S)


def jsonld_problem(page, identifier):
    """Why a dataset page's embedded JSON-LD is wrong, or None. (Escapes like \\u003c are plain JSON.)"""
    found = JSONLD.findall(page.read_text(encoding="utf-8"))
    if len(found) != 1:
        return "has %d JSON-LD scripts, not 1" % len(found)
    try:
        data = json.loads(found[0])
    except ValueError as e:
        return "JSON-LD is not valid JSON: %s" % e
    nodes = data.get("@graph", [data]) if isinstance(data, dict) else []
    wanted = str(dataset_uri(identifier))
    if not any(n.get("@id") == wanted or n.get("@id") == wanted.replace("http://lod-cloud.net/", "") for n in nodes
               if isinstance(n, dict)):
        return "JSON-LD does not describe %s" % wanted
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    site = Path(sys.argv[1])
    records = load_records(ROOT / "data" / "datasets")
    missing = []
    for rec in records:
        p = dataset_path(rec["identifier"])
        expected = [site / "dataset" / p / "index.html", site / "edit-dataset" / p / "index.html",
                    site / "json" / p, site / "api" / p,
                    site / "rdf" / p, site / "ttl" / p, site / "nt" / p]
        missing += [str(e.relative_to(site)) for e in expected if not e.is_file()]
        page = site / "dataset" / p / "index.html"
        if page.is_file():
            problem = jsonld_problem(page, rec["identifier"])
            if problem:
                missing.append("dataset/%s/index.html: %s" % (p, problem))

    redirects = json.loads((site / "dataset-redirects.json").read_text(encoding="utf-8"))
    for ident, p in redirects.items():
        if not (site / "dataset" / p / "index.html").is_file():
            missing.append("dataset/%s/index.html (redirect target of %r)" % (p, ident))

    # Nothing else under dataset/, so a page at a different path is noticed.
    wanted = {dataset_path(r["identifier"]) for r in records}
    stray = sorted(d.name for d in (site / "dataset").iterdir() if d.name not in wanted)

    for m in missing[:20]:
        print("missing:", m)
    for s in stray[:20]:
        print("unexpected under dataset/:", s)
    print("%d datasets, %d missing, %d unexpected" % (len(records), len(missing), len(stray)), file=sys.stderr)
    return 1 if missing or stray else 0


if __name__ == "__main__":
    sys.exit(main())
