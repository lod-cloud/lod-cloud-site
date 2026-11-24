#!/usr/bin/env python3
"""Download the current diagram set into the built site.

    scripts/fetch_clouds.py _site/clouds

The newest row of site/_data/versions.yml names a GitHub release (`release: clouds-<date>`,
made by the Clouds workflow). Its files are what the site serves under /clouds/: the home
page and the domain pages show them, and the SVGs are interactive. Release downloads cannot
do this themselves, because GitHub serves them as attachments. Needs the `gh` CLI (GH_TOKEN).

The site has both formats of each diagram under /clouds/: the pages use the WebP (half the size of
the PNG, the same pixels), and the PNG stays at its old address, which many pages link to. A release
made since #117 has only the WebP, an older one only the PNG; the missing one is made here.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_clouds as gc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def current_release(versions_yml):
    """The release of the newest row that has one (the file is newest first)."""
    best = None
    for block in re.split(r"(?m)^- ", Path(versions_yml).read_text(encoding="utf-8"))[1:]:
        date = re.match(r'date: "?([^"\s]+)', block)
        release = re.search(r"(?m)^\s+release: (\S+)", block)
        if date and release and (best is None or date.group(1) > best[0]):
            best = (date.group(1), release.group(1))
    if best is None:
        raise SystemExit("No row with a release in %s" % versions_yml)
    return best[1]


def ensure_both_formats(directory):
    """For every diagram, the PNG if only the WebP is there, and the WebP if only the PNG is. Returns the number made."""
    directory = Path(directory)
    made = 0
    for webp in sorted(directory.glob("*.webp")):
        png = webp.with_suffix(".png")
        if not png.exists():
            gc.webp_to_png(webp, png)
            made += 1
    for png in sorted(directory.glob("*.png")):
        webp = png.with_suffix(".webp")
        if not webp.exists():
            gc.png_to_webp(png, webp)
            made += 1
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="directory to download into (created)")
    ap.add_argument("--versions", default=str(ROOT / "site" / "_data" / "versions.yml"))
    ap.add_argument("--repo", default="lod-cloud/lod-cloud-site")
    args = ap.parse_args(argv)

    tag = current_release(args.versions)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gh", "release", "download", tag, "--repo", args.repo, "--dir", str(out), "--clobber"], check=True)
    files = sorted(p.name for p in out.iterdir())
    for needed in ("lod-cloud.svg", "lod-cloud-sm.jpg"):
        if needed not in files:
            raise SystemExit("%s does not contain %s" % (tag, needed))
    if "lod-cloud.webp" not in files and "lod-cloud.png" not in files:
        raise SystemExit("%s has neither lod-cloud.webp nor lod-cloud.png" % tag)
    made = ensure_both_formats(out)
    print("Release %s: %d files in %s (%d images made from the other format)" % (tag, len(files), out, made),
          file=sys.stderr)


if __name__ == "__main__":
    main()
