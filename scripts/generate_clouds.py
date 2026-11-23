#!/usr/bin/env python3
"""Draw the LOD cloud diagrams (replaces GenerateClouds.java and UpdateClouds.java).

    scripts/generate_clouds.py --binary ./lod-cloud-draw --data lod-data.json --out out/2026-11-18

For the whole cloud and each domain it runs lod-cloud-draw, then converts the
SVG to a PNG (rsvg-convert) and, for the whole cloud, a small JPEG
(rsvg-convert, then ImageMagick). The settings files are in cloud-settings/. The canvas radius and
iteration count are those used by the old generate-clouds.sh. With --versions
it adds the new diagram to site/_data/versions.yml.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "cloud-settings"

# stem, canvas radius (None: the tool's default). Same values as generate-clouds.sh.
CLOUDS = [
    ("cross-domain-lod", 350),
    ("geography-lod", 300),
    ("government-lod", 400),
    ("life-sciences-lod", 600),
    ("linguistic-lod", 500),
    ("media-lod", 300),
    ("publications-lod", 400),
    ("social-networking-lod", 400),
    ("user-generated-lod", 300),
    ("lod-cloud", None),
]
ALGORITHMS = ["lbfgs", "sd"]
RELEASE_PREFIX = "clouds-"  # release tag = prefix + directory name
PNG_ZOOM = 3  # the old PNGs were 3x the SVG's width
JPEG_SCALE = 0.4  # of the PNG size


def draw(binary, data, stem, canvas, out, iterations):
    settings = SETTINGS / ("lod-cloud-settings.json" if stem == "lod-cloud" else stem + ".json")
    base = [str(binary), "--settings=" + str(settings), "-n", "10", "-i", str(iterations),
            "--ident=neighbour"]
    if canvas:
        base += ["-c", str(canvas)]
    base += [str(data), str(out / (stem + ".svg"))]
    # The run is deterministic, so retrying the same command is pointless. L-BFGS
    # can stop with "Search direction must be a descent direction" (media-lod does,
    # with the current data); steepest descent is slower but does not.
    for algorithm in ALGORITHMS:
        result = subprocess.run(base + ["--algorithm", algorithm], stdout=subprocess.DEVNULL)
        if result.returncode == 0:
            return
        print("%s: --algorithm %s failed (exit %d)" % (stem, algorithm, result.returncode),
              file=sys.stderr)
    raise SystemExit("%s: lod-cloud-draw failed with %s" % (stem, " and ".join(ALGORITHMS)))


def to_png(svg):
    subprocess.run(["rsvg-convert", "-z", str(PNG_ZOOM), "-b", "white", "-f", "png",
                    "-o", str(svg.with_suffix(".png")), str(svg)], check=True)


def to_jpeg(svg, jpeg):
    """The small JPEG, drawn from the SVG at JPEG_SCALE of the PNG size.

    Scaling down the full-size PNG with ImageMagick ran out of its pixel-cache
    limit on a runner (the policy differs between images), so the SVG is drawn
    small instead and ImageMagick only converts the small image.
    """
    convert = shutil.which("magick") or shutil.which("convert")
    if not convert:
        raise SystemExit("ImageMagick (magick or convert) is required for the JPEG")
    small = jpeg.with_suffix(".small.png")
    subprocess.run(["rsvg-convert", "-z", str(PNG_ZOOM * JPEG_SCALE), "-b", "white", "-f", "png",
                    "-o", str(small), str(svg)], check=True)
    try:
        subprocess.run([convert, str(small), "-quality", "85", str(jpeg)], check=True)
    finally:
        small.unlink(missing_ok=True)


def count_datasets(svg):
    """Circles in the SVG, as CountLinks.java did."""
    return len(re.findall(r"<circle", svg.read_text(encoding="utf-8")))


def add_version(versions_yml, date, datasets):
    """Add the new diagram at the top of _data/versions.yml (keeps the file's comments)."""
    text = versions_yml.read_text(encoding="utf-8")
    entry = ('- date: "%s"\n  release: %s%s\n  datasets: %d\n  colored:\n    png: lod-cloud.png\n'
             '    svg: lod-cloud.svg\n  graph: lod-data.json\n\n') % (date, RELEASE_PREFIX, date, datasets)
    if 'date: "%s"' % date in text:
        raise SystemExit("%s already has an entry for %s" % (versions_yml, date))
    first = text.index("\n- date:") + 1
    versions_yml.write_text(text[:first] + entry + text[first:], encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--binary", required=True, help="the lod-cloud-draw executable")
    ap.add_argument("--data", required=True, help="lod-data.json (old format; see export_site_data.py)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--iterations", type=int, default=5000)
    ap.add_argument("--only", action="append", metavar="STEM",
                    help="draw only this cloud (repeatable), e.g. media-lod")
    ap.add_argument("--date", help="with --versions: the date for the entry (yyyy-mm-dd)")
    ap.add_argument("--versions", type=Path, help="site/_data/versions.yml to add the new diagram to")
    args = ap.parse_args(argv)

    known = [stem for stem, _ in CLOUDS]
    for stem in args.only or []:
        if stem not in known:
            ap.error("unknown cloud %r (choose from %s)" % (stem, ", ".join(known)))
    if args.versions and not args.date:
        ap.error("--versions needs --date")
    if args.versions and args.only:
        ap.error("--versions needs the whole set; do not combine with --only")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(args.data).resolve()
    for stem, canvas in CLOUDS:
        if args.only and stem not in args.only:
            continue
        print("Drawing %s" % stem, file=sys.stderr)
        draw(Path(args.binary).resolve(), data, stem, canvas, out, args.iterations)
        to_png(out / (stem + ".svg"))
        if stem == "lod-cloud":
            to_jpeg(out / "lod-cloud.svg", out / "lod-cloud-sm.jpg")
    shutil.copy(data, out / "lod-data.json")
    # The settings used are published with the diagrams, as in the old sets
    for settings in sorted(SETTINGS.glob("*.json")):
        shutil.copy(settings, out / settings.name)

    if args.versions:
        n = count_datasets(out / "lod-cloud.svg")
        add_version(args.versions, args.date, n)
        print("Added %s (%d datasets) to %s" % (args.date, n, args.versions), file=sys.stderr)


if __name__ == "__main__":
    main()
