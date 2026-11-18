import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_clouds as gc

VERSIONS = '''# comment

- date: "2026-06-15"
  datasets: 1360
  graph: lod-data.json

- date: "2026-04-09"
  datasets: 1358
'''


class VersionsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "versions.yml"
        self.path.write_text(VERSIONS, encoding="utf-8")

    def tearDown(self):
        self.dir.cleanup()

    def test_new_entry_goes_first_and_the_header_is_kept(self):
        gc.add_version(self.path, "2026-11-18", 1678)
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# comment\n\n- date: \"2026-11-18\"\n  datasets: 1678\n"))
        self.assertLess(text.index("2026-11-18"), text.index("2026-06-15"))
        self.assertIn("graph: lod-data.json\n\n- date: \"2026-06-15\"", text)

    def test_same_date_twice_is_an_error(self):
        gc.add_version(self.path, "2026-11-18", 1678)
        with self.assertRaises(SystemExit):
            gc.add_version(self.path, "2026-11-18", 1678)


class CountTest(unittest.TestCase):
    def test_counts_circles(self):
        with tempfile.TemporaryDirectory() as d:
            svg = Path(d) / "a.svg"
            svg.write_text('<svg><circle r="1"/><line/><circle r="2"/></svg>', encoding="utf-8")
            self.assertEqual(gc.count_datasets(svg), 2)


class CloudListTest(unittest.TestCase):
    def test_every_cloud_has_a_settings_file(self):
        for stem, _ in gc.CLOUDS:
            name = "lod-cloud-settings.json" if stem == "lod-cloud" else stem + ".json"
            self.assertTrue((gc.SETTINGS / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
