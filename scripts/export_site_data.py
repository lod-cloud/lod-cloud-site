#!/usr/bin/env python3
"""Write the machine-readable files the old Java site served dynamically.

    scripts/export_site_data.py _site

Run after `jekyll build`, into the built site. For every dataset file in
data/datasets it writes (paths are relative to the output directory):

    lod-data.json, extract/datasets   all datasets, old lod-data.json format
    json/<id>, api/<id>               one dataset, old format
    rdf/<id>, ttl/<id>, nt/<id>       one dataset as RDF/XML, Turtle, N-Triples
                                      (port of RDFView.java, plus DCAT-3, below)
    extract/rdf                       all datasets, N-Triples
    catalog.ttl, catalog.jsonld       the catalogue (dcat:Catalog) with all datasets
    dataset/<id>/index.html           (already built by Jekyll) gets the dataset's RDF as JSON-LD
                                      in a <script type="application/ld+json"> in its head
    dataset-redirects.json            identifier -> path, for 404.html

The RDF is VoID as the old site had it (every old statement is kept, so consumers of the old
files are not affected) with DCAT-3 added to each dataset: it is also a dcat:Dataset, with
dcat:Distribution (downloads), dcat:DataService (SPARQL endpoints), dcat:contactPoint,
dcat:keyword, dcat:theme (the domain) and dcat:landingPage; the links are void:Linkset.

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
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, SKOS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
from domains import DOMAINS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VOID = Namespace("http://rdfs.org/ns/void#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
DATASET_URI = "http://lod-cloud.net/dataset/"
DOMAIN_URI = "http://lod-cloud.net/domain/"
CATALOG_URI = URIRef("http://lod-cloud.net/#catalog")
MEDIA_TYPE_URI = "https://www.iana.org/assignments/media-types/"
SPARQL_PROTOCOL = URIRef("https://www.w3.org/TR/sparql11-protocol/")
RESOURCE_LISTS = ("full_download", "example", "sparql", "other_download")

# Characters GitHub's upload-artifact refuses in a path (and NTFS forbids).
# Keep in sync with LODCloud.dataset_path in site/_plugins/lodcloud.rb;
# scripts/check_site_paths.py checks the two agree on the built site.
UNSAFE = re.compile(r'["<>:|*?\\\r\n]')


def dataset_path(identifier):
    """Directory / file name under dataset/, json/, rdf/, ttl/, nt/ ... for an identifier."""
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


def media_type(value):
    """The IANA URI of a media type such as text/turtle, or None (the data has some free text)."""
    value = (value or "").strip().lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*", value):
        return URIRef(MEDIA_TYPE_URI + value)
    return None


def domain_uri(key):
    return URIRef("%s%s/" % (DOMAIN_URI, key))


def add_dataset(g, rec):
    """Add the triples for one dataset: the old VoID ones (RDFView.createResource) and DCAT-3."""
    ident = rec["identifier"]
    ds = dataset_uri(ident)

    def bnode(kind, i=0):
        return BNode("b" + hashlib.sha1(("%s/%s/%d" % (ident, kind, i)).encode("utf-8")).hexdigest()[:16])

    def add_url(subject, predicate, url):
        node = iri(url or "")
        if node is not None:
            g.add((subject, predicate, node))

    def describe(node, resource):
        """Title, description and media type of a download or endpoint, on its distribution."""
        if resource.get("title"):
            g.add((node, DCTERMS.title, Literal(resource["title"])))
        if resource.get("description"):
            g.add((node, DCTERMS.description, Literal(resource["description"])))
        mt = media_type(resource.get("media_type"))
        if mt is not None:
            g.add((node, DCAT.mediaType, mt))

    g.add((ds, RDF.type, VOID.Dataset))
    g.add((ds, RDF.type, DCAT.Dataset))
    g.add((ds, DCTERMS.identifier, Literal(ident)))
    if rec.get("title"):
        g.add((ds, DCTERMS.title, Literal(rec["title"], lang="en")))
    for lang, text in sorted(rec.get("description", {}).items()):
        g.add((ds, DCTERMS.description, Literal(text, lang=lang)))
    for i, r in enumerate(rec.get("full_download", [])):
        node = iri(r.get("download_url") or "")
        if node is None:
            continue
        g.add((ds, VOID.dataDump, node))
        b = bnode("full", i)
        g.add((ds, DCAT.distribution, b))
        g.add((b, RDF.type, DCAT.Distribution))
        g.add((b, DCAT.downloadURL, node))
        add_url(b, DCAT.accessURL, r.get("access_url"))
        describe(b, r)
    for i, r in enumerate(rec.get("sparql", [])):
        node = iri(r.get("access_url") or "")
        if node is None:
            continue
        g.add((ds, VOID.sparqlEndpoint, node))
        b, service = bnode("sparql", i), bnode("service", i)
        g.add((ds, DCAT.distribution, b))
        g.add((b, RDF.type, DCAT.Distribution))
        g.add((b, DCAT.accessService, service))
        g.add((service, RDF.type, DCAT.DataService))
        g.add((service, DCAT.endpointURL, node))
        g.add((service, DCAT.servesDataset, ds))
        g.add((service, DCTERMS.conformsTo, SPARQL_PROTOCOL))
        describe(service, r)
    for r in rec.get("example", []):
        add_url(ds, VOID.exampleResource, r.get("access_url"))
    for i, r in enumerate(rec.get("other_download", [])):
        node = iri(r.get("access_url", ""))
        if node is not None:
            b = bnode("dist", i)
            g.add((ds, DCAT.distribution, b))
            g.add((b, RDF.type, DCAT.Distribution))
            g.add((b, DCAT.accessURL, node))
            describe(b, r)
    for keyword in rec.get("keywords", []):
        g.add((ds, DCTERMS.subject, Literal(keyword)))
        g.add((ds, DCAT.keyword, Literal(keyword)))
    if rec.get("domain"):
        g.add((ds, DCTERMS.subject, Literal(rec["domain"])))
        g.add((ds, DCAT.theme, domain_uri(rec["domain"])))
    add_url(ds, FOAF.homepage, rec.get("website"))
    add_url(ds, DCAT.landingPage, rec.get("website"))
    add_url(ds, FOAF.depiction, rec.get("image"))
    add_url(ds, VOID.uriSpace, rec.get("namespace"))
    if rec.get("doi"):
        g.add((ds, DCTERMS.identifier, Literal("https://doi.org/" + rec["doi"])))
    contact = rec.get("contact_point")
    if contact:
        b = bnode("publisher")
        g.add((ds, DCTERMS.publisher, b))
        if contact.get("name"):
            g.add((b, RDFS.label, Literal(contact["name"])))
        if contact.get("email"):
            g.add((b, FOAF.mbox, Literal(contact["email"])))
        c = bnode("contact")
        g.add((ds, DCAT.contactPoint, c))
        g.add((c, RDF.type, VCARD.Kind))
        if contact.get("name"):
            g.add((c, VCARD.fn, Literal(contact["name"])))
        if contact.get("email"):
            add_url(c, VCARD.hasEmail, "mailto:" + contact["email"].strip())
    for link in rec.get("links", []):
        # A linkset of its own, named after the pair of datasets (the old site wrote an
        # unnamed one, and only for links with a known count).
        target = dataset_uri(link["target"])
        ls = URIRef("%s#linkset-%s" % (ds, java_url_encode(link["target"])))
        g.add((ls, RDF.type, VOID.Linkset))
        g.add((ls, VOID.subjectsTarget, ds))
        g.add((ls, VOID.objectsTarget, target))
        g.add((ls, VOID.target, ds))
        g.add((ls, VOID.target, target))
        if "value" in link:
            g.add((ls, VOID.triples, Literal(str(link["value"]), datatype=XSD.integer)))
    if "triples" in rec:
        g.add((ds, VOID.triples, Literal(str(rec["triples"]), datatype=XSD.integer)))
    # The Java code read "license_url", a field that never existed, so no
    # license was ever emitted. The field is "license".
    add_url(ds, DCTERMS.license, rec.get("license"))


def add_catalog(g, records):
    """The dcat:Catalog: the datasets, and the domains as a SKOS concept scheme (dcat:theme)."""
    g.add((CATALOG_URI, RDF.type, DCAT.Catalog))
    g.add((CATALOG_URI, DCTERMS.title, Literal("The Linked Open Data Cloud", lang="en")))
    g.add((CATALOG_URI, DCTERMS.description, Literal(
        "Datasets published as Linked Open Data, the catalogue behind the LOD Cloud diagram.", lang="en")))
    g.add((CATALOG_URI, FOAF.homepage, URIRef("https://lod-cloud.net/")))
    g.add((CATALOG_URI, DCAT.themeTaxonomy, URIRef(DOMAIN_URI)))
    scheme = URIRef(DOMAIN_URI)
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, DCTERMS.title, Literal("Domains of the LOD Cloud", lang="en")))
    for key, label in DOMAINS.items():
        concept = domain_uri(key)
        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept, SKOS.inScheme, scheme))
        g.add((scheme, SKOS.hasTopConcept, concept))
    for rec in records:
        g.add((CATALOG_URI, DCAT.dataset, dataset_uri(rec["identifier"])))


# Prefixes for the JSON-LD embedded in the dataset pages (keeps it short and readable)
JSONLD_CONTEXT = {"dcat": str(DCAT), "dcterms": str(DCTERMS), "foaf": str(FOAF), "rdfs": str(RDFS),
                  "void": str(VOID), "vcard": str(VCARD), "skos": str(SKOS), "xsd": str(XSD)}
JSONLD_ID = "dataset-jsonld"


def json_for_html(text):
    """JSON that is safe inside <script>: no "<" (so no </script> or <!--) and no line separators."""
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") \
               .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def embed_jsonld(page, graph):
    """Put the graph into the head of the dataset page as JSON-LD. Returns False if there is no page.

    A client that fetches /dataset/<id> can then read the RDF from the page, which is all a
    static host allows instead of content negotiation (#115). Running it again replaces the script.
    """
    if not page.is_file():
        return False
    html = page.read_text(encoding="utf-8")
    html = re.sub(r'<script type="application/ld\+json" id="%s">.*?</script>\n?' % JSONLD_ID, "", html, flags=re.S)
    data = graph.serialize(format="json-ld", context=JSONLD_CONTEXT, indent=1)
    tag = '<script type="application/ld+json" id="%s">\n%s\n</script>\n' % (JSONLD_ID, json_for_html(data))
    if "</head>" not in html:
        return False
    page.write_text(html.replace("</head>", tag + "</head>", 1), encoding="utf-8")
    return True


def new_graph():
    g = Graph()
    for prefix, ns in (("void", VOID), ("dcterms", DCTERMS), ("foaf", FOAF),
                       ("dcat", DCAT), ("rdfs", RDFS), ("xsd", XSD), ("vcard", VCARD),
                       ("skos", SKOS)):
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
        for directory, fmt in (("rdf", "xml"), ("ttl", "turtle"), ("nt", "nt")):
            write(out / directory / p, g.serialize(format=fmt))
        embed_jsonld(out / "dataset" / p / "index.html", g)
    write(out / "extract" / "rdf", all_rdf.serialize(format="nt"))
    catalog = new_graph()
    for rec in records:
        add_dataset(catalog, rec)
    add_catalog(catalog, records)
    write(out / "catalog.ttl", catalog.serialize(format="turtle"))
    write(out / "catalog.jsonld", catalog.serialize(format="json-ld", indent=1))

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
