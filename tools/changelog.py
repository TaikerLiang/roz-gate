#!/usr/bin/env python3
"""Regenerate CHANGELOG.md from the GitHub releases.

    python3 tools/changelog.py            # rewrite CHANGELOG.md
    python3 tools/changelog.py --check    # exit 1 if CHANGELOG.md is stale

The release note is canonical; CHANGELOG.md is a copy, newest first, one
entry per release: its title, its link, its body verbatim. Never edit the
file by hand — edit the release (`gh release edit`) and rerun this.
Needs an authenticated `gh`. Dev-only tooling; see docs/releasing.md.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "CHANGELOG.md")

HEADER = (
    "# Changelog\n\n"
    "Generated from the GitHub releases (`gh release list`, `gh release view <tag>`), "
    "newest first, one entry per tag with its title and body verbatim. "
    "**The release note is canonical**; this file is a convenience copy — regenerate "
    "it, never edit it by hand. It exists because \"why does this rule exist\" is "
    "answered by the release that introduced it better than by any other document "
    "here.\n"
)


def gh(*args):
    out = subprocess.run(["gh"] + list(args), capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        sys.exit("changelog: gh %s failed: %s" % (" ".join(args), out.stderr.strip()))
    return json.loads(out.stdout)


def render():
    releases = gh("release", "list", "--limit", "1000", "--exclude-drafts",
                  "--json", "tagName,publishedAt")
    releases.sort(key=lambda r: r["publishedAt"], reverse=True)
    parts = [HEADER]
    for r in releases:
        v = gh("release", "view", r["tagName"], "--json", "name,tagName,publishedAt,url,body")
        title = v["name"] or v["tagName"]
        # a body edited in the web UI comes back with CRLF line ends
        body = v["body"].replace("\r\n", "\n").strip()
        parts.append("## %s — %s\n\n<%s>\n\n%s\n" % (title, v["publishedAt"][:10], v["url"], body))
    return "\n".join(parts) + "\n"  # the historical copy ends in a blank line


def main(argv):
    text = render()
    if "--check" in argv:
        with open(PATH, encoding="utf-8") as f:
            stale = f.read() != text
        print("CHANGELOG.md is %s" % ("stale — run tools/changelog.py" if stale else "current"))
        return 1 if stale else 0
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("CHANGELOG.md: %d releases" % text.count("\n## v"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
