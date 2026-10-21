#!/usr/bin/env python3
"""Regenerate CHANGELOG.md from the GitHub releases.

    python3 tools/changelog.py            # rewrite CHANGELOG.md
    python3 tools/changelog.py --check    # exit 1 if CHANGELOG.md is stale
    python3 tools/changelog.py --pending v<x.y.z> notes.md ["<title>"]
                                          # the release PR: rewrite, plus the
                                          # unpublished release on top

The release note is canonical; CHANGELOG.md is a copy, newest first, one
entry per release: its title, its link, its body verbatim. Never edit the
file by hand — edit the release (`gh release edit`) and rerun this.
`--pending` lets the release PR carry its own entry before the release
exists: the title (default: the tag), today's date, the notes file as
body — the same title and file the release is then published with. Any later difference (a date, an
edited note) is corrected by the next run, which reads the releases only.
Needs an authenticated `gh`. Dev-only tooling; see docs/releasing.md.
"""

import datetime
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


def pending_entry(tag, notes_path, title=None):
    """The entry the release `tag` will have once published from `notes_path`."""
    published = gh("release", "list", "--limit", "1000", "--exclude-drafts",
                   "--json", "tagName")
    if any(r["tagName"] == tag for r in published):
        sys.exit("changelog: %s is already published — run without --pending" % tag)
    url = "%s/releases/tag/%s" % (gh("repo", "view", "--json", "url")["url"], tag)
    with open(notes_path, encoding="utf-8") as f:
        body = f.read().replace("\r\n", "\n").strip()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return "## %s — %s\n\n<%s>\n\n%s\n" % (title or tag, today, url, body)


def main(argv):
    text = render()
    if "--pending" in argv:
        i = argv.index("--pending")
        if len(argv) < i + 3:
            sys.exit("changelog: --pending needs <tag> <notes-file>")
        head, rest = text[:len(HEADER)], text[len(HEADER):]
        title = argv[i + 3] if len(argv) > i + 3 and not argv[i + 3].startswith("--") else None
        text = head + "\n" + pending_entry(argv[i + 1], argv[i + 2], title) + rest
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
