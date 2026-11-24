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
        self.assertTrue(text.startswith("# comment\n\n- date: \"2026-11-18\"\n  release: clouds-2026-11-18\n  datasets: 1678\n"))
        self.assertLess(text.index("2026-11-18"), text.index("2026-06-15"))
        self.assertIn("graph: lod-data.json\n\n- date: \"2026-06-15\"", text)
        self.assertIn("colored:\n    webp: lod-cloud.webp\n    svg: lod-cloud.svg\n", text)

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


class PngZoomTest(unittest.TestCase):
    def zoom(self, width, height):
        with tempfile.TemporaryDirectory() as d:
            svg = Path(d) / "x.svg"
            svg.write_text('<svg\n    xmlns="http://www.w3.org/2000/svg" width="%s" height="%s">\n</svg>' % (width, height))
            return gc.png_zoom(svg)

    def test_a_finished_diagram_gets_the_normal_zoom(self):
        self.assertEqual(self.zoom(2200, 2242), gc.PNG_ZOOM)

    def test_a_huge_unconverged_one_is_scaled_down_to_the_pixel_limit(self):
        zoom = self.zoom(11000, 11000)
        self.assertLess(zoom, gc.PNG_ZOOM)
        self.assertLessEqual(11000 * 11000 * zoom ** 2, gc.MAX_PNG_PIXELS * 1.01)

    def test_unreadable_size_falls_back_to_the_normal_zoom(self):
        with tempfile.TemporaryDirectory() as d:
            svg = Path(d) / "x.svg"
            svg.write_text("<svg></svg>")
            self.assertEqual(gc.png_zoom(svg), gc.PNG_ZOOM)


class WebpTest(unittest.TestCase):
    def image(self, directory, name):
        from PIL import Image
        im = Image.new("RGB", (60, 40), "white")
        for x in range(60):
            im.putpixel((x, x % 40), (x * 4 % 256, 30, 200))   # thin coloured lines, like the links
        im.save(directory / name)
        return im

    def test_png_to_webp_to_png_is_pixel_identical(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            original = self.image(d, "a.png")
            gc.png_to_webp(d / "a.png", d / "a.webp")
            gc.webp_to_png(d / "a.webp", d / "b.png")
            with Image.open(d / "a.webp") as w:
                self.assertEqual(w.format, "WEBP")
            with Image.open(d / "b.png") as b:
                self.assertEqual(list(b.convert("RGB").getdata()), list(original.getdata()))

    def test_ensure_both_formats_makes_whichever_is_missing(self):
        sys.path.insert(0, str(Path(gc.__file__).resolve().parent))
        import fetch_clouds as fc
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.image(d, "only-png.png")
            self.image(d, "only-webp.png")
            gc.png_to_webp(d / "only-webp.png", d / "only-webp.webp")
            (d / "only-webp.png").unlink()
            self.assertEqual(fc.ensure_both_formats(d), 2)
            self.assertEqual(sorted(p.name for p in d.iterdir()),
                             ["only-png.png", "only-png.webp", "only-webp.png", "only-webp.webp"])
            self.assertEqual(fc.ensure_both_formats(d), 0)
