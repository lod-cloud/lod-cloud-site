#!/usr/bin/env python3
"""Convert the legacy lod-data.json into one JSON file per dataset.

    scripts/migrate_lod_data.py lod-data.json data [--report report.md]

Writes data/datasets/<filename>.json (see schema/README.md for the filename
rule) and data/conflicts/ for records whose identifier differs from another
only by case. Only mechanical normalisations are applied; everything else is
left for the validation script and reported. Safe to re-run: it replaces the
two output directories.
"""
import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "dataset.schema.json"
RESOURCES = ("full_download", "other_download", "example", "sparql")
HTTP = re.compile(r"^https?://\S+$")
DOI = re.compile(r"^10\.\d{4,9}/\S+$")
HOSTLIKE = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(/\S*)?$")


def filename(identifier):
    out = []
    last = len(identifier) - 1
    for i, ch in enumerate(identifier):
        if re.fullmatch(r"[A-Za-z0-9_-]", ch) or (ch == "." and 0 < i < last):
            out.append(ch)
        else:
            out.append("".join("%%%02X" % b for b in ch.encode("utf-8")))
    return "".join(out) + ".json"


class Stats:
    def __init__(self):
        self.counts = collections.Counter()
        self.examples = collections.defaultdict(list)

    def note(self, kind, ident, detail=None):
        self.counts[kind] += 1
        self.examples[kind].append((ident, detail))


def text(v):
    return v.strip() if isinstance(v, str) and v.strip() else None


def parse_int(v):
    """Digits with optional thousands commas -> int, else None."""
    v = str(v).strip().strip('"').replace(",", "")
    return int(v) if v.isdigit() else None


def convert(ident, d, st):
    out = {"identifier": ident}
    if text(d.get("title")):
        out["title"] = d["title"].strip()

    desc = {k: v.strip() for k, v in (d.get("description") or {}).items() if text(v)}
    if desc:
        out["description"] = desc
    else:
        st.note("description omitted (empty)", ident)

    domain = (d.get("domain") or "").strip().replace("-", "_")
    if domain:
        if domain != d["domain"]:
            st.note("domain cross-domain -> cross_domain", ident)
        out["domain"] = domain
    else:
        st.note("domain omitted (empty)", ident)

    web = text(d.get("website"))
    if web and not HTTP.match(web):
        if HOSTLIKE.match(web):
            st.note("website: added http://", ident, web)
            web = "http://" + web
        else:
            st.note("website dropped (not a URL)", ident, web)
            web = None
    if web:
        out["website"] = web

    for k in ("license", "namespace"):
        if text(d.get(k)):
            out[k] = d[k].strip()

    t = d.get("triples")
    if isinstance(t, int):
        out["triples"] = t
    elif text(t):
        n = parse_int(t)
        if n is None:
            st.note("triples dropped (not an integer)", ident, t)
        else:
            out["triples"] = n
            st.note("triples string -> integer", ident)

    doi = text(d.get("doi"))
    if doi:
        bare = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi)
        if DOI.match(bare):
            out["doi"] = bare
        else:
            st.note("doi dropped (not a DOI)", ident, doi)

    img = text(d.get("image")) or text(d.get("Image"))
    if "Image" in d and d["Image"]:
        st.note("Image -> image", ident)
    if img:
        out["image"] = img

    cp = d.get("contact_point") or {}
    contact = {k: cp[k].strip() for k in ("name", "email") if text(cp.get(k))}
    if contact:
        out["contact_point"] = contact

    kws = []
    for k in d.get("keywords") or []:
        if text(k) and k.strip() not in kws:
            kws.append(k.strip())
    if kws:
        out["keywords"] = kws

    links = {}
    for l in d.get("links") or []:
        target = text(l.get("target"))
        if not target:
            continue
        if target in links:
            st.note("duplicate link target dropped", ident, target)
            continue
        link = {"target": target}
        raw = l.get("value")
        n = parse_int(raw)
        if n is None and text(raw) and re.fullmatch(r">\s*[\d,]+", raw.strip()):
            n = parse_int(raw.strip()[1:])
            st.note("link value '>N' -> N", ident, raw)
        elif n is None:
            st.note("link value omitted (not a number)", ident, raw)
        elif str(raw) != str(n):
            st.note("link value cleaned", ident, raw)
        if n:
            link["value"] = n
        links[target] = link
    if links:
        out["links"] = [links[t] for t in sorted(links)]

    for field in RESOURCES:
        res = []
        for r in d.get(field) or []:
            e = {}
            for k in ("title", "description", "media_type", "download_url", "access_url"):
                if text(r.get(k)):
                    e[k] = r[k].strip()
            if field == "full_download" and "download_url" not in e:
                st.note("resource dropped (no download_url)", ident, r.get("access_url"))
                continue
            if field != "full_download" and "access_url" not in e:
                st.note("resource dropped (no access_url)", ident, r)
                continue
            res.append(e)
        if res:
            out[field] = res
    return out


def normalise_targets(records, st):
    """Apply the old Java loader's identifier rule to link targets.

    MongoConnection rewrote identifiers (space -> '_', '?', '/', '\\' removed)
    but not link targets, so some links point at the pre-rewrite spelling.
    Only rewritten when the result is an existing dataset.
    """
    ids = set(records)
    for ident, rec in records.items():
        links = rec.get("links")
        if not links:
            continue
        seen = set()
        fixed = []
        for l in links:
            t = l["target"]
            if t not in ids:
                n = re.sub(r"[?/\\]", "", t.replace(" ", "_"))
                if n in ids:
                    st.note("link target normalised (space -> _)", ident, "%s -> %s" % (t, n))
                    l = dict(l, target=n)
            if l["target"] in seen:
                st.note("duplicate link target dropped", ident, l["target"])
                continue
            seen.add(l["target"])
            fixed.append(l)
        rec["links"] = sorted(fixed, key=lambda x: x["target"])


def case_conflicts(data):
    groups = collections.defaultdict(list)
    for ident in data:
        groups[ident.lower()].append(ident)
    return [sorted(g) for g in groups.values() if len(g) > 1]


def weight(rec):
    return len(rec.get("links", [])) + sum(len(rec.get(f, [])) for f in RESOURCES)


def write(path, rec):
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="legacy lod-data.json")
    ap.add_argument("out", help="output directory, e.g. data")
    ap.add_argument("--report", help="write a markdown report here")
    args = ap.parse_args()

    legacy = json.loads(Path(args.source).read_text(encoding="utf-8"))
    st = Stats()
    records = {}
    for key, d in legacy.items():
        ident = d.get("identifier") or key
        if ident != key:
            st.note("key differs from identifier", key, ident)
        records[ident] = convert(ident, d, st)
    normalise_targets(records, st)

    out = Path(args.out)
    for sub in ("datasets", "conflicts"):
        shutil.rmtree(out / sub, ignore_errors=True)
        (out / sub).mkdir(parents=True)

    conflicts = case_conflicts(records)
    excluded = {}
    for group in conflicts:
        keep = sorted(group, key=lambda i: (-weight(records[i]), i))[0]
        for ident in group:
            if ident != keep:
                excluded[ident] = keep
    for ident, rec in records.items():
        if ident in excluded:
            digest = hashlib.sha1(ident.encode("utf-8")).hexdigest()[:8]
            name = filename(ident.lower())[:-5] + "." + digest + ".json"
            write(out / "conflicts" / name, rec)
        else:
            write(out / "datasets" / filename(ident), rec)

    report(args, records, excluded, conflicts, st)


def report(args, records, excluded, conflicts, st):
    lines = ["# Migration report", ""]
    lines.append("Source: %s. Datasets: %d. Written to datasets/: %d. Case conflicts moved to conflicts/: %d."
                 % (args.source, len(records), len(records) - len(excluded), len(excluded)))
    lines += ["", "## Case-insensitive identifier conflicts", ""]
    for group in conflicts:
        keep = [i for i in group if i not in excluded][0]
        lines.append("- kept `%s`, set aside %s" % (keep, ", ".join("`%s`" % i for i in group if i != keep)))

    lines += ["", "## Normalisations applied", "", "| Change | Records |", "|---|---|"]
    for k, n in sorted(st.counts.items()):
        lines.append("| %s | %d |" % (k, n))

    lines += ["", "## Values dropped or altered that need a human", ""]
    for kind in sorted(st.examples):
        items = [(i, d) for i, d in st.examples[kind] if d is not None]
        if items and kind.startswith(("triples dropped", "doi dropped", "website", "link value", "resource dropped", "duplicate", "link target")):
            lines.append("**%s** (%d)" % (kind, len(items)))
            for i, d in items[:40]:
                lines.append("- `%s`: `%s`" % (i, str(d).replace("`", "'")[:100]))
            if len(items) > 40:
                lines.append("- ... %d more" % (len(items) - 40))
            lines.append("")

    ids = set(records)
    dangling = [(i, l["target"]) for i, r in records.items() for l in r.get("links", []) if l["target"] not in ids]
    selflinks = [i for i, r in records.items() for l in r.get("links", []) if l["target"] == i]
    lower = {i.lower() for i in ids}
    case_only = [(i, t) for i, t in dangling if t.lower() in lower]
    lines += ["## Link problems (not changed)", "",
              "- links to a dataset that does not exist: %d, across %d distinct targets" % (len(dangling), len({t for _, t in dangling})),
              "- of those, %d match an existing dataset only ignoring case (e.g. `%s`)" % (len(case_only), case_only[0][1] if case_only else ""),
              "- links from a dataset to itself: %d" % len(selflinks), ""]

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        lines.append("(jsonschema not installed; schema violations not computed)")
    else:
        v = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        kinds = collections.Counter()
        bad = 0
        for rec in records.values():
            errs = list(v.iter_errors(rec))
            bad += bool(errs)
            for e in errs:
                where = ".".join(str(p) for p in e.absolute_path if not isinstance(p, int)) or "(record)"
                msg = e.message if e.validator == "required" else "%s: %s" % (e.validator, where)
                kinds[msg] += 1
        lines += ["## Schema violations (strict schema, before any cleanup)", "",
                  "%d of %d records have at least one violation." % (bad, len(records)), "",
                  "| Violation | Count |", "|---|---|"]
        for k, n in kinds.most_common():
            lines.append("| %s | %d |" % (k.replace("|", "/"), n))

    text_out = "\n".join(lines) + "\n"
    if args.report:
        Path(args.report).write_text(text_out, encoding="utf-8")
    else:
        sys.stdout.write(text_out)


if __name__ == "__main__":
    main()
