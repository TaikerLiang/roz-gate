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

import hashlib
import json
import os
import re
import subprocess
import sys

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(S))
sys.path.insert(0, os.path.dirname(S))
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


# The SUT's environment, shared by every `claude -p` a SUT runs (runner,
# drivers, the judgment tier). Headless Claude Code waits only 600 s for
# background tasks and then terminates the session — a next-stage that
# dispatches its seats in the background was cut off mid-stage and still
# ended on a result event (judgment F-54, 2026-09-28). 0 = wait for them;
# the fixture's own timeout is the bound.
SUT_ENV = {"CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"}

# What the runtime (or our own timeout) writes to the SUT's stderr when the
# session was cut short. A cut-short session can still carry result events
# — one per turn the main agent finished — so has_result_event() cannot
# see it; stderr can.
TIMEOUT_NOTE = "roz-gate: SUT killed at its %ds timeout"
CUT_SHORT_RE = re.compile(
    r"Background tasks still running after \d+s; terminating"
    r"|roz-gate: SUT killed at its \d+s timeout")


def cut_short(stderr_log):
    """The session was terminated before it finished — background tasks
    killed by the runtime, or our timeout. Returns the invalid_reason, or
    None. Invalid, never red: an unfinished session scored as data reads as
    a model that surfaced nothing (F-54: recall 0/1 from an empty surface)."""
    try:
        text = open(stderr_log, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = CUT_SHORT_RE.search(text)
    return "session cut short: %s" % m.group(0) if m else None


def iteration_done(rdir):
    """Resume skips an iteration only when its result.json measured the
    SUT. A quota-exhausted result is the harness stopping mid-sweep — the
    banner says "resume after reset" — so it re-runs; every other result,
    valid or invalid, stands (the judgment k=2 resume on 1.17.0 printed
    `skip F-63 run-2 (done)` over a quota banner)."""
    try:
        with open(os.path.join(rdir, "result.json"), encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, ValueError):
        return False
    if not isinstance(r, dict):   # valid JSON that is not a result (codex review, PR #35)
        return False
    return r.get("invalid_reason") != "quota-exhausted"


# ---- the case as scored — stamped into every result.json (#190) -----------
# A verdict depends on the checker (or the driver), the case's metadata, the
# seed and the forge state. A run carries the fingerprint of the case that
# scored it, so a case edited after its baseline leaves those runs STALE
# in report.json instead of silently current: C5's 4/5 of 2026-09-15 was
# scored by the pre-#97 checker and read as the current case for a month.
def case_fingerprint(cdir):
    """sha256 (16 hex) over check.py — or the driver case.json names —
    case.json, seed.sh and state.json; an absent file hashes as absent. A
    case that depends on shared files (`"fixture"` in case.json: a path or a
    list of paths relative to evals/replay — fixture trees the seed copies,
    the frame the checker imports, #199) hashes each of them too, every file
    under a directory: the seed is the recipe, the tree is the ingredients,
    the frame is most of the verdict."""
    try:
        with open(os.path.join(cdir, "case.json"), encoding="utf-8") as f:
            meta = json.load(f) or {}
    except (OSError, ValueError):
        meta = {}
    driver, fixture = meta.get("driver") or "", meta.get("fixture") or ""
    h = hashlib.sha256()
    for name in (driver or "check.py", "case.json", "seed.sh", "state.json"):
        try:
            with open(os.path.join(cdir, name), "rb") as f:
                data = f.read()
        except OSError:
            data = b"<absent>"
        h.update(name.encode("utf-8") + b"\0" + data + b"\0")
    deps = [fixture] if isinstance(fixture, str) else list(fixture or [])
    for dep in [d for d in deps if d]:
        top = os.path.join(S, dep)
        paths = [top] if os.path.isfile(top) else []
        if not paths:
            for dirpath, dirs, files in os.walk(top):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                paths += [os.path.join(dirpath, name) for name in sorted(files)]
        for path in paths:
            rel = os.path.relpath(path, S).replace(os.sep, "/")
            with open(path, "rb") as f:
                h.update(rel.encode("utf-8") + b"\0" + f.read() + b"\0")
    return h.hexdigest()[:16]


def brief_sha256(path):
    """sha256 (full hex) of a file as it is on disk — the QA brief the SUT
    loaded (#199): stamped into every result.json beside `case_fp` and
    `plugin_sha`, read back from the plugin dir the session ran, never from
    the variant's source file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---- the checker's INVALID exit (#199) -------------------------------------
# A checker may find that the iteration never exercised what it scores — the
# QA dispatch never ran, the main agent dropped the seat's work before it
# was observable. That is a verdict about the harness, not the rule: exit 3
# with one `INVALID <reason>` line, and the runner records the iteration as
# invalid (never red, never green) with that reason.
CHECK_INVALID = 3


def invalid(reason):
    print("INVALID %s" % reason)
    sys.exit(CHECK_INVALID)


def invalid_reason(check_log):
    """The reason a checker's INVALID line gave, or a generic one."""
    try:
        for line in open(check_log, encoding="utf-8"):
            if line.startswith("INVALID "):
                return "checker: " + line[len("INVALID "):].strip()
    except OSError:
        pass
    return "checker: invalid without a reason"


def plugin_sha():
    """The checkout's short HEAD, or "" outside a checkout."""
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


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

    def remote_heads(self):
        """Every branch on the sandbox's bare remote, by short name."""
        rc, out = self.git("for-each-ref", "--format=%(refname:short)", "refs/heads/")
        return [ln.strip() for ln in out.splitlines() if ln.strip()] if rc == 0 else None

    def signal(self, **values):
        """Add to attempts.json — the report's extra columns (D2's pattern):
        informational, never a verdict."""
        path = os.path.join(self.dir, "attempts.json")
        try:
            with open(path, encoding="utf-8") as f:
                cur = json.load(f)
        except (OSError, ValueError):
            cur = {}
        if not isinstance(cur, dict):
            cur = {}
        cur.update(values)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cur, f)

    def shadow_branch(self, bindings, template=None):
        """#135 shadow comparison: for each (kind, issue) → the name the
        command bound (None when it bound nothing), ask hooks/branch_names
        what Lookup over the remote's final heads says. Agreement: ONE match
        equal to the bound name, or NO_MATCH when nothing was bound;
        MULTIPLE_SEQ agrees when the bound name is the highest {seq}.
        Writes `shadow_branch_mismatch` (a count) and
        `shadow_branch_detail`; a signal, never a fail — the exit from
        shadow mode is evals/CONTRIBUTING.md § Shadow signals."""
        sys.path.insert(0, os.path.join(ROOT, "hooks"))
        import branch_names as bn  # noqa: E402
        heads = self.remote_heads()
        snap = (bn.snapshot_from_heads(heads) if heads is not None
                else {"status": "unknown", "reason": "no remote", "heads": []})
        detail, mismatches = {}, 0
        for (kind, n), bound in bindings.items():
            m = bn.match_heads(snap, template, kind=kind, n=n)
            names = [x["branch"] for x in m["matches"]]
            if m["outcome"] == "ONE":
                agree = bound == names[0]
            elif m["outcome"] == "NO_MATCH":
                agree = bound is None
            elif m["outcome"] == "MULTIPLE_SEQ":
                agree = bound == max(m["matches"], key=lambda x: x["seq"] or 0)["branch"]
            else:
                agree = False
            detail["%s/%s" % (kind, n)] = {"bound": bound, "outcome": m["outcome"],
                                           "matches": names, "agree": agree}
            mismatches += 0 if agree else 1
        self.signal(shadow_branch_mismatch=mismatches, shadow_branch_detail=detail)
        return mismatches

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

