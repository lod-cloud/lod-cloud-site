import json
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, RDF, XSD

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

    def test_only_links_with_a_count_become_linksets(self):
        g = graph_of(FULL)
        targets = {o for _, _, o in g.triples((None, ex.VOID.target, None))}
        self.assertIn(URIRef("http://lod-cloud.net/dataset/other"), targets)
        self.assertNotIn(URIRef("http://lod-cloud.net/dataset/unknown-count"), targets)

    def test_invalid_urls_are_skipped_or_escaped(self):
        rec = dict(MINIMAL, full_download=[{"download_url": "not a url"}, {"download_url": "http://x.org/a b"}])
        g = graph_of(rec)
        self.assertEqual([str(o) for o in g.objects(None, ex.VOID.dataDump)], ["http://x.org/a%20b"])

    def test_output_is_deterministic(self):
        self.assertEqual(sorted(graph_of(FULL).serialize(format="nt").splitlines()),
                         sorted(graph_of(FULL).serialize(format="nt").splitlines()))

    def test_dataset_uri_uses_the_old_encoding(self):
        self.assertEqual(str(ex.dataset_uri("a b:c")), "http://lod-cloud.net/dataset/a+b%3Ac")


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
