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
import shutil
import subprocess
import sys
import tempfile

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

# The SUT's configuration scope, on every `claude -p` a SUT runs (#307).
# Without it a session loads the operator's user scope: their plugins (a
# second roz-gate from the installed copy, telegram), hooks, skills, MCP
# servers (claude.ai connectors, a connected messaging server) and
# ~/.claude/CLAUDE.md. Measured on 2.1.325: `--setting-sources
# project,local` drops the user plugins, skills, commands, hooks, MCP
# servers and the user CLAUDE.md; `--strict-mcp-config` (with no
# --mcp-config) drops every MCP server on its own, a project `.mcp.json`
# included. The plugin under test still loads from --plugin-dir, hooks
# and all. `--bare` would need an API key.
SUT_ISOLATION_ARGS = ["--setting-sources", "project,local", "--strict-mcp-config"]


def init_events(transcript):
    """Every system/init event in a transcript (one per session start)."""
    out = []
    try:
        for line in open(transcript, encoding="utf-8"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                out.append(ev)
    except OSError:
        pass
    return out


def session_plugins(transcript):
    """The effective plugin list of the session — its first init event's
    `plugins`, as the runtime reported them — or None without one."""
    inits = init_events(transcript)
    return inits[0].get("plugins") or [] if inits else None


def _builtin(p):
    return str(p.get("name", "")).startswith("cc-plugin-") and \
        str(p.get("source", "")).endswith("@builtin")


def isolation_breach(transcript, plugin_dir):
    """Why this session is not a clean measurement, or None (#307). Clean:
    every init event lists the runtime's built-ins (`cc-plugin-*@builtin`)
    and, when `plugin_dir` is given, exactly one roz-gate loaded from it —
    no other plugin, no MCP server. With no init event the isolation is
    unverifiable, which is a breach too: it is never assumed."""
    inits = init_events(transcript)
    if not inits:
        return "isolation unverifiable — no init event in the transcript (#307)"
    want = os.path.realpath(plugin_dir) if plugin_dir else None
    for ev in inits:
        rest = [p for p in ev.get("plugins") or [] if not _builtin(p)]
        roz = [p for p in rest if p.get("name") == "roz-gate"]
        other = [p for p in rest if p.get("name") != "roz-gate"]
        if other:
            return "user-scope plugin(s) in the SUT session: %s (#307)" % ", ".join(
                "%s (%s)" % (p.get("name"), p.get("source")) for p in other)
        if len(roz) > 1:
            return "roz-gate loaded %d times: %s (#307)" % (
                len(roz), ", ".join(str(p.get("path")) for p in roz))
        if roz and want is None:
            return "roz-gate loaded in a no-plugin session, from %s (#307)" % roz[0].get("path")
        if want is not None and (not roz or os.path.realpath(str(roz[0].get("path"))) != want):
            return "roz-gate not loaded from --plugin-dir %s (got %s) (#307)" % (
                plugin_dir, roz[0].get("path") if roz else "none")
        mcp = ev.get("mcp_servers") or []
        if mcp:
            return "MCP server(s) in the SUT session: %s (#307)" % ", ".join(
                str(m.get("name")) for m in mcp)
    return None

PATH_FILE_RE = re.compile(r"(?:^|/)references/(next-stage-path-(?:a|b|b2|c)\.md)$")


def path_files_read(transcript):
    """The `next-stage` path files a session Read (#279): the distinct
    `references/next-stage-path-*.md` names in the order first Read, seats
    included, and their count — `path_files_read` is a signal (a count),
    `path_files_read_detail` a detail. A Read counts only once its
    tool_result came back without `is_error`: a failed or unanswered Read
    loaded nothing (codex review, PR #316). A report, never a verdict."""
    names, asked = [], {}
    try:
        for line in open(transcript, encoding="utf-8"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            for b in (ev.get("message") or {}).get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b.get("name") == "Read":
                    m = PATH_FILE_RE.search(str((b.get("input") or {}).get("file_path", "")))
                    if m:
                        asked[b.get("id")] = m.group(1)
                elif b.get("type") == "tool_result" and not b.get("is_error"):
                    name = asked.get(b.get("tool_use_id"))
                    if name and name not in names:
                        names.append(name)
    except OSError:
        pass
    return {"path_files_read": len(names), "path_files_read_detail": names}

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
# Files every case's sandbox is built from, hashed into every case's
# fingerprint (#293). Explicit data: `lib/seed-common.sh` seeds the base all
# 62 cases start from, and until this list existed an edit to it changed
# every sandbox and marked no recorded result stale. Paths relative to
# evals/replay. A new shared seed input is added here by hand — never
# discovered by reading a seed's shell text.
SHARED_FINGERPRINT_INPUTS = ("lib/seed-common.sh",)


def case_fingerprint(cdir, shared=None):
    """sha256 (16 hex) over check.py — or the driver case.json names —
    case.json, seed.sh and state.json; an absent file hashes as absent;
    then every SHARED_FINGERPRINT_INPUTS file (`shared` overrides the list
    for the harness). A
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
    for dep in (SHARED_FINGERPRINT_INPUTS if shared is None else shared):
        try:
            with open(os.path.join(S, dep), "rb") as f:
                data = f.read()
        except OSError:
            data = b"<absent>"
        h.update(b"shared:" + dep.encode("utf-8") + b"\0" + data + b"\0")
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


# The token counter's version, stamped into every `tokens` (#308). Version 1
# (no `counter` key) summed message.usage over every stream event: an API
# call streams one assistant event per content block, each repeating the
# call's usage with a partial output count — input double-counted, output
# about 40x low. Results counted by different versions are never summed or
# compared; the report leaves the old ones out of the totals and counts them.
TOKEN_COUNTER = 2


def _process_tokens(transcript):
    """One process's (in, out, cache_read), in = input + cache creation.
    The last result event's modelUsage is the process's running total, its
    seats included; without it the result events' usage (one per turn, the
    main thread) is summed; with no result event at all, each message once
    at its last usage."""
    results, msgs = [], {}
    try:
        for line in open(transcript, encoding="utf-8"):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "result":
                results.append(ev)
            elif ev.get("type") == "assistant":
                m = ev.get("message") or {}
                if m.get("usage"):
                    msgs[m.get("id") or len(msgs)] = m["usage"]
    except OSError:
        return 0, 0, 0
    mu = next((r["modelUsage"] for r in reversed(results) if r.get("modelUsage")), None)
    if mu:
        return (sum(v.get("inputTokens", 0) + v.get("cacheCreationInputTokens", 0)
                    for v in mu.values()),
                sum(v.get("outputTokens", 0) for v in mu.values()),
                sum(v.get("cacheReadInputTokens", 0) for v in mu.values()))
    usages = [r.get("usage") or {} for r in results] if results else list(msgs.values())
    return (sum(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                for u in usages),
            sum(u.get("output_tokens", 0) for u in usages),
            sum(u.get("cache_read_input_tokens", 0) for u in usages))


def session_tokens(transcripts):
    """A session's tokens over its transcripts — one per `claude -p`
    process, so a resumed session (F6's turns) sums them (#308)."""
    tin = tout = tcr = 0
    for t in transcripts:
        i, o, c = _process_tokens(t)
        tin, tout, tcr = tin + i, tout + o, tcr + c
    return {"in": tin, "out": tout, "cache_read": tcr, "counter": TOKEN_COUNTER}


def current_counter(tokens):
    """True when a run's `tokens` were counted by this TOKEN_COUNTER."""
    return isinstance(tokens, dict) and tokens.get("counter") == TOKEN_COUNTER


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

    # The acts by which a command binds a branch name, read from what it did
    # (codex review, PR #254 — never a fixture constant):
    #   create — CR-OPEN's head, a `git push` refspec's destination, the
    #            `git worktree add` path under roz-gate/wt/, `checkout -b`.
    #   find   — CR-FIND's head (`--head X`, or `head=` in an API query).
    _PUSH = re.compile(r"\bgit\b[^|;&\n]*\bpush\b([^|;&\n]*)")
    _WT = re.compile(r"roz-gate/wt/(\S+)")
    _CO = re.compile(r"\bgit\b[^|;&\n]*\b(?:checkout|switch)\s+-[bBcC]\s+(\S+)")

    @staticmethod
    def _ref(tok):
        tok = tok.strip("'\"`")
        for pre in ("refs/remotes/origin/", "refs/heads/", "origin/"):
            if tok.startswith(pre):
                tok = tok[len(pre):]
        return tok.split(":")[-1] if ":" in tok else tok

    def observed_bindings(self, acts=("create", "find")):
        """Every branch name the run bound by one of `acts`."""
        names = set()
        for e in self.journal():
            argv = [str(a) for a in e.get("argv") or []]
            if "create" in acts and e.get("route") == "pr-create" and e.get("head"):
                names.add(self._ref(e["head"]))
            if "find" in acts:
                for k, a in enumerate(argv):
                    if a == "--head" and k + 1 < len(argv):
                        names.add(self._ref(argv[k + 1]))
                    for m in re.finditer(r"[?&]head=([^&\s]+)", a):
                        names.add(self._ref(m.group(1).split(":")[-1]))
        if "create" in acts:
            for u in self.tool_uses(("Bash",)):
                cmd = (u.get("input") or {}).get("command", "")
                for m in self._PUSH.finditer(cmd):
                    toks = [t for t in m.group(1).split() if not t.startswith("-")]
                    names.update(self._ref(t) for t in toks[1:])     # toks[0]: the remote
                names.update(self._ref(m.group(1)) for m in self._WT.finditer(cmd))
                names.update(self._ref(m.group(1)) for m in self._CO.finditer(cmd))
        return names

    def shadow_branch(self, keys, template=None, acts=("create", "find")):
        """#135 shadow comparison: for each (kind, issue) in `keys`, the names
        the run itself bound (observed_bindings, filtered to that kind and
        issue under `template`) against what hooks/branch_names' Lookup over
        the remote's final heads would bind (ONE → it; MULTIPLE_SEQ → the
        highest {seq}; NO_MATCH → nothing). Agreement: the observed set is
        exactly the resolver's choice, or both are empty. Writes
        `shadow_branch_mismatch` (a count) and `shadow_branch_detail`; a
        signal, never a fail — evals/CONTRIBUTING.md § 7."""
        sys.path.insert(0, os.path.join(ROOT, "hooks"))
        import branch_names as bn  # noqa: E402
        heads = self.remote_heads()
        snap = (bn.snapshot_from_heads(heads) if heads is not None
                else {"status": "unknown", "reason": "no remote", "heads": []})
        seen = self.observed_bindings(acts)
        detail, mismatches = {}, 0
        for kind, n in keys:
            pat = bn.pattern_for_kind(template, kind, n=n)
            bound = sorted(x for x in seen if pat.match(x))
            m = bn.match_heads(snap, template, kind=kind, n=n)
            if m["outcome"] == "ONE":
                choice = [m["matches"][0]["branch"]]
            elif m["outcome"] == "MULTIPLE_SEQ":
                choice = [max(m["matches"], key=lambda x: x["seq"] or 0)["branch"]]
            elif m["outcome"] == "NO_MATCH":
                choice = []
            else:
                choice = None                       # ambiguous or unknown: never agrees
            agree = choice is not None and bound == choice
            detail["%s/%s" % (kind, n)] = {"bound": bound, "outcome": m["outcome"],
                                           "resolver": choice, "agree": agree}
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


    # ---- #133: roz-state in shadow ---------------------------------------
    def remote_shas(self):
        """branch → commit on the sandbox's bare remote, or None."""
        rc, out = self.git("for-each-ref", "--format=%(refname:short) %(objectname)",
                           "refs/heads/")
        if rc != 0:
            return None
        return dict(ln.split(" ", 1) for ln in out.splitlines() if " " in ln)

    def roz_state(self, issue, template=None, bare=None, state_path=None):
        """Run bin/roz-state for `issue`: (exit code, parsed stdout or None).
        By default against this run's FINAL forge state and remote; `bare` and
        `state_path` name another moment (shadow_scan: the seeded one). The
        tool runs in a fresh clone of the bare remote with a COPY of the forge
        state, so nothing it does — not even the stub's journal line for a
        read — reaches the run's artifacts."""
        tmp = tempfile.mkdtemp()
        try:
            work, forge = os.path.join(tmp, "work"), os.path.join(tmp, "forge")
            os.makedirs(forge)
            shutil.copy(state_path or os.path.join(self.dir, "forge", "state.json"),
                        os.path.join(forge, "state.json"))
            # the seed contract: every sandbox ends on `main` (run_replay.build_sandbox);
            # the bare remote's own HEAD may name a branch that does not exist
            if subprocess.run(["git", "clone", "-q", "--branch", "main", bare or self.bare,
                               work], capture_output=True).returncode != 0:
                return None, None
            if template:
                os.makedirs(os.path.join(work, ".claude"), exist_ok=True)
                with open(os.path.join(work, ".claude", "roz-gate.local.json"), "w",
                          encoding="utf-8") as f:
                    json.dump({"branch_template": template}, f)
            env = dict(os.environ, FORGE_STATE=forge,
                       PATH=os.path.join(S, "forge-stub") + os.pathsep + os.environ["PATH"])
            p = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "roz-state"),
                                str(issue), "--json"], cwd=work, env=env,
                               capture_output=True, text=True)
            # what the tool asked the forge, for the read-only proof (redproof § state)
            self.state_journal = []
            try:
                with open(os.path.join(forge, "journal.jsonl"), encoding="utf-8") as f:
                    self.state_journal = [json.loads(x) for x in f if x.strip()]
            except (OSError, ValueError):
                pass
            try:
                return p.returncode, json.loads(p.stdout) if p.stdout.strip() else None
            except ValueError:
                return p.returncode, None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def shadow_state(self, issues, template=None, _collect=None):
        """#133 shadow, primary: for each issue, bin/roz-state on the run's
        final forge state against the answer computed straight from the stub's
        state.json and the remote's heads (`state_truth` — it shares no code
        with the collector). Writes `shadow_state_mismatch` (differing facts),
        `shadow_state_invalid` (runs whose output the contract rejects, or
        that exit 3) and `shadow_state_detail`; a signal, never a fail —
        evals/CONTRIBUTING.md § 7."""
        sys.path.insert(0, os.path.join(ROOT, "hooks"))
        import state_contract as sc  # noqa: E402
        state, shas = self.state(), self.remote_shas()
        detail, mismatches, invalid = {}, 0, 0
        for n in issues:
            rc, obj = (_collect or self.roz_state)(n, template)
            truth = state_truth(state, shas, n, template)
            errs = (sc.validate(obj) if rc == 0 else sc.validate_failure(obj) if rc == 2
                    else ["exit %s" % rc])
            if errs:
                invalid += 1
                detail[str(n)] = {"invalid": errs[:5]}
                continue
            diff = state_diff(obj, truth)
            mismatches += len(diff)
            detail[str(n)] = {"diff": diff}
        self.signal(shadow_state_mismatch=mismatches, shadow_state_invalid=invalid,
                    shadow_state_detail=detail)
        return mismatches + invalid

    def scanner_table(self):
        """The patrol scanner's table — its dispatch's tool_result, or the
        task notification of a background dispatch — or ''."""
        events = list(self.transcript_events())

        def blocks(ev):
            return [b for b in ((ev.get("message") or {}).get("content") or [])
                    if isinstance(b, dict)]
        sid = None
        for ev in events:
            for b in blocks(ev):
                if b.get("type") == "tool_use" and b.get("name") in ("Task", "Agent") \
                        and "patrol-scan.md" in json.dumps(b.get("input", {}),
                                                           ensure_ascii=False):
                    sid = b.get("id")
                    break
            if sid:
                break
        table = ""
        for ev in events:
            for b in blocks(ev):
                if b.get("type") == "tool_result" and b.get("tool_use_id") == sid:
                    cont = b.get("content")
                    text = cont if isinstance(cont, str) else "".join(
                        x.get("text", "") for x in (cont or []) if isinstance(x, dict))
                    if "|" in text:
                        table = text
            if ev.get("type") == "system" and ev.get("subtype") == "task_notification" \
                    and ev.get("tool_use_id") == sid and "|" in (ev.get("summary") or ""):
                table = ev["summary"]
        return table

    def shadow_scan(self, issues, case_dir, template=None, table=None, _collect=None):
        """#133 shadow, secondary: the scanner table's FACT columns — `track`,
        `status`, `cr` — against a snapshot of the state the scanner read.
        Never `waiting on`, `verdict`, `unheard` or `evidence`: those are the
        scanner's interpretation, and their parity is #134's.

        The table is from the scan's time, and the pass acts after it, so the
        run's final state is the wrong thing to compare with (codex review,
        PR #273: a lock taken after a faithful table read as a misread). The
        scan is patrol's first step, before any write: the state it read is
        the case's SEEDED one — `case_dir`'s seed.sh and state.json, rebuilt
        here. If the journal shows a forge write before the first listing,
        that premise is false and no row is compared.

        Writes `shadow_scan_mismatch`, `shadow_scan_rows` (rows compared) and
        `shadow_scan_detail`; a signal, never a fail."""
        table = self.scanner_table() if table is None else table
        detail, mismatches, rows = {}, 0, 0
        routes = [(e.get("route"), bool(e.get("write"))) for e in self.journal()]
        first_list = next((i for i, (r, _) in enumerate(routes) if r == "issue-list"),
                          len(routes))
        early = [r for r, w in routes[:first_list] if w]
        sbx = bare = None
        if early:
            detail["premise"] = "forge writes before the scan: %s" % ", ".join(early[:5])
        elif _collect is None:
            sbx, bare = seed_sandbox(case_dir)
            if not sbx:
                detail["premise"] = "the seeded state could not be rebuilt"
        try:
            for n in issues if "premise" not in detail else ():
                row = scan_row(table, n)
                if row is None:
                    detail[str(n)] = {"row": "absent"}
                    continue
                rc, obj = (_collect(n, template) if _collect else self.roz_state(
                    n, template, bare=bare, state_path=os.path.join(case_dir, "state.json")))
                if rc != 0 or not isinstance(obj, dict):
                    detail[str(n)] = {"snapshot": "exit %s" % rc}
                    continue
                rows += 1
                diff = scan_diff(row, obj)
                mismatches += len(diff)
                detail[str(n)] = {"diff": diff}
        finally:
            if sbx:
                shutil.rmtree(sbx, ignore_errors=True)
        self.signal(shadow_scan_mismatch=mismatches, shadow_scan_rows=rows,
                    shadow_scan_detail=detail)
        return mismatches


    # ---- #134: roz-check in shadow ----------------------------------------
    def lock_taken(self, issue):
        """The run added `status: processing` to `issue` — integrate's § 2."""
        return any(e.get("route") == "issue-edit" and str(e.get("issue")) == str(issue)
                   and any("processing" in a for a in e.get("add", []))
                   for e in self.journal())

    def shadow_check(self, issue, case_dir, operation="integrate", template=None,
                     _result=None):
        """#134 shadow: roz-check's verdict for `operation` on the state the
        command READ — the case's seeded state, rebuilt from `case_dir` (the
        lesson of shadow_scan: never the run's final state) — against whether
        the command took the lock.

            eligible   → the lock is expected
            ineligible → no lock is expected
            unknown    → no lock is expected: the evidence does not authorize
                         the operation, so a lock taken on it is a mismatch,
                         never ignored

        A snapshot that could not be collected is `unknown` too. Writes
        `shadow_check_mismatch` (0 / 1), `shadow_check_unknown` (0 / 1, for
        information) and `shadow_check_detail`; a signal, never a fail."""
        sys.path.insert(0, os.path.join(ROOT, "hooks"))
        import state_check as ck  # noqa: E402
        detail = {"operation": operation, "issue": str(issue)}
        if _result is not None:
            result = _result
        else:
            result = {"verdict": "unknown", "may_start": False, "failed": [], "unknown": []}
            sbx, bare = seed_sandbox(case_dir)
            try:
                if sbx:
                    rc, obj = self.roz_state(issue, template, bare=bare,
                                             state_path=os.path.join(case_dir, "state.json"))
                    if rc == 0:
                        try:
                            result = ck.check(operation, obj)
                        except ck.InvalidSnapshot as e:
                            detail["snapshot"] = "invalid: %s" % e
                    else:
                        detail["snapshot"] = "exit %s" % rc
                else:
                    detail["snapshot"] = "the seeded state could not be rebuilt"
            finally:
                if sbx:
                    shutil.rmtree(sbx, ignore_errors=True)
        locked = self.lock_taken(issue)
        mismatch = int(bool(result["may_start"]) != locked)
        detail.update(verdict=result["verdict"], failed=result["failed"],
                      unknown=result["unknown"], locked=locked)
        self.signal(shadow_check_mismatch=mismatch,
                    shadow_check_unknown=int(result["verdict"] == "unknown"),
                    shadow_check_detail=detail)
        return mismatch


def seed_sandbox(cdir):
    """(sandbox dir, bare remote) for a case's seeded state — run_replay's
    build_sandbox, with a git identity in the environment: a seed that makes
    a merge commit needs one, and a CI runner has none."""
    import run_replay as rr  # noqa: E402 — call time: run_replay imports this module
    ident = {"GIT_AUTHOR_NAME": "seed", "GIT_AUTHOR_EMAIL": "seed@example.com",
             "GIT_COMMITTER_NAME": "seed", "GIT_COMMITTER_EMAIL": "seed@example.com"}
    old = {k: os.environ.get(k) for k in ident}
    os.environ.update({k: v for k, v in ident.items() if not old[k]})
    try:
        sbx, _work, bare = rr.build_sandbox(cdir)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
    return sbx, bare


# ---- #133: stub truth — what a correct snapshot of this forge state says ----
# Written from the stub's fixture format, sharing no code with
# hooks/state_collect.py (only the branch resolver, which is roz-branch's and
# is the truth for branch identity by #239 ruling 4).

_STATE_FACTS = ("branches.spec", "branches.implementation", "branches.qa", "spec.cr",
                "implementation.cr", "implementation.open_review_threads",
                "implementation.review_marker", "qa.cr", "qa.open_fidelity_threads",
                "qa.fidelity_marker", "dependencies.blocked_by")
_STATE_PLAIN = ("issue", "track", "status", "processing", "blocked")


def state_truth(state, shas, issue, template=None):
    """{'plain': {...}, 'facts': {path: (status, value)}} for a snapshot, or
    {'failure': reason} where no snapshot can be honest."""
    sys.path.insert(0, os.path.join(ROOT, "hooks"))
    import branch_names as bn  # noqa: E402
    iss = (state.get("issues") or {}).get(str(issue))
    if iss is None:
        return {"failure": "forge_query_failed"}
    labels = iss.get("labels", [])
    worn = [x.split(":", 1)[1].strip() for x in labels if x.startswith("status:")]
    tracks = [x.split(":", 1)[1].strip() for x in labels if x.startswith("track:")]
    stages = [x for x in worn if x not in ("processing", "blocked")]
    if len(set(tracks)) > 1 or len(set(stages)) > 1:
        return {"failure": "ambiguous"}
    track = tracks[0] if tracks else None
    types = sorted({x.split(":", 1)[1].strip() for x in labels if x.startswith("type:")})
    plain = {"issue": int(issue), "track": track, "status": stages[0] if stages else None,
             "processing": "processing" in worn, "blocked": "blocked" in worn}
    facts = {}

    def expand(text):
        return re.sub(r"\{\{sha:([^}\s]+)\}\}",
                      lambda m: (shas or {}).get(m.group(1), m.group(0)), text or "")

    snap = (bn.snapshot_from_heads(shas) if shas is not None
            else {"status": "unknown", "heads": []})
    # #272 — the head names merged CRs remember, straight from the fixture:
    # per name, the CR merged last (then the higher number)
    gone = {}
    for p in sorted((state.get("prs") or {}).values(),
                    key=lambda x: (x.get("mergedAt") or "", int(x["number"]))):
        if p.get("state", "OPEN").upper() == "MERGED" and p.get("headRefName"):
            gone[p["headRefName"]] = {"cr": int(p["number"]), "sha": p.get("headRefOid")}
    snap["merged_heads"] = {"status": "observed", "heads": gone}
    for name, kind in (("spec", "spec"), ("implementation", "feat"), ("qa", "qa")):
        bkey, ckey = "branches.%s" % name, "%s.cr" % name
        deps = {"implementation": ("implementation.open_review_threads",
                                   "implementation.review_marker", "**[reviewer] · code-review**"),
                "qa": ("qa.open_fidelity_threads", "qa.fidelity_marker",
                       "**[reviewer] · fidelity**")}.get(name)
        if track != "spec":
            facts[bkey], facts[ckey] = ("unknown", None), ("unknown", None)
        else:
            m = bn.match_heads(snap, template, kind=kind, n=str(issue),
                               type=(types[0] if len(types) == 1 else "feat")
                               if kind == "feat" else None)
            if m["outcome"] in ("UNKNOWN", "MULTIPLE_SAME_SEQ"):
                facts[bkey], facts[ckey] = ("unknown", None), ("unknown", None)
            elif m["outcome"] == "NO_MATCH":
                facts[bkey], facts[ckey] = ("absent", None), ("absent", None)
            else:
                top = sorted(m["matches"], key=lambda x: x["seq"] or 0)[-1]
                head, head_sha = top["branch"], top["sha"]
                # a head only a merged CR remembers is no branch; its CR is still found
                facts[bkey] = (("absent", None) if top.get("deleted")
                               else ("observed", {"name": head, "sha": head_sha}))
                mine = [p for p in (state.get("prs") or {}).values()
                        if p.get("headRefName") == head]
                by = {}
                for p in mine:
                    by.setdefault(p.get("state", "OPEN").upper(), []).append(p)
                if len(by.get("OPEN", [])) > 1:
                    facts[ckey] = ("unknown", None)
                elif not mine:
                    facts[ckey] = ("absent", None)
                else:
                    pool = by.get("OPEN") or by.get("MERGED") or by.get("CLOSED")
                    p = sorted(pool, key=lambda x: int(x["number"]))[-1]
                    facts[ckey] = ("observed", {
                        "number": int(p["number"]), "state": p.get("state", "OPEN").lower(),
                        "draft": bool(p.get("isDraft", False)),
                        "base": p.get("baseRefName"), "head_sha": head_sha})
                    if deps:
                        facts[deps[0]] = ("observed", len(
                            [t for t in p.get("threads", []) if not t.get("isResolved", False)]))
                        recs = [c for c in p.get("comments", [])
                                if expand(c.get("body")).lstrip().startswith(deps[2])]
                        if recs:
                            rec = sorted(recs, key=lambda c: c["id"])[-1]
                            sha = re.search(r"^\s*reviewed-sha:\s*`?([0-9a-fA-F]{7,64})`?\s*$",
                                            expand(rec.get("body")), re.M)
                            facts[deps[1]] = ("observed", {
                                "reviewed_sha": sha.group(1) if sha else None,
                                "comment_id": rec["id"]})
                        else:
                            facts[deps[1]] = ("absent", None)
        if deps and deps[0] not in facts:
            st = facts[ckey][0]                       # absent / unknown: they follow the CR
            facts[deps[0]], facts[deps[1]] = (st, None), (st, None)
    if iss.get("blocked_by_error"):
        facts["dependencies.blocked_by"] = ("unknown", None)
    else:
        facts["dependencies.blocked_by"] = ("observed", sorted(
            [{"issue": int(b),
              "state": ((state.get("issues") or {}).get(str(b)) or {}).get("state", "open"),
              # #250 — the fixture's own repository, read here and not from
              # the stub: the truth shares no code with what it checks
              "url": "https://github.com/%s/%s/issues/%s" % (
                  (state.get("repo") or {}).get("owner", "acme"),
                  (state.get("repo") or {}).get("name", "demo"), b)}
             for b in iss.get("blocked_by", [])], key=lambda x: x["issue"]))
    return {"plain": plain, "facts": facts}


def state_diff(obj, truth):
    """The paths where a snapshot (or a typed failure) and the truth differ."""
    if "failure" in truth or "collection_failure" in obj:
        got = (obj.get("collection_failure") or {}).get("reason")
        return [] if got == truth.get("failure") else [
            "collection_failure: %r, truth %r" % (got, truth.get("failure", "a snapshot"))]
    out = []
    for k in _STATE_PLAIN:
        if obj.get(k) != truth["plain"][k]:
            out.append("%s: %r, truth %r" % (k, obj.get(k), truth["plain"][k]))
    for path in _STATE_FACTS:
        node = obj
        for k in path.split("."):
            node = node.get(k) if isinstance(node, dict) else None
        got = (node.get("status"), node.get("value")) if isinstance(node, dict) else (None, None)
        if got != truth["facts"][path]:
            out.append("%s: %r, truth %r" % (path, got, truth["facts"][path]))
    return out


# ---- #133: the scanner table's fact columns --------------------------------

def scan_row(table, issue):
    """The cells of the table row for `issue`, or None."""
    for line in (table or "").splitlines():
        line = line.strip()
        if re.match(r"^\|\s*#?%s\b" % issue, line):
            return [c.strip() for c in line.strip("|").split("|")]
    return None


def _scan_words(cell, prefix):
    cell = re.sub(r"[`*]", "", cell or "").replace(prefix, " ")
    return set(re.findall(r"[a-z][a-z-]*", cell.lower())) - {"none"}


def scan_diff(cells, snap):
    """Differences between a scanner row's `track` / `status` / `cr` cells
    (columns 2, 3 and 5 of `issue · track · status · holder · cr · unheard ·
    verdict · evidence`) and a snapshot. An unknown fact is never compared."""
    out = []
    if len(cells) < 5:
        return ["row: fewer than five columns"]
    track = _scan_words(cells[1], "track:")
    want = {snap["track"]} if snap.get("track") else set()
    if track != want:
        out.append("track: scanner %s, snapshot %s" % (sorted(track), sorted(want)))
    status = _scan_words(cells[2], "status:")
    want = ({snap["status"]} if snap.get("status") else set()) \
        | ({"processing"} if snap.get("processing") else set()) \
        | ({"blocked"} if snap.get("blocked") else set())
    if status != want:
        out.append("status: scanner %s, snapshot %s" % (sorted(status), sorted(want)))
    crs = [snap[k]["cr"] for k in ("spec", "implementation", "qa")]
    if any(c["status"] == "unknown" for c in crs):
        return out
    seen = [c["value"] for c in crs if c["status"] == "observed"]
    cell = re.sub(r"https?://\S+", " ", cells[4])
    num = re.search(r"#?(\d+)", cell)
    if num:
        hit = [v for v in seen if v["number"] == int(num.group(1))]
        if not hit:
            out.append("cr: scanner cites %s, the snapshot has no such CR" % num.group(1))
        else:
            word = re.search(r"\b(open|draft|merged|closed)\b", cell.lower())
            v = hit[0]
            have = "draft" if v["state"] == "open" and v["draft"] else v["state"]
            if word and word.group(1) != have:
                out.append("cr: scanner says %s is %s, snapshot %s"
                           % (v["number"], word.group(1), have))
    elif re.search(r"\bnone\b|—", cell.lower()) and any(v["state"] == "open" for v in seen):
        out.append("cr: scanner says none, the snapshot has an open CR")
    return out
