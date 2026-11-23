#!/usr/bin/env python3
"""Check that every internal link and image in a built site resolves to a file.

    scripts/check_site_links.py _site [--baseurl /path] [--allow /path ...]

External links (http:, mailto:, ...) are not checked. Exit status is 1 if any
internal link is broken.
"""
import argparse
import html
import os
import re
import sys
import urllib.parse

EXTERNAL = re.compile(r"^(https?:|mailto:|ftp:|#|//)", re.I)


def resolves(site, page_dir, href, baseurl=""):
    path = urllib.parse.unquote(href)
    if baseurl and (path == baseurl or path.startswith(baseurl + "/")):
        path = path[len(baseurl):] or "/"
    base = site if path.startswith("/") else page_dir
    target = os.path.normpath(os.path.join(base, path.lstrip("/")))
    return os.path.isfile(target) or os.path.isfile(os.path.join(target, "index.html"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("site")
    ap.add_argument("--baseurl", default="", help="path the site is served under, e.g. /lod-cloud-site")
    ap.add_argument("--allow", nargs="*", default=[], help="paths that are known to be missing for now")
    args = ap.parse_args()

    checked, broken = 0, {}
    for root, _, files in os.walk(args.site):
        for name in files:
            if not name.endswith(".html"):
                continue
            page = os.path.join(root, name)
            with open(page, encoding="utf-8") as f:
                content = f.read()
            for href in re.findall(r'(?:href|src)="([^"]+)"', content):
                href = html.unescape(href)
                if EXTERNAL.match(href):
                    continue
                href = href.split("#")[0].split("?")[0]
                if not href or href in args.allow:
                    continue
                checked += 1
                if not resolves(args.site, root, href, args.baseurl.rstrip("/")):
                    broken.setdefault(href, []).append(os.path.relpath(page, args.site))
    for href, pages in sorted(broken.items()):
        print("broken link %s (%d page(s), e.g. %s)" % (href, len(pages), pages[0]))
    print("%d internal links checked, %d broken" % (checked, len(broken)), file=sys.stderr)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
