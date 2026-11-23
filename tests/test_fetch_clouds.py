import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_clouds as fc  # noqa: E402

YML = '''# comment
#   release  not a row

- date: "2026-11-23"
  release: clouds-2026-11-23
  datasets: 1368

- date: "2026-06-15"
  release: clouds-2026-06-15

- date: "2018-08-28"
  datasets: 1
'''


class CurrentReleaseTest(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "v.yml"
            p.write_text(text)
            return fc.current_release(p)

    def test_newest_row_with_a_release(self):
        self.assertEqual(self.read(YML), "clouds-2026-11-23")

    def test_a_newer_row_without_a_release_is_skipped_and_order_does_not_matter(self):
        self.assertEqual(self.read('- date: "2027-01-01"\n  datasets: 3\n\n' + YML), "clouds-2026-11-23")
        self.assertEqual(self.read('- date: "2026-06-15"\n  release: a\n\n- date: "2026-11-23"\n  release: b\n'), "b")

    def test_the_real_file_has_one(self):
        self.assertRegex(fc.current_release(fc.ROOT / "site" / "_data" / "versions.yml"), r"^clouds-\d{4}-\d\d-\d\d$")

    def test_none_is_an_error(self):
        with self.assertRaises(SystemExit):
            self.read('- date: "2018-08-28"\n  datasets: 1\n')


class BaseurlLinksTest(unittest.TestCase):
    def test_links_under_the_baseurl_resolve_against_the_site_root(self):
        import check_site_links as cs
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "dataset" / "x").mkdir(parents=True)
            (Path(d) / "dataset" / "x" / "index.html").write_text("x")
            self.assertTrue(cs.resolves(d, d, "/lod-cloud-site/dataset/x/", "/lod-cloud-site"))
            self.assertFalse(cs.resolves(d, d, "/lod-cloud-site/dataset/y/", "/lod-cloud-site"))
            self.assertTrue(cs.resolves(d, d, "/dataset/x/"))
            self.assertFalse(cs.resolves(d, d, "/lod-cloud-site/dataset/x/"))
