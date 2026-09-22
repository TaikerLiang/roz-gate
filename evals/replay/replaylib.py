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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Shared kit; case checkers keep importing it from here
# (`from replaylib import Run, Checker`).
from lib.checkkit import Checker  # noqa: E402,F401

MARKERS = ("**[", "✅ [")


# ---- session validity — shared by the runner (check.py path) and the
# drivers (F6): one classifier, or the two paths drift and the driver
# path scores a quota-exhausted session as data (codex review, PR #5).
def has_result_event(transcript):
    try:
        for line in open(transcript, encoding="utf-8"):
            if re.search(r'"type":\s*"result"', line):
                return True
    except OSError:
        pass
    return False


# Error strings the CLI emits as a RESULT when the session itself failed.
# Phrase-level on purpose: a patrol report legitimately discussing rate
# limits must not match; these are the runtime's own failure banners.
SESSION_ERR_RE = re.compile(
    r"(?i)hit your session limit|usage limit reached|rate.?limit.?error"
    r"|overloaded.?error|credit balance is too low|invalid x-api-key"
    r"|OAuth token has expired")


def session_error(transcript):
    """Result event present but the SESSION failed: the result is an
    error, its text is the limit/overload/auth family, or zero tokens
    were consumed. The no-result-event guard (codex review) caught the
    silent-death case; the live opus sweep hit the result-IS-an-error
    case — 45 iterations of 'the agent never ran' scored as valid FAILs.
    Returns the invalid_reason class, or None for a healthy session."""
    is_err, text, tok = False, "", 0
    try:
        for line in open(transcript, encoding="utf-8"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            u = (ev.get("message") or {}).get("usage") or {}
            tok += (u.get("input_tokens", 0) + u.get("output_tokens", 0)
                    + u.get("cache_creation_input_tokens", 0))
            if ev.get("type") == "result":
                is_err = bool(ev.get("is_error"))
                text = ev.get("result") or ""
    except OSError:
        return "transcript unreadable"
    if SESSION_ERR_RE.search(text):
        return "quota-exhausted"
    if is_err:
        return "session-error: %s" % text[:80]
    if tok == 0:
        return "zero-token session"
    return None


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
        return sorted(lab for lab in self.state()["issues"][issue]["labels"]
                      if lab.startswith("status:"))

    def has_label(self, issue, label):
        return label in self.state()["issues"][issue]["labels"]

    def issue_comment_bodies(self, issue):
        return [c.get("body", "") for c in
                self.state()["issues"][issue].get("comments", [])]

    def item_bound_reply(self, *needles):
        """A marker-prefixed reply whose body cites the ITEM it answers —
        one of the given needles (the item's URL fragment or distinctive
        fixture text). The A-group cases are about WHICH item was seen,
        so the assertion binds to the item, never just the issue."""
        return any(e.get("write")
                   and e.get("route") in ("pr-comment", "thread-reply",
                                          "thread-post-inline")
                   and e.get("body", "").startswith(MARKERS)
                   and any(n in e.get("body", "") for n in needles)
                   for e in self.journal())

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
        return len([line for line in out.splitlines() if line.strip()])

    def remote_file(self, ref, path):
        rc, out = self.git("show", "%s:%s" % (ref, path))
        return out if rc == 0 else None

    def remote_is_ancestor(self, ancestor_ref, ref):
        rc, _ = self.git("merge-base", "--is-ancestor",
                         self.git("rev-parse", ancestor_ref)[1].strip(), ref)
        return rc == 0

    def remote_commits_touching(self, ref, path):
        rc, out = self.git("log", ref, "--oneline", "--follow", "--", path)
        return len([line for line in out.splitlines() if line.strip()])

