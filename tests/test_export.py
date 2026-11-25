import json
import sys
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, RDF, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_site_data as ex

FULL = {
    "identifier": "full",
    "title": "Full",
    "description": {"en": "English", "fr": "Français"},
    "domain": "media",
    "website": "https://example.org/",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "triples": 1500,
    "contact_point": {"name": "A", "email": "a@example.org"},
    "keywords": ["k"],
    "links": [{"target": "other", "value": 12}, {"target": "unknown-count"}],
    "full_download": [{"download_url": "https://example.org/dump.ttl"}],
    "sparql": [{"access_url": "https://example.org/sparql"}],
    "example": [{"access_url": "https://example.org/r/1"}],
    "other_download": [{"access_url": "https://example.org/doc"}],
}
MINIMAL = {"identifier": "min", "title": "Min"}


def graph_of(rec):
    g = ex.new_graph()
    ex.add_dataset(g, rec)
    return g


class LegacyTest(unittest.TestCase):
    def test_minimal_record_has_every_list_the_old_consumers_need(self):
        legacy = ex.legacy_record(MINIMAL)
        for field in ex.RESOURCE_LISTS + ("keywords", "links"):
            self.assertEqual(legacy[field], [])
        self.assertEqual(legacy["_id"], "min")
        self.assertIsNone(legacy["website"])
        self.assertEqual(legacy["triples"], 0)
        self.assertEqual(legacy["contact_point"], {"name": None, "email": None})
        self.assertNotIn("license", legacy)

    def test_link_values_are_strings_as_before(self):
        links = ex.legacy_record(FULL)["links"]
        self.assertEqual(links, [{"target": "other", "value": "12"}, {"target": "unknown-count", "value": "unknown"}])

    def test_matches_the_old_field_order(self):
        self.assertEqual(list(ex.legacy_record(FULL))[:4], ["_id", "identifier", "doi", "image"])


class PathTest(unittest.TestCase):
    def test_safe_identifiers_are_unchanged(self):
        for ident in ("dbpedia", "Qualité_de_l'air", "a b#c", "100%", "x.", "_lead"):
            self.assertEqual(ex.dataset_path(ident), ident)

    def test_unsafe_characters_are_encoded(self):
        self.assertEqual(ex.dataset_path("ISSN:0080-3626"), "ISSN%3A0080-3626")
        self.assertEqual(ex.dataset_path('a"b|c*d'), "a%22b%7Cc%2Ad")

    def test_collisions_are_refused(self):
        with self.assertRaises(SystemExit):
            ex.export([{"identifier": "a:b"}, {"identifier": "a%3Ab"}], tempfile.mkdtemp())

    def test_java_url_encoding(self):
        self.assertEqual(ex.java_url_encode("a b~c*d/é"), "a+b%7Ec*d%2F%C3%A9")


class RdfTest(unittest.TestCase):
    def test_dataset_triples(self):
        g = graph_of(FULL)
        ds = URIRef("http://lod-cloud.net/dataset/full")
        self.assertIn((ds, RDF.type, ex.VOID.Dataset), g)
        self.assertIn((ds, DCTERMS.title, Literal("Full", lang="en")), g)
        self.assertIn((ds, DCTERMS.description, Literal("Français", lang="fr")), g)
        self.assertIn((ds, ex.VOID.dataDump, URIRef("https://example.org/dump.ttl")), g)
        self.assertIn((ds, ex.VOID.sparqlEndpoint, URIRef("https://example.org/sparql")), g)
        self.assertIn((ds, ex.VOID.exampleResource, URIRef("https://example.org/r/1")), g)
        self.assertIn((ds, ex.VOID.triples, Literal("1500", datatype=XSD.integer)), g)
        self.assertIn((ds, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")), g)
        self.assertIn((ds, DCTERMS.subject, Literal("media")), g)

    def test_every_link_is_a_linkset_and_only_known_counts_have_triples(self):
        g = graph_of(FULL)
        ds = URIRef("http://lod-cloud.net/dataset/full")
        other = URIRef("http://lod-cloud.net/dataset/other")
        ls = URIRef("http://lod-cloud.net/dataset/full#linkset-other")
        for triple in ((ls, RDF.type, ex.VOID.Linkset), (ls, ex.VOID.subjectsTarget, ds),
                       (ls, ex.VOID.objectsTarget, other), (ls, ex.VOID.target, ds), (ls, ex.VOID.target, other),
                       (ls, ex.VOID.triples, Literal("12", datatype=XSD.integer))):
            self.assertIn(triple, g)
        unknown = URIRef("http://lod-cloud.net/dataset/full#linkset-unknown-count")
        self.assertIn((unknown, ex.VOID.objectsTarget, URIRef("http://lod-cloud.net/dataset/unknown-count")), g)
        self.assertEqual(list(g.objects(unknown, ex.VOID.triples)), [])

    def test_invalid_urls_are_skipped_or_escaped(self):
        rec = dict(MINIMAL, full_download=[{"download_url": "not a url"}, {"download_url": "http://x.org/a b"}])
        g = graph_of(rec)
        self.assertEqual([str(o) for o in g.objects(None, ex.VOID.dataDump)], ["http://x.org/a%20b"])

    def test_output_is_deterministic(self):
        self.assertEqual(sorted(graph_of(FULL).serialize(format="nt").splitlines()),
                         sorted(graph_of(FULL).serialize(format="nt").splitlines()))

    def test_dataset_uri_uses_the_old_encoding(self):
        self.assertEqual(str(ex.dataset_uri("a b:c")), "http://lod-cloud.net/dataset/a+b%3Ac")


DCAT = ex.DCAT
VCARD = ex.VCARD


class DcatTest(unittest.TestCase):
    def setUp(self):
        rec = dict(FULL, doi="10.1234/x", image="https://example.org/logo.png", namespace="https://example.org/ns/",
                   full_download=[{"title": "Dump", "description": "All", "media_type": "text/turtle",
                                   "download_url": "https://example.org/dump.ttl", "access_url": "https://example.org/page"}],
                   sparql=[{"title": "Endpoint", "access_url": "https://example.org/sparql"}],
                   other_download=[{"access_url": "https://example.org/doc", "media_type": "image"}])
        self.g = graph_of(rec)
        self.ds = URIRef("http://lod-cloud.net/dataset/full")

    def one(self, s, p):
        values = list(self.g.objects(s, p))
        self.assertEqual(len(values), 1, (s, p, values))
        return values[0]

    def test_a_dataset_is_both_void_and_dcat(self):
        for cls in (ex.VOID.Dataset, DCAT.Dataset):
            self.assertIn((self.ds, RDF.type, cls), self.g)
        self.assertIn((self.ds, DCTERMS.identifier, Literal("full")), self.g)
        self.assertIn((self.ds, DCTERMS.identifier, Literal("https://doi.org/10.1234/x")), self.g)
        self.assertIn((self.ds, DCAT.keyword, Literal("k")), self.g)
        self.assertIn((self.ds, DCAT.landingPage, URIRef("https://example.org/")), self.g)
        self.assertIn((self.ds, DCAT.theme, URIRef("http://lod-cloud.net/domain/media/")), self.g)
        self.assertIn((self.ds, ex.VOID.uriSpace, URIRef("https://example.org/ns/")), self.g)

    def test_a_full_download_is_a_distribution_and_still_a_void_dump(self):
        self.assertIn((self.ds, ex.VOID.dataDump, URIRef("https://example.org/dump.ttl")), self.g)
        dist = [d for d in self.g.objects(self.ds, DCAT.distribution)
                if (d, DCAT.downloadURL, URIRef("https://example.org/dump.ttl")) in self.g]
        self.assertEqual(len(dist), 1)
        d = dist[0]
        self.assertIn((d, RDF.type, DCAT.Distribution), self.g)
        self.assertIn((d, DCAT.accessURL, URIRef("https://example.org/page")), self.g)
        self.assertEqual(self.one(d, DCTERMS.title), Literal("Dump"))
        self.assertEqual(self.one(d, DCAT.mediaType), URIRef("https://www.iana.org/assignments/media-types/text/turtle"))

    def test_a_sparql_endpoint_is_a_data_service(self):
        self.assertIn((self.ds, ex.VOID.sparqlEndpoint, URIRef("https://example.org/sparql")), self.g)
        services = list(self.g.subjects(RDF.type, DCAT.DataService))
        self.assertEqual(len(services), 1)
        s = services[0]
        self.assertEqual(self.one(s, DCAT.endpointURL), URIRef("https://example.org/sparql"))
        self.assertEqual(self.one(s, DCAT.servesDataset), self.ds)
        self.assertEqual(self.one(s, DCTERMS.conformsTo), ex.SPARQL_PROTOCOL)
        self.assertEqual(len(list(self.g.subjects(DCAT.accessService, s))), 1)

    def test_free_text_media_types_are_not_made_into_uris(self):
        doc = [d for d in self.g.objects(self.ds, DCAT.distribution)
               if (d, DCAT.accessURL, URIRef("https://example.org/doc")) in self.g][0]
        self.assertEqual(list(self.g.objects(doc, DCAT.mediaType)), [])

    def test_contact_point_is_a_vcard_and_the_old_publisher_stays(self):
        c = self.one(self.ds, DCAT.contactPoint)
        self.assertIn((c, RDF.type, VCARD.Kind), self.g)
        self.assertEqual(self.one(c, VCARD.fn), Literal("A"))
        self.assertEqual(self.one(c, VCARD.hasEmail), URIRef("mailto:a@example.org"))
        self.assertEqual(len(list(self.g.objects(self.ds, DCTERMS.publisher))), 1)

    def test_old_triples_are_all_still_there(self):
        old = [(self.ds, ex.VOID.dataDump, URIRef("https://example.org/dump.ttl")),
               (self.ds, ex.VOID.exampleResource, URIRef("https://example.org/r/1")),
               (self.ds, DCTERMS.subject, Literal("media")), (self.ds, DCTERMS.subject, Literal("k"))]
        for t in old:
            self.assertIn(t, self.g)

    def test_the_catalog_lists_the_datasets_and_the_domains(self):
        g = ex.new_graph()
        ex.add_dataset(g, FULL)
        ex.add_catalog(g, [FULL, MINIMAL])
        self.assertIn((ex.CATALOG_URI, RDF.type, DCAT.Catalog), g)
        self.assertEqual({str(o) for o in g.objects(ex.CATALOG_URI, DCAT.dataset)},
                         {"http://lod-cloud.net/dataset/full", "http://lod-cloud.net/dataset/min"})
        concepts = list(g.subjects(RDF.type, ex.SKOS.Concept))
        self.assertEqual(len(concepts), len(ex.DOMAINS))
        self.assertIn((URIRef("http://lod-cloud.net/domain/media/"), ex.SKOS.prefLabel, Literal("Media", lang="en")), g)

    def test_catalog_files_are_written_and_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            ex.export([FULL, MINIMAL], tmp)
            ttl = Graph().parse(Path(tmp) / "catalog.ttl", format="turtle")
            js = Graph().parse(Path(tmp) / "catalog.jsonld", format="json-ld")
            self.assertTrue(isomorphic(ttl, js))
            self.assertIn((ex.CATALOG_URI, DCAT.dataset, URIRef("http://lod-cloud.net/dataset/min")), ttl)


PAGE = "<!DOCTYPE html><html><head><title>x</title>\n</head><body>x</body></html>"


class IriTest(unittest.TestCase):
    def test_brackets_are_escaped_except_in_an_ipv6_host(self):
        self.assertEqual(str(ex.iri("http://x.org/a[1]")), "http://x.org/a%5B1%5D")
        self.assertEqual(str(ex.iri("http://[::1]:8080/a[1]")), "http://[::1]:8080/a%5B1%5D")
        self.assertEqual(str(ex.iri("mailto:a [at] b")), "mailto:a%20%5Bat%5D%20b")

    def test_an_obfuscated_email_gives_no_vcard_email_but_keeps_the_foaf_mbox(self):
        rec = dict(MINIMAL, contact_point={"name": "N", "email": "bernard [dot] vatant [at] example [dot] com"})
        g = graph_of(rec)
        self.assertEqual(list(g.objects(None, VCARD.hasEmail)), [])
        self.assertEqual(len(list(g.objects(None, ex.FOAF.mbox))), 1)
        self.assertEqual(invalid_iris(g), [])

    def test_every_iri_of_the_real_example_data_is_one_a_strict_parser_accepts(self):
        g = ex.new_graph()
        for rec in (FULL, MINIMAL, dict(MINIMAL, full_download=[{"download_url": "http://x.org/a b[1]|{c}"}],
                                        website="http://[2001:db8::1]/x")):
            ex.add_dataset(g, rec)
        self.assertEqual(invalid_iris(g), [])


def invalid_iris(g):
    return ex.invalid_iris(g)


class EmbedTest(unittest.TestCase):
    def embed(self, rec, page_text=PAGE):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        page = Path(tmp.name) / "index.html"
        page.write_text(page_text, encoding="utf-8")
        self.assertTrue(ex.embed_jsonld(page, graph_of(rec)))
        return page

    def scripts(self, page):
        import re
        return re.findall(r'<script type="application/ld\+json" id="dataset-jsonld">(.*?)</script>',
                          page.read_text(encoding="utf-8"), re.S)

    def test_the_page_carries_the_datasets_rdf_as_json_ld(self):
        found = self.scripts(self.embed(FULL))
        self.assertEqual(len(found), 1)
        g = Graph().parse(data=found[0], format="json-ld")
        self.assertTrue(isomorphic(g, graph_of(FULL)))

    def test_it_goes_in_the_head(self):
        text = self.embed(FULL).read_text(encoding="utf-8")
        self.assertLess(text.index('id="dataset-jsonld"'), text.index("</head>"))

    def test_running_again_replaces_it(self):
        page = self.embed(FULL)
        ex.embed_jsonld(page, graph_of(dict(FULL, title="Changed")))
        found = self.scripts(page)
        self.assertEqual(len(found), 1)
        self.assertIn("Changed", found[0])

    def test_hostile_text_cannot_end_the_script(self):
        rec = dict(MINIMAL, title='</script><script>alert(1)</script><!--', description={"en": "a & b <b>x</b>"})
        page = self.embed(rec)
        text = page.read_text(encoding="utf-8")
        self.assertEqual(text.count("</script>"), 1)
        self.assertNotIn("<script>alert", text)
        g = Graph().parse(data=self.scripts(page)[0], format="json-ld")
        self.assertIn(Literal(rec["title"], lang="en"), set(g.objects(None, DCTERMS.title)))

    def test_no_page_or_no_head_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(ex.embed_jsonld(Path(tmp) / "none.html", graph_of(FULL)))
            page = Path(tmp) / "bare.html"
            page.write_text("no head")
            self.assertFalse(ex.embed_jsonld(page, graph_of(FULL)))

    def test_export_embeds_into_the_built_dataset_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("full", "x%3Ay"):
                (Path(tmp) / "dataset" / d).mkdir(parents=True)
                (Path(tmp) / "dataset" / d / "index.html").write_text(PAGE)
            ex.export([FULL, {"identifier": "x:y", "title": "T"}], tmp)
            for d in ("full", "x%3Ay"):
                self.assertIn('id="dataset-jsonld"', (Path(tmp) / "dataset" / d / "index.html").read_text())


class PageCheckTest(unittest.TestCase):
    def test_the_site_check_finds_a_missing_or_wrong_script(self):
        import check_site_paths as cp
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "index.html"
            page.write_text(PAGE)
            self.assertIn("0 JSON-LD scripts", cp.jsonld_problem(page, "full"))
            ex.embed_jsonld(page, graph_of(FULL))
            self.assertIsNone(cp.jsonld_problem(page, "full"))
            self.assertIn("does not describe", cp.jsonld_problem(page, "other"))


class ExportTest(unittest.TestCase):
    def test_files_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ex.export([FULL, MINIMAL, {"identifier": "x:y", "title": "T"}], tmp), (3, 1))
            out = Path(tmp)
            for name in ("lod-data.json", "extract/datasets", "extract/rdf", "json/full", "api/full",
                         "rdf/full", "ttl/full", "nt/full", "json/x%3Ay", "rdf/x%3Ay", "ttl/x%3Ay", "nt/x%3Ay"):
                self.assertTrue((out / name).is_file(), name)
            self.assertEqual(json.loads((out / "extract/datasets").read_text()), json.loads((out / "lod-data.json").read_text()))
            self.assertEqual(json.loads((out / "dataset-redirects.json").read_text()), {"x:y": "x%3Ay"})
            self.assertEqual(json.loads((out / "json/full").read_text())["identifier"], "full")
            # each directory holds the format its name says
            expected = graph_of(FULL)
            for directory, fmt in (("rdf", "xml"), ("ttl", "turtle"), ("nt", "nt")):
                g = Graph().parse(out / directory / "full", format=fmt)
                self.assertTrue(isomorphic(g, expected), directory)


if __name__ == "__main__":
    unittest.main()
