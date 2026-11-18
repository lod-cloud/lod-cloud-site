#!/usr/bin/env python3
"""Upload the old diagram sets (src/main/webapp/versions/<dir>/) as GitHub releases.

    scripts/upload_historical_versions.py                 # dry run: list what would be done
    scripts/upload_historical_versions.py --execute       # create the releases
    scripts/upload_historical_versions.py --update-versions site/_data/versions.yml

Each directory becomes a release `clouds-<dir>` (the same name the diagram
workflow uses) with its files as assets, marked "not latest". Directories whose
release already exists are skipped, so an interrupted run can be repeated.
`--update-versions` adds `release: clouds-<dir>` to the entries in versions.yml.

Needs the real files, not Git LFS pointers: run `git lfs pull` first. Releases
are created on the repository's default branch (the tag points at its head).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "src" / "main" / "webapp" / "versions"
RELEASE_PREFIX = "clouds-"  # keep in sync with generate_clouds.py
LFS_POINTER = b"version https://git-lfs.github.com/spec/"


def version_dirs(root):
    """Directories named like a date (the old site wrote some as yyyy-dd-mm); `latest` is a copy."""
    return sorted(p for p in Path(root).iterdir()
                  if p.is_dir() and not p.is_symlink() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))


def files_of(directory):
    files = sorted(p for p in directory.iterdir() if p.is_file())
    for f in files:
        with f.open("rb") as fh:
            if fh.read(len(LFS_POINTER)) == LFS_POINTER:
                raise SystemExit("%s is a Git LFS pointer; run `git lfs pull` first" % f)
        if f.stat().st_size == 0:
            raise SystemExit("%s is empty; GitHub does not accept empty assets" % f)
    return files


def release_exists(repo, tag):
    return subprocess.run(["gh", "release", "view", tag, "-R", repo],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def upload(repo, directory):
    tag = RELEASE_PREFIX + directory.name
    cmd = ["gh", "release", "create", tag, "-R", repo, "--latest=false",
           "--title", "LOD Cloud diagram " + directory.name,
           "--notes", "Imported from versions/%s of the previous lod-cloud.net site." % directory.name]
    subprocess.run(cmd + [str(f) for f in files_of(directory)], check=True)


def add_release_keys(versions_yml, existing_dirs):
    """Add `release:` after the date (or dir) line of each entry that has files."""
    lines = versions_yml.read_text(encoding="utf-8").split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'- date: "([^"]+)"', line)
        if not m:
            out.append(line)
            i += 1
            continue
        block = [line]
        i += 1
        while i < len(lines) and lines[i].startswith("  "):
            block.append(lines[i])
            i += 1
        d = next((re.match(r'  dir: "?([^"\s]+)"?', b).group(1) for b in block if re.match(r"  dir:", b)), m.group(1))
        if d in existing_dirs and not any(b.startswith("  release:") for b in block):
            at = 2 if len(block) > 1 and block[1].startswith("  dir:") else 1
            block.insert(at, "  release: " + RELEASE_PREFIX + d)
        out.extend(block)
    versions_yml.write_text("\n".join(out), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--versions-dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--repo", default="lod-cloud/lod-cloud-site")
    ap.add_argument("--execute", action="store_true", help="create the releases (default: dry run)")
    ap.add_argument("--only", action="append", metavar="DIR", help="only this directory (repeatable)")
    ap.add_argument("--update-versions", type=Path, metavar="versions.yml")
    args = ap.parse_args(argv)

    dirs = version_dirs(args.versions_dir)
    if args.only:
        dirs = [d for d in dirs if d.name in args.only]
    if args.update_versions:
        add_release_keys(args.update_versions, {d.name for d in version_dirs(args.versions_dir)})
        print("Updated", args.update_versions, file=sys.stderr)
        return

    total = 0
    for d in dirs:
        files = files_of(d)
        size = sum(f.stat().st_size for f in files)
        total += size
        if args.execute and release_exists(args.repo, RELEASE_PREFIX + d.name):
            print("%-12s exists, skipped" % d.name, file=sys.stderr)
            continue
        print("%-12s %2d files %7.1f MB  -> release %s%s" % (d.name, len(files), size / 1e6, RELEASE_PREFIX, d.name),
              file=sys.stderr)
        if args.execute:
            upload(args.repo, d)
    print("%d directories, %.0f MB%s" % (len(dirs), total / 1e6, "" if args.execute else " (dry run; use --execute)"),
          file=sys.stderr)


if __name__ == "__main__":
    main()
