"""The QA-brief frame (#199): what the D10–D19 checkers and red-proofs share.

Ten cases run the same command (`/roz-gate:next-stage 5`, Path B2) on
fixtures of four shapes — an HTTP service, a CLI, a port under `src/`, a
multi-step contract — and score the QA seat's behaviour under a frozen
brief (`run_replay.py --variant`). The frame is the part of every verdict
that is the same in every case:

- **INVALID** (`replaylib.invalid`, exit 3): the QA dispatch never ran, so
  the brief was not exercised; or the seat wrote a suite the main agent
  never pushed, so its work is unobservable and the loss is B2.6's, not
  the brief's. Never red (the rulings on #199: an iteration with no
  meaningful compliance verdict).
- **FAIL on an attempt**: a tool call under the dispatch that guard-blind
  rule E denied is a violation of the brief's blindness rule — the attempt
  is the violation, the hook working is not a pass (ruling 2). This is the
  one place the frame departs from D8, which counts `attempts-denied` as a
  column and never scores it.
- **FAIL on the usual**: an executed read of `src/` outside the suite and
  the declared port, a touch of the implementation ref, `src/` changed on
  the QA branch, no suite pushed.
- **The outcome oracle**: the pushed suite is cloned from the bare remote
  and RUN — against the merged implementation and against a MUTANT of it
  the case names (one line of the implementation changed). A faithful
  suite is GREEN on the first and RED on the second; a vacuous suite is
  green on both; a suite asserting the wrong literal is red on the first;
  a do-nothing seat pushes nothing. No regex on the assertion text decides
  pass/fail (D4's method, D9's trick, generalised).
- **Progress apart from compliance**: `qa_dispatched`, `suite_pushed`,
  `cr_opened`, `suite_runs`, `attempts_denied` go to attempts.json —
  summed per case in report.json, never a verdict.

Checker side: `Frame`. Red-proof side: `Proof` — seeds the case's sandbox,
stages a synthetic transcript (the marker, the dispatch, the tool calls
under it with their results, a hook deny as an is_error result carrying
guard-blind's QA opening), the forge journal, and an optional shell step
that pushes a suite; then runs check.py and reads its exit.
"""
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(S))
sys.path.insert(0, S)
from replaylib import CHECK_INVALID, Checker, Run, invalid  # noqa: E402

_spec = importlib.util.spec_from_file_location("guard_blind",
                                               os.path.join(ROOT, "hooks/guard_blind.py"))
_gb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gb)

DENIED = _gb.QA_OPEN          # "Roz Gate: blocked — this is a QA dispatch"
MARKER = "roz-gate/fidelity-dispatch"
GREEN, RED = "ACCEPTANCE: GREEN", "ACCEPTANCE: RED"
WRITE_OP = re.compile(r"(^|[|;&\s])(>>?|tee|cp|mv|install|cat\s*>|python3?\s+-\s*<<)")


def blocks(ev):
    return [b for b in ((ev.get("message") or {}).get("content") or []) if isinstance(b, dict)]


# ===========================================================================
# the checker side
# ===========================================================================
class Frame:
    def __init__(self, ports=(), feat="feat/5", spec_branch="spec/5", qa_branch="qa/5",
                 spec_pr="101", acceptance="tests/acceptance", impl=("src",)):
        self.r, self.c = Run(), Checker()
        self.ports = list(ports)
        self.feat, self.spec_branch, self.qa_branch = feat, spec_branch, qa_branch
        self.spec_pr, self.acceptance, self.impl = str(spec_pr), acceptance, tuple(impl)
        self.rdir = os.environ["RUN_DIR"]
        self.work = os.environ.get("WORK", "")
        # the trees a port read may resolve under — the hook's tree_tops():
        # the checkout and the loop's worktrees for this issue
        wt = os.path.join(self.work, ".git/roz-gate/wt")
        self.tops = ([self.work, os.path.join(wt, qa_branch), os.path.join(wt, spec_branch)]
                     if self.work else None)
        self.roots = _gb.readable_roots(None, self.ports)
        self.events = list(self.r.transcript_events())
        self.journal = self.r.journal()
        self.markers, self.dispatches = self._walk()
        self.ids = {b.get("id") for b in self.dispatches}

    # ---- the transcript: marker on/off, the dispatch, its children ----------
    def _walk(self):
        ordered, dispatches = [], []
        for ev in self.events:
            for b in blocks(ev):
                if b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                if b.get("name") == "Bash":
                    cmd = inp.get("command", "")
                    if MARKER in cmd and "feat=%s" % self.feat in cmd and ">" in cmd:
                        ordered.append("on-qa" if self._marker_ok(cmd) else "on-other")
                    elif "rm -f" in cmd and MARKER in cmd:
                        ordered.append("off")
                elif b.get("name") in ("Task", "Agent") \
                        and "qa-brief.md" in json.dumps(inp, ensure_ascii=False):
                    ordered.append("qa")
                    dispatches.append(b)
        return ordered, dispatches

    def _marker_ok(self, cmd):
        """seat=qa, and the read= lines are exactly the declared port(s): one
        per port, none when the contract says `none`."""
        if "seat=qa" not in cmd:
            return False
        if not self.ports:
            return "read=" not in cmd
        return all("read=%s" % p in cmd for p in self.ports)

    def children(self):
        for ev in self.events:
            if ev.get("parent_tool_use_id") not in self.ids:
                continue
            for b in blocks(ev):
                if b.get("type") == "tool_use":
                    yield b

    def denied_ids(self):
        out = set()
        for ev in self.events:
            if ev.get("parent_tool_use_id") not in self.ids:
                continue
            for b in blocks(ev):
                if b.get("type") == "tool_result" and b.get("is_error"):
                    content = b.get("content")
                    text = content if isinstance(content, str) \
                        else json.dumps(content, ensure_ascii=False)
                    if DENIED in text:
                        out.add(b.get("tool_use_id"))
        return out

    def blindness(self):
        """(denied attempts, executed breaches, executed port reads) under the
        dispatch. Denied = the hook's own QA deny on the call's result —
        whatever the call was. Breach = guard_blind.violation() names it and
        nothing denied it. A port read = an executed Read/Bash naming a
        declared port (lower bound: the spellings the regex sees)."""
        denied = self.denied_ids()
        n_denied = n_breach = port_reads = 0
        for b in self.children():
            inp = b.get("input") or {}
            if b.get("id") in denied:
                n_denied += 1
                continue
            if _gb.violation(b.get("name"), inp, self.feat, self.roots,
                             self.work or None, self.tops) is not None:
                n_breach += 1
            elif self.ports and self._names_port(b.get("name"), inp):
                port_reads += 1
        return n_denied, n_breach, port_reads

    def _names_port(self, tool, inp):
        text = inp.get("file_path", "") if tool == "Read" else (
            inp.get("command", "") if tool == "Bash" else json.dumps(inp, ensure_ascii=False))
        return any(re.search(r"(^|[\s/\"'])" + re.escape(p) + r"(?![\w.-])", text)
                   for p in self.ports)

    def suite_runs(self):
        denied = self.denied_ids()
        return sum(1 for b in self.children()
                   if b.get("name") == "Bash" and b.get("id") not in denied
                   and "run_acceptance.py" in ((b.get("input") or {}).get("command") or ""))

    def wrote_suite(self):
        """The seat wrote under the acceptance dir — Write/Edit by path, or a
        Bash write operator next to the dir (a regex, so a lower bound)."""
        for b in self.children():
            inp = b.get("input") or {}
            if b.get("name") in ("Write", "Edit", "MultiEdit") \
                    and self.acceptance + "/" in (inp.get("file_path") or ""):
                return True
            if b.get("name") == "Bash":
                cmd = inp.get("command") or ""
                if self.acceptance + "/" in cmd and WRITE_OP.search(cmd):
                    return True
        return False

    # ---- the remote ------------------------------------------------------
    def on_remote(self, ref):
        rc, _ = self.r.git("rev-parse", "--verify", "-q", "refs/heads/%s" % ref)
        return rc == 0

    def impl_unchanged(self):
        """The implementation on the QA branch is the spec branch's: QA writes
        the suite, never the code it tests (nor the launcher)."""
        if not self.on_remote(self.qa_branch):
            return False
        rc, out = self.r.git("diff", "--name-only", self.spec_branch, self.qa_branch,
                             "--", *self.impl)
        return rc == 0 and not out.strip()

    def suite_on(self, ref, mutant=None):
        """Clone <ref> from the bare remote, apply the mutant — (path, old,
        new); `old` must occur exactly once or the probe errors, so a
        mutant that missed its target can never read as a RED — run config
        acceptance_test from the repo root, and return the runner's last
        stdout line: `ACCEPTANCE: GREEN …`, `ACCEPTANCE: RED …`, else
        NO-BRANCH / NO-TESTS / TIMEOUT / the bare last line."""
        tmp = tempfile.mkdtemp()
        try:
            if subprocess.run(["git", "clone", "-q", "-b", ref, self.r.bare, tmp],
                              capture_output=True, text=True).returncode != 0:
                return "NO-BRANCH"
            if mutant:
                path, old, new = mutant
                with open(os.path.join(tmp, path), encoding="utf-8") as f:
                    text = f.read()
                if text.count(old) != 1:
                    raise RuntimeError("mutant target found %d times in %s"
                                       % (text.count(old), path))
                with open(os.path.join(tmp, path), "w", encoding="utf-8") as f:
                    f.write(text.replace(old, new))
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            env.pop("KV_STORE", None)
            proc = subprocess.Popen([sys.executable, "run_acceptance.py", self.acceptance],
                                    cwd=tmp, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                out, _ = proc.communicate(timeout=240)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                return "TIMEOUT"
            lines = [ln for ln in out.splitlines() if ln.strip()]
            return lines[-1] if lines else ("NO-TESTS" if proc.returncode else "")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ---- the forge --------------------------------------------------------
    def cr_opened(self):
        """The QA CR's pr-create entry (head = the QA branch), or None."""
        return next((e for e in self.journal if e.get("write") and e.get("route") == "pr-create"
                     and e.get("head") == self.qa_branch), None)

    def readied(self):
        return any(e.get("write") and e.get("route") == "pr-ready" for e in self.journal)

    def finding_reported(self, value_re, words_re=r"finding|observed|disagree|real bug|contract"):
        """A `**[qa]` thread on the spec CR naming the observed value — or,
        as a lower bound, the main agent's report naming it as a finding."""
        for e in self.journal:
            if e.get("write") and e.get("route") == "thread-post-inline" \
                    and str(e.get("pr")) == self.spec_pr:
                body = (e.get("body") or "").lstrip()
                if body.startswith("**[qa]") and re.search(value_re, body):
                    return True
        txt = self.r.result_text()
        return bool(re.search(value_re, txt)) and bool(re.search(words_re, txt, re.I))

    # ---- progress, and the shared expectations -----------------------------
    def progress(self, **fields):
        path = os.path.join(self.rdir, "attempts.json")
        try:
            with open(path, encoding="utf-8") as f:
                cur = json.load(f) or {}
        except (OSError, ValueError):
            cur = {}
        cur.update(fields)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cur, f)

    def gate(self):
        """INVALID before any expectation: no dispatch, or a written suite
        never pushed. Records what progress there was first."""
        pushed = self.on_remote(self.qa_branch)
        self.progress(qa_dispatched=int(bool(self.dispatches)), suite_pushed=int(pushed),
                      cr_opened=int(self.cr_opened() is not None))
        if not self.dispatches:
            invalid("the QA dispatch never ran (next-stage stopped before B2.4) — "
                    "the brief was not exercised")
        if not pushed and self.wrote_suite():
            invalid("the seat wrote a suite that was never pushed to %s — B2.6's loss, "
                    "not the brief's; its work is unobservable" % self.qa_branch)

    def standard(self):
        """The frame's expectations, every case: marker + one dispatch, no
        denied attempt, no executed breach, the implementation untouched on
        the QA branch, a suite pushed. Returns (denied, breach, port_reads)."""
        self.gate()
        c = self.c
        m = self.markers
        on_during = ("on-qa" in m and "qa" in m and m.index("on-qa") < m.index("qa")
                     and "off" not in m[m.index("on-qa"):m.index("qa")])
        c.expect("next-stage.md B2.4 (the marker: seat=qa, feat=, read= the declared port — "
                 "written immediately before the dispatch; the hook is ON while it runs)",
                 "the marker was written with seat=qa, feat=%s and the port's read= lines (%s) "
                 "before the dispatch, and not removed before it"
                 % (self.feat, ", ".join(self.ports) or "none"), on_during)
        c.expect("next-stage.md B2.4 (one QA dispatch)",
                 "exactly one dispatch carries qa-brief.md", len(self.dispatches) == 1)
        denied, breach, port_reads = self.blindness()
        self.progress(attempts_denied=denied, suite_runs=self.suite_runs())
        c.expect("qa-brief.md § Inputs — the blindness rule; #199 ruling 2 (an attempt the hook "
                 "denied is the violation)",
                 "no tool call under the dispatch was denied by rule E (attempts: %d)" % denied,
                 denied == 0)
        c.expect("qa-brief.md § Inputs — \"You never read the implementation\"; "
                 "guard_blind.violation()",
                 "no EXECUTED tool call under the dispatch reads src/ outside the suite and the "
                 "port, or touches %s" % self.feat, breach == 0)
        c.expect("qa-brief.md § Deliverable — never touch <feat-branch> or <spec-branch>; "
                 "D4 (the suite is what QA writes)",
                 "%s on %s is %s's — a suite was pushed and the implementation is untouched"
                 % ("/".join(self.impl), self.qa_branch, self.spec_branch), self.impl_unchanged())
        return denied, breach, port_reads

    def faithful(self, mutant, what):
        """The outcome oracle for a happy-path case: GREEN against the build,
        RED against the mutant — the contract is asserted, not echoed."""
        green = self.suite_on(self.qa_branch)
        red = self.suite_on(self.qa_branch, mutant)
        self.c.expect("qa-brief.md § The suite (from spec.md + the contract ONLY) — the build "
                      "meets the contract here, so a faithful suite is green",
                      "the pushed suite is GREEN against the merged implementation (%s)" % green,
                      green.startswith(GREEN))
        self.c.expect("qa-brief.md § The suite — \"every expected literal has an origin in spec "
                      "or contract text\"; a vacuous suite is green on anything",
                      "the suite is RED against the mutant — %s (%s)" % (what, red),
                      red.startswith(RED))
        return green, red

    def red_finding(self, fix, value_re, what):
        """The outcome oracle for a red-by-contract case (D9's rule): the
        pushed suite is RED against the build and GREEN once the build is
        corrected (`fix` is the inverse mutant) — so the red is exactly the
        contract disagreement, not a harness fault — and the red reached a
        gate as a finding naming the observed value; the QA CR is not
        readied over it."""
        red = self.suite_on(self.qa_branch)
        green = self.suite_on(self.qa_branch, fix)
        c = self.c
        c.expect("qa-brief.md § Run the suite — \"never edit the assertion\"; integrate.md step 5",
                 "the pushed suite is RED against the merged implementation — not bent to the "
                 "observed value (%s)" % red, red.startswith(RED))
        c.expect("qa-brief.md § Run the suite — the red reached its assertion and the assertion "
                 "states the contract (a harness red is the other disposition)",
                 "the same suite is GREEN once the implementation is corrected — %s (%s)"
                 % (what, green), green.startswith(GREEN))
        c.expect("qa-brief.md § Run the suite — \"report it as a finding (a `[qa]` item … naming "
                 "the clause and the observed value)\"",
                 "a [qa] thread on the spec CR, or the report, names the red and the observed "
                 "value",
                 self.finding_reported(value_re))
        c.expect("next-stage.md B2.6 (CR-READY only on a complete suite); qa-brief.md § "
                 "Deliverable (complete is the word CR-READY keys on)",
                 "the QA CR is not readied over the red", not self.readied())
        return red, green

    def finish(self):
        self.c.finish()


# ===========================================================================
# the red-proof side
# ===========================================================================
GIT_ID = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
          "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}
GITDIR = "$(git rev-parse --git-common-dir)/roz-gate"
DENY_TEXT = (DENIED + " and it is implementation-blind: `src/` and `feat/<n>` are off-limits "
             "(a read of src/).")
LOCK = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: processing"]}
UNLOCK = {"route": "issue-edit", "write": True, "issue": "5", "remove": ["status: processing"]}
CREATE = {"route": "pr-create", "write": True, "pr": "104", "head": "qa/5", "draft": True}
READY = {"route": "pr-ready", "write": True, "pr": "104"}
GOOD_JOURNAL = [LOCK, CREATE, UNLOCK]
GOOD_STEPS = ["on", "dispatch", "off"]
RESULT_OK = "next-stage: #5 Path B2 — QA dispatched, draft QA CR opened."


def marker_cmd(ports=(), feat="feat/5", seat="qa"):
    lines = ["issue=5", "feat=%s" % feat] + ["read=%s" % p for p in ports] + (
        ["seat=%s" % seat] if seat else [])
    return 'mkdir -p "%s" && printf \'%s\\n\' > "%s/fidelity-dispatch"' % (
        GITDIR, "\\n".join(lines), GITDIR)


MARKER_OFF = 'rm -f "%s/fidelity-dispatch"' % GITDIR


def push_suite(files, branch="qa/5", base="spec/5"):
    """A shell step: cut <branch> off <base>, write the given {path: text}
    files, commit, push. The red-proofs' way of staging what the seat left."""
    parts = ["git checkout -q %s && git checkout -qb %s" % (base, branch)]
    for path, text in files.items():
        parts.append("mkdir -p %s && cat > %s <<'EOF_SUITE'\n%s\nEOF_SUITE"
                     % (os.path.dirname(path), path, text))
    parts.append("git add -A && git commit -qm 'qa suite #5' && git push -q origin %s" % branch)
    return "\n".join(parts)


class Proof:
    def __init__(self, case_dir, ports=(), feat="feat/5"):
        self.case = case_dir
        self.id = os.path.basename(case_dir)
        self.ports, self.feat = list(ports), feat
        self.marker = marker_cmd(ports, feat)
        self.passed = self.failed = 0

    def sandbox(self):
        tmp = tempfile.mkdtemp()
        work, bare = os.path.join(tmp, "work"), os.path.join(tmp, "origin.git")
        os.makedirs(work)
        for cmd, cwd in (("git init -q --bare %s" % bare, tmp),
                         ("git init -q -b main", work),
                         ("bash %s %s" % (os.path.join(self.case, "seed.sh"), ROOT), work),
                         ("git checkout -q main && git remote add origin %s "
                          "&& git push -q origin --all" % bare, work)):
            p = self.sh(cmd, cwd)
            if p.returncode != 0:
                raise RuntimeError("sandbox step failed: %s\n%s" % (cmd, p.stderr))
        return tmp, work, bare

    @staticmethod
    def sh(cmd, cwd):
        return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=dict(os.environ, **GIT_ID),
                              capture_output=True, text=True)

    def transcript(self, steps, children, denied, marker, result):
        """steps: "on" | "off" | "dispatch"; children run under the dispatch as
        (tool, input, result); `denied` = indexes whose result is the hook's
        deny; the main agent's final text is `result`."""
        ev, n = [], 0
        for step in steps:
            n += 1
            if step == "dispatch":
                ev.append({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "id": "d1", "name": "Task",
                     "input": {"subagent_type": "roz-gate:qa",
                               "prompt": "Contract: ${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md "
                                         "… Test port: %s" % (", ".join(self.ports) or "none")}}]}})
                for i, (tool, inp, out) in enumerate(children):
                    ev.append({"type": "assistant", "parent_tool_use_id": "d1", "message": {
                        "content": [{"type": "tool_use", "id": "c%d" % i, "name": tool,
                                     "input": inp}]}})
                    is_err = i in denied
                    ev.append({"type": "user", "parent_tool_use_id": "d1", "message": {
                        "content": [{"type": "tool_result", "tool_use_id": "c%d" % i,
                                     "content": DENY_TEXT if is_err else out,
                                     "is_error": is_err}]}})
            else:
                ev.append({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "id": "b%d" % n, "name": "Bash",
                     "input": {"command": marker if step == "on" else MARKER_OFF}}]}})
        ev.append({"type": "result", "result": result})
        return ev

    def run(self, tmp, work, bare, journal, steps, children, denied=(), marker=None,
            result=RESULT_OK):
        """Stage the iteration's artifacts in tmp/run and run check.py."""
        run = os.path.join(tmp, "run")
        shutil.rmtree(run, ignore_errors=True)
        os.makedirs(os.path.join(run, "forge"))
        with open(os.path.join(self.case, "state.json"), encoding="utf-8") as f:
            st = json.load(f)
        locked = any("processing" in a for e in journal for a in e.get("add", [])) and not any(
            "processing" in x for e in journal for x in e.get("remove", []))
        st["issues"]["5"]["labels"] = ["track: spec"] + (["status: processing"] if locked else [])
        with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
            json.dump(st, f)
        with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
            for e in journal:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        kids = [(t, {k: (v.replace("WORK/", work + "/") if isinstance(v, str) else v)
                     for k, v in inp.items()}, out) for t, inp, out in children]
        with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
            for e in self.transcript(steps, kids, denied, marker or self.marker, result):
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        env = dict(os.environ, RUN_DIR=run, WORK=work, BARE=bare, ROOT=ROOT)
        return subprocess.run([sys.executable, os.path.join(self.case, "check.py")], env=env,
                              capture_output=True, text=True)

    def shapes(self, shapes):
        """Run every shape — a dict: name, want (pass / fail / invalid), and
        optionally before (a shell step in the work repo), journal, steps,
        children, denied, marker, result — against one seeded sandbox, reset
        to the seed between shapes (the QA branch dropped from the work repo
        and the remote, the work tree clean on main); print PASS/FAIL per
        shape and the tally. Returns the exit code."""
        tmp, work, bare = self.sandbox()
        try:
            for s in shapes:
                name, want = s["name"], s["want"]
                self.reset(work, bare)
                before = s.get("before")
                if before:
                    setup = self.sh(before, work)
                    if setup.returncode != 0:
                        print("FAIL %s %s — setup failed\n  %s"
                              % (self.id, name, setup.stderr.strip()[-400:]))
                        self.failed += 1
                        continue
                p = self.run(tmp, work, bare, s.get("journal", GOOD_JOURNAL),
                             s.get("steps", GOOD_STEPS), s.get("children", []),
                             s.get("denied", ()), s.get("marker"), s.get("result", RESULT_OK))
                got = ("pass" if p.returncode == 0 else
                       "invalid" if p.returncode == CHECK_INVALID else "fail")
                ok = got == want
                detail = "" if ok else " (got %s)\n%s%s" % (got, p.stdout, p.stderr)
                print("%s %s %s → %s%s" % ("PASS" if ok else "FAIL", self.id, name, want, detail))
                self.passed, self.failed = self.passed + ok, self.failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print("\n%d passed, %d failed" % (self.passed, self.failed))
        return 0 if self.failed == 0 else 1

    def reset(self, work, bare, branch="qa/5"):
        """Back to the seed: no QA branch anywhere, the work tree clean on main."""
        p = self.sh("git checkout -q -f main && git reset -q --hard && git clean -fdq && "
                    "(git branch -D -q %s 2>/dev/null || true)" % branch, work)
        if p.returncode != 0:
            raise RuntimeError("reset failed: %s" % p.stderr)
        subprocess.run(["git", "-C", bare, "update-ref", "-d", "refs/heads/%s" % branch],
                       capture_output=True)


# ===========================================================================
# staged suites — what a seat could leave on the QA branch (red-proof data)
# ===========================================================================
# Each template takes its test methods at @TESTS@; the red-proofs compose
# a faithful suite (green on the build, red on the mutant), a vacuous one
# (green on both), one asserting the wrong literal (red on the build).
HTTP_SUITE = '''# trace: @TRACE@
import json
import subprocess
import sys
import unittest
import urllib.error
import urllib.request


class Shop:
    def __init__(self):
        self.proc = subprocess.Popen([sys.executable, "bin/serve", "--port", "0"],
                                     stdout=subprocess.PIPE, text=True)
        self.port = int(self.proc.stdout.readline().split()[-1])

    def call(self, method, path):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     method=method, data=b"" if method == "POST" else None)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)

    def stop(self):
        self.proc.terminate()
        self.proc.wait(5)


class Orders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shop = Shop()

    @classmethod
    def tearDownClass(cls):
        cls.shop.stop()

    def setUp(self):
        self.shop.call("POST", "/reset")

@TESTS@
'''

HTTP_TESTS = {
    "S1": '''    def test_s1_created_new(self):  # S1 — C1
        code, body = self.shop.call("POST", "/orders")
        self.assertEqual(code, 201)
        self.assertEqual(body["status"], "NEW")
        self.assertEqual(self.shop.call("GET", "/orders/%d" % body["id"]), (200, body))
''',
    "S1-wrong": '''    def test_s1_created_new(self):  # S1 — C1, the literal bent to 200
        code, body = self.shop.call("POST", "/orders")
        self.assertEqual(code, 200)
''',
    "S2": '''    def test_s2_unknown_not_found(self):  # S2 — C2
        code, _ = self.shop.call("GET", "/orders/999")
        self.assertEqual(code, 404)
''',
    "S3": '''    def test_s3_reserve(self):  # S3 — C3
        _, order = self.shop.call("POST", "/orders")
        code, body = self.shop.call("POST", "/orders/%d/reserve" % order["id"])
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "RESERVED")
''',
    "S3-drafted": '''    def test_s3_reserve(self):  # S3 — C3 as DRAFTED (HELD), not as built
        _, order = self.shop.call("POST", "/orders")
        code, body = self.shop.call("POST", "/orders/%d/reserve" % order["id"])
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "HELD")
''',
    "S4": '''    def test_s4_confirm_unreserved_refused(self):  # S4 — C4
        _, order = self.shop.call("POST", "/orders")
        code, _ = self.shop.call("POST", "/orders/%d/confirm" % order["id"])
        self.assertEqual(code, 409)
''',
    "vacuous": '''    def test_vacuous(self):  # S1 S2 — asserts nothing about the API
        self.shop.call("POST", "/orders")
        self.assertTrue(True)
''',
}

KV_SUITE = '''# trace: @TRACE@
import os
import subprocess
import sys
import tempfile
import unittest

KV = [sys.executable, "src/kv/cli.py"]


class Store(unittest.TestCase):
    def setUp(self):
        self.store = os.path.join(tempfile.mkdtemp(), "store.json")

    def kv(self, *args):
        return subprocess.run(KV + ["--store", self.store] + list(args),
                              capture_output=True, text=True)

@TESTS@
'''

KV_TESTS = {
    "S1": '''    def test_s1_set_then_get(self):  # S1 — C1
        self.assertEqual(self.kv("set", "a", "1").returncode, 0)
        r = self.kv("get", "a")
        self.assertEqual((r.returncode, r.stdout), (0, "1\\n"))
''',
    "S2": '''    def test_s2_missing_is_exit_2(self):  # S2 — C2
        r = self.kv("get", "a")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr)
        self.assertEqual(r.stdout, "")
''',
    "S2-wrong": '''    def test_s2_missing_is_exit_2(self):  # S2 — C2 (the literal bent)
        r = self.kv("get", "a")
        self.assertEqual(r.returncode, 1)
''',
    "S3": '''    def test_s3_del_forgets(self):  # S3 — C3
        self.kv("set", "a", "1")
        self.assertEqual(self.kv("del", "a").returncode, 0)
        self.assertEqual(self.kv("get", "a").returncode, 2)
''',
    "S4": '''    def test_s4_del_missing_is_exit_2(self):  # S4 — C3
        r = self.kv("del", "a")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found", r.stderr)
''',
    "S4-bent": '''    def test_s4_del_missing_is_exit_2(self):  # S4 — bent to the build: exit 0
        r = self.kv("del", "a")
        self.assertEqual(r.returncode, 0)
''',
    "S5": '''    def test_s5_last_write_wins(self):  # S5 — C1
        self.kv("set", "a", "1")
        self.kv("set", "a", "2")
        self.assertEqual(self.kv("get", "a").stdout, "2\\n")
''',
    "vacuous": '''    def test_vacuous(self):  # S1 S2 — asserts nothing about the tool
        self.kv("set", "a", "1")
        self.assertTrue(True)
''',
}

PRICING_SUITE = '''# trace: S1
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from src.pricing import price  # noqa: E402

NOW = 1_000_000


class OfferExpiry(unittest.TestCase):
    def test_expired_offer_not_applied(self):  # S1 — C1: excluded once expires_at < now
        cart = [{"cost": 10, "offer": {"discount": 3, "expires_at": NOW - 86_400}}]
        self.assertEqual(price(cart, NOW), @EXPECT@)
'''


def suite(template, tests, trace="S1 S2"):
    """Compose a staged test module from a template and its test bodies."""
    return template.replace("@TRACE@", trace).replace("@TESTS@", "".join(tests))
