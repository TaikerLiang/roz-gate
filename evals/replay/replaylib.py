"""Shared library for the replay tier — the ONE place that parses the
journal, the forge state, the transcript, and run results. Checkers import
this; the runner imports this; nothing re-implements the parsing (three
drifting copies of the same JSON walk is the B3 defect class).

Checker contract: a per-case `check.py` runs with env RUN_DIR (the
iteration's artifact dir), BARE (the sandbox's bare remote), WORK (kept
for interface compatibility; the sandbox is discarded after the run), and
ROOT (the plugin root). It exits 0 iff every expectation held. Assertions
derive from the ledger case and the owning prose, cited via `# source:`
comments — the runner refuses an uncited checker.
"""

import json
import os
import re
import subprocess
import sys

MARKERS = ("**[", "✅ [")


class Run:
    """Read-side view of one replay iteration's artifacts."""

    def __init__(self, rundir=None):
        self.dir = rundir or os.environ["RUN_DIR"]
        self.bare = os.environ.get("BARE", "")

    # ---- forge journal / state ------------------------------------------
    def journal(self):
        path = os.path.join(self.dir, "forge", "journal.jsonl")
        out = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
        except OSError:
            pass
        return out

    def state(self):
        with open(os.path.join(self.dir, "forge", "state.json"),
                  encoding="utf-8") as f:
            return json.load(f)

    def journal_writes(self, route_re="."):
        return sum(1 for e in self.journal()
                   if e.get("write") and re.search(route_re, e.get("route", "")))

    def marker_replies(self, routes=("pr-comment", "thread-reply")):
        return sum(1 for e in self.journal()
                   if e.get("write") and e.get("route") in routes
                   and e.get("body", "").startswith(MARKERS))

    def unmarked_comment_writes(self):
        return sum(1 for e in self.journal()
                   if e.get("write")
                   and e.get("route") in ("pr-comment", "thread-reply", "issue-comment")
                   and not e.get("body", "").startswith(MARKERS))

    def status_labels(self, issue):
        return sorted(l for l in self.state()["issues"][issue]["labels"]
                      if l.startswith("status:"))

    def has_label(self, issue, label):
        return label in self.state()["issues"][issue]["labels"]

    def issue_comment_bodies(self, issue):
        return [c.get("body", "") for c in
                self.state()["issues"][issue].get("comments", [])]

    def route_taken(self, issue):
        """The A-family predicate: the pass acted on the unheard item —
        the review-answers lock was taken on the issue, or a
        marker-prefixed reply landed on a CR channel."""
        lock = any(e.get("route") == "issue-edit" and e.get("issue") == issue
                   and any("processing" in a for a in e.get("add", []))
                   for e in self.journal())
        return lock or self.marker_replies(
            ("pr-comment", "thread-reply", "thread-post-inline")) > 0

    # ---- transcript ------------------------------------------------------
    def transcript_events(self):
        path = os.path.join(self.dir, "transcript.jsonl")
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        yield json.loads(line)
                    except ValueError:
                        pass
        except OSError:
            return

    def tool_uses(self, names=None):
        for ev in self.transcript_events():
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" \
                        and (names is None or b.get("name") in names):
                    yield b

    def dispatch_count(self):
        return sum(1 for _ in self.tool_uses(("Task", "Agent")))

    def result_text(self):
        last = ""
        for ev in self.transcript_events():
            if ev.get("type") == "result":
                last = ev.get("result") or ""
        return last

    # ---- sandbox remote --------------------------------------------------
    def git(self, *args):
        out = subprocess.run(["git", "-C", self.bare, *args],
                             capture_output=True, text=True)
        return out.returncode, out.stdout

    def remote_ref_count(self):
        rc, out = self.git("for-each-ref")
        return len([l for l in out.splitlines() if l.strip()])

    def remote_file(self, ref, path):
        rc, out = self.git("show", "%s:%s" % (ref, path))
        return out if rc == 0 else None

    def remote_is_ancestor(self, ancestor_ref, ref):
        rc, _ = self.git("merge-base", "--is-ancestor",
                         self.git("rev-parse", ancestor_ref)[1].strip(), ref)
        return rc == 0

    def remote_commits_touching(self, ref, path):
        rc, out = self.git("log", ref, "--oneline", "--follow", "--", path)
        return len([l for l in out.splitlines() if l.strip()])


class Checker:
    """Named expectations; prints ok/FAIL lines; exit 0 iff all held."""

    def __init__(self):
        self.fails = 0

    def expect(self, source, desc, cond):
        if callable(cond):
            try:
                cond = bool(cond())
            except Exception as exc:  # a broken probe is a failed check
                print("FAIL %s  [probe error: %s] [source: %s]"
                      % (desc, exc, source))
                self.fails += 1
                return
        if cond:
            print("ok   %s" % desc)
        else:
            print("FAIL %s  [source: %s]" % (desc, source))
            self.fails += 1

    def finish(self):
        sys.exit(0 if self.fails == 0 else 1)
