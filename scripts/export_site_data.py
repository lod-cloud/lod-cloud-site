#!/usr/bin/env python3
"""Write the machine-readable files the old Java site served dynamically.

    scripts/export_site_data.py _site

Run after `jekyll build`, into the built site. For every dataset file in
data/datasets it writes (paths are relative to the output directory):

    lod-data.json, extract/datasets   all datasets, old lod-data.json format
    json/<id>, api/<id>               one dataset, old format
    rdf/<id>.ttl|.rdf|.nt             one dataset as RDF (port of RDFView.java)
    rdf/<id>                          the same Turtle, for old /rdf/<id>[?format=ttl] links
    extract/rdf                       all datasets, N-Triples
    dataset-redirects.json            identifier -> path, for 404.html

<id> is the identifier, except identifiers containing characters that cannot
be in a published file name (see UNSAFE), which are percent-encoded.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parent.parent
VOID = Namespace("http://rdfs.org/ns/void#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DATASET_URI = "http://lod-cloud.net/dataset/"
RESOURCE_LISTS = ("full_download", "example", "sparql", "other_download")

# Characters GitHub's upload-artifact refuses in a path (and NTFS forbids).
# Keep in sync with LODCloud.dataset_path in site/_plugins/lodcloud.rb;
# scripts/check_site_paths.py checks the two agree on the built site.
UNSAFE = re.compile(r'["<>:|*?\\\r\n]')


def dataset_path(identifier):
    """Directory / file name under dataset/, json/, rdf/ ... for an identifier."""
    if UNSAFE.search(identifier):
        return urllib.parse.quote(identifier, safe="")
    return identifier


def java_url_encode(text):
    """java.net.URLEncoder.encode(text, "UTF-8"), which the old dataset URIs used."""
    return urllib.parse.quote_plus(text, safe="*").replace("~", "%7E")


def dataset_uri(identifier):
    return URIRef(DATASET_URI + java_url_encode(identifier))


def legacy_record(rec):
    """A record in the format of the old lod-data.json.

    The old consumers (GetData, lod-cloud-draw) expect every list to be
    present, so empty ones are written out. owner, status and mirror were
    dropped in the migration and are not restored.
    """
    contact = rec.get("contact_point") or {}
    out = {
        "_id": rec["identifier"],
        "identifier": rec["identifier"],
        "doi": rec.get("doi", ""),
        "image": rec.get("image", ""),
        "keywords": rec.get("keywords", []),
        "links": [{"target": l["target"], "value": str(l["value"]) if "value" in l else "unknown"}
                  for l in rec.get("links", [])],
        "title": rec.get("title", ""),
    }
    for field in RESOURCE_LISTS:
        out[field] = rec.get(field, [])
    out.update({
        "description": rec.get("description", {"en": ""}),
        "owner": "",
        "website": rec.get("website"),
        "triples": rec.get("triples", 0),
        "domain": rec.get("domain", ""),
        "namespace": rec.get("namespace", ""),
        "contact_point": {"name": contact.get("name"), "email": contact.get("email")},
    })
    if "license" in rec:
        out["license"] = rec["license"]
    return out


def iri(url):
    """An IRI for a URL from the data, or None if it has no scheme.

    Characters not allowed in an IRI are percent-encoded; the old code only
    escaped < and >, leaving e.g. spaces to produce invalid N-Triples.
    """
    url = url.strip()
    if not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", url):
        return None
    return URIRef(re.sub(r'[\x00-\x20"<>\\^`{|}]', lambda m: "%%%02X" % ord(m.group()), url))


def add_dataset(g, rec):
    """Add the triples for one dataset (port of RDFView.createResource)."""
    ident = rec["identifier"]
    ds = dataset_uri(ident)

    def bnode(kind, i=0):
        return BNode("b" + hashlib.sha1(("%s/%s/%d" % (ident, kind, i)).encode("utf-8")).hexdigest()[:16])

    def add_url(subject, predicate, url):
        node = iri(url or "")
        if node is not None:
            g.add((subject, predicate, node))

    g.add((ds, RDF.type, VOID.Dataset))
    if rec.get("title"):
        g.add((ds, DCTERMS.title, Literal(rec["title"], lang="en")))
    for lang, text in sorted(rec.get("description", {}).items()):
        g.add((ds, DCTERMS.description, Literal(text, lang=lang)))
    for r in rec.get("full_download", []):
        add_url(ds, VOID.dataDump, r.get("download_url"))
    for r in rec.get("sparql", []):
        add_url(ds, VOID.sparqlEndpoint, r.get("access_url"))
    for r in rec.get("example", []):
        add_url(ds, VOID.exampleResource, r.get("access_url"))
    for i, r in enumerate(rec.get("other_download", [])):
        node = iri(r.get("access_url", ""))
        if node is not None:
            b = bnode("dist", i)
            g.add((ds, DCAT.distribution, b))
            g.add((b, DCAT.accessURL, node))
    for keyword in rec.get("keywords", []):
        g.add((ds, DCTERMS.subject, Literal(keyword)))
    if rec.get("domain"):
        g.add((ds, DCTERMS.subject, Literal(rec["domain"])))
    add_url(ds, FOAF.homepage, rec.get("website"))
    contact = rec.get("contact_point")
    if contact:
        b = bnode("publisher")
        g.add((ds, DCTERMS.publisher, b))
        if contact.get("name"):
            g.add((b, RDFS.label, Literal(contact["name"])))
        if contact.get("email"):
            g.add((b, FOAF.mbox, Literal(contact["email"])))
    for i, link in enumerate(rec.get("links", [])):
        if "value" not in link:
            continue
        b = bnode("link", i)
        g.add((b, VOID.target, ds))
        g.add((b, VOID.target, dataset_uri(link["target"])))
        g.add((b, VOID.triples, Literal(str(link["value"]), datatype=XSD.integer)))
    if "triples" in rec:
        g.add((ds, VOID.triples, Literal(str(rec["triples"]), datatype=XSD.integer)))
    # The Java code read "license_url", a field that never existed, so no
    # license was ever emitted. The field is "license".
    add_url(ds, DCTERMS.license, rec.get("license"))


def new_graph():
    g = Graph()
    for prefix, ns in (("void", VOID), ("dcterms", DCTERMS), ("foaf", FOAF),
                       ("dcat", DCAT), ("rdfs", RDFS), ("xsd", XSD)):
        g.bind(prefix, ns)
    return g


def load_records(data_dir):
    records = []
    for path in sorted(Path(data_dir).glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.write_bytes(content)


def export(records, out):
    out = Path(out)
    paths = {}
    for rec in records:
        p = dataset_path(rec["identifier"])
        if p in paths:
            raise SystemExit("Identifiers %r and %r have the same path %r" % (paths[p], rec["identifier"], p))
        paths[p] = rec["identifier"]

    legacy = {rec["identifier"]: legacy_record(rec) for rec in records}
    everything = json.dumps(legacy, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    write(out / "lod-data.json", everything)
    write(out / "extract" / "datasets", everything)

    all_rdf = new_graph()
    for rec in records:
        p = dataset_path(rec["identifier"])
        one = json.dumps(legacy[rec["identifier"]], indent=2, ensure_ascii=False) + "\n"
        write(out / "json" / p, one)
        write(out / "api" / p, one)

        g = new_graph()
        add_dataset(g, rec)
        add_dataset(all_rdf, rec)
        for ext, fmt in (("ttl", "turtle"), ("rdf", "xml"), ("nt", "nt")):
            serialized = g.serialize(format=fmt)
            write(out / "rdf" / (p + "." + ext), serialized)
            if ext == "ttl":
                # A static server ignores ?format=, so /rdf/<id> can only be one
                # format; the old default was Turtle.
                write(out / "rdf" / p, serialized)
    write(out / "extract" / "rdf", all_rdf.serialize(format="nt"))

    redirects = {i: p for p, i in paths.items() if p != i}
    write(out / "dataset-redirects.json", json.dumps(redirects, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    return len(records), len(redirects)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="output directory (the built site)")
    ap.add_argument("--data", default=str(ROOT / "data" / "datasets"))
    args = ap.parse_args(argv)
    records = load_records(args.data)
    count, encoded = export(records, args.out)
    print("Exported %d datasets (%d with an encoded path) to %s" % (count, encoded, args.out), file=sys.stderr)


if __name__ == "__main__":
    main()
