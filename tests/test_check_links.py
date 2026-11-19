import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_links as cl

HITS = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, code, redirect=None):
        HITS.append((self.command, self.path))
        self.send_response(code)
        if redirect:
            self.send_header("Location", redirect)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def handle_any(self):
        path = self.path
        if path == "/ok":
            self.respond(200)
        elif path == "/missing":
            self.respond(404)
        elif path == "/redirect":
            self.respond(302, "/ok")
        elif path == "/no-head":  # refuses HEAD, serves GET
            self.respond(405 if self.command == "HEAD" else 200)
        elif path == "/sparql":  # no query: 400
            self.respond(400)
        else:
            self.respond(500)

    do_GET = do_HEAD = handle_any


class CheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_port
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        HITS.clear()

    def check(self, path, kinds, previous=None):
        url = self.base + path
        return cl.run({url: set(kinds)}, previous or {}, 2, 5, 60, 3, "2026-11-18")[url]

    def test_ok_and_redirect_and_missing(self):
        self.assertEqual(self.check("/ok", ["full_download"])["status"], "OK")
        self.assertEqual(self.check("/redirect", ["full_download"])["status"], "OK")
        missing = self.check("/missing", ["full_download"])
        self.assertEqual((missing["status"], missing["http"]), ("FAIL (404)", 404))

    def test_a_server_that_refuses_head_is_asked_again_with_get(self):
        self.assertEqual(self.check("/no-head", ["other_download"])["status"], "OK")
        self.assertEqual([m for m, p in HITS if p == "/no-head"], ["HEAD", "GET"])

    def test_one_request_for_a_working_url(self):
        self.check("/ok", ["full_download"])
        self.assertEqual(HITS, [("HEAD", "/ok")])

    def test_examples_use_get(self):
        self.check("/ok", ["example"])
        self.assertEqual(HITS, [("GET", "/ok")])

    def test_sparql_endpoint_answering_400_is_alive_but_a_download_is_not(self):
        self.assertEqual(self.check("/sparql", ["sparql"])["status"], "OK")
        self.assertEqual(self.check("/sparql", ["full_download"])["status"], "FAIL (400)")

    def test_unreachable_host_is_given_up_after_a_few_errors(self):
        urls = {"http://127.0.0.1:1/%d" % i: {"full_download"} for i in range(6)}
        state = cl.run(urls, {}, 2, 2, 60, 3, "2026-11-18")
        self.assertTrue(all(r["status"].startswith("FAIL") for r in state.values()))
        self.assertEqual(sum("unreachable" in r["status"] for r in state.values()), 3)

    def test_a_malformed_host_name_is_a_failure_not_a_crash(self):
        url = "http://www.assets.funding.accounts..com/x"
        self.assertEqual(cl.run({url: {"full_download"}}, {}, 1, 2, 60, 3, "2026-11-18")[url]["status"], "FAIL (invalid URL)")

    def test_other_schemes(self):
        r = cl.run({"ftp://example.org/x": {"full_download"}, "ihttp://x/": {"full_download"}}, {}, 1, 2, 60, 3, "2026-11-18")
        self.assertTrue(r["ftp://example.org/x"]["status"].startswith("SKIPPED"))
        self.assertEqual(r["ihttp://x/"]["status"], "FAIL (not a web URL)")


class StateTest(unittest.TestCase):
    def test_failures_count_up_and_reset_and_last_ok_is_kept(self):
        fail = {"status": "FAIL (404)", "http": 404}
        s1 = cl.merge({"u": {"status": "OK", "last_ok": "2026-11-01", "failures": 0}}, {"u": fail}, "2026-11-08")
        self.assertEqual((s1["u"]["failures"], s1["u"]["last_ok"]), (1, "2026-11-01"))
        s2 = cl.merge(s1, {"u": fail}, "2026-11-15")
        self.assertEqual(s2["u"]["failures"], 2)
        s3 = cl.merge(s2, {"u": {"status": "OK", "http": 200}}, "2026-11-22")
        self.assertEqual((s3["u"]["failures"], s3["u"]["last_ok"]), (0, "2026-11-22"))

    def test_an_unchecked_url_keeps_its_record(self):
        old = {"status": "FAIL (404)", "failures": 3, "last_checked": "2026-11-01"}
        self.assertEqual(cl.merge({"u": old}, {"u": None}, "2026-11-08")["u"], old)

    def test_recently_ok_urls_are_not_due(self):
        previous = {"a": {"status": "OK", "last_checked": "2026-11-10"},
                    "b": {"status": "OK", "last_checked": "2026-10-01"},
                    "c": {"status": "FAIL (404)", "last_checked": "2026-11-17"}}
        urls = {u: {"full_download"} for u in "abcd"}
        self.assertEqual(sorted(cl.due(urls, previous, "2026-11-18", 28)), ["b", "c", "d"])
        self.assertEqual(sorted(cl.due(urls, previous, "2026-11-18", 0)), list("abcd"))

    def test_collect_reads_every_resource_kind(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.json").write_text(json.dumps({
                "full_download": [{"download_url": "http://a/1"}],
                "other_download": [{"access_url": "http://a/2"}, {"access_url": ""}],
                "example": [{"access_url": "http://a/1"}],
                "sparql": [{"access_url": "http://a/3"}]}))
            urls = cl.collect(d)
        self.assertEqual(sorted(urls), ["http://a/1", "http://a/2", "http://a/3"])
        self.assertEqual(urls["http://a/1"], {"full_download", "example"})


if __name__ == "__main__":
    unittest.main()
