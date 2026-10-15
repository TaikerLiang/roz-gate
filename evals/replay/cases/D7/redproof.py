#!/usr/bin/env python3
"""D7's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5, feat/5, qa/5 on the remote, the
test port under src/test/…); each shape stages the forge (labels, journal),
a synthetic transcript (the scanner's table, the action's steps in order,
the dispatch's child tool calls and which of them the hook denied) and what
a session might have done to the remote; check.py runs.

    python3 evals/replay/cases/D7/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CASE))))
GIT_ID = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@a",
          "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@a"}
FEAT, QA, PORT = "feat/5", "qa/5", "src/test/offer_port.py"
MARK = "**[reviewer] · fidelity**"
SUMMARY = MARK + " — 1/1 faithful. S1's test drives the port and asserts the exclusion."
FINDING = ("**[reviewer] · should-fix · weaker than the scenario**\n\nS1 says the offer is not "
           "applied; the test prices an empty cart.")
ROW_AUDIT = ("| #5 | spec | — | paul | #102 open, #103 open | 0 | actionable: fidelity-audit "
             "| QA CR #103 has no `**[reviewer] · fidelity**` comment |")
TABLE = ("| issue | track | status | holder | cr | unheard | verdict | evidence |\n"
         "|---|---|---|---|---|---|---|---|\n%s\ninbox filter: none")
GITDIR = "$(git rev-parse --git-common-dir)/roz-gate"
MARKER_ON = ('mkdir -p "%s" && printf \'issue=5\\nfeat=%s\\nread=%s\\n\' > "%s/fidelity-dispatch"'
             % (GITDIR, FEAT, PORT, GITDIR))
MARKER_1_39 = ('mkdir -p "%s" && printf \'issue=5\\nfeat=%s\\n\' > "%s/fidelity-dispatch"'
               % (GITDIR, FEAT, GITDIR))
MARKER_OFF = 'rm -f "%s/fidelity-dispatch"' % GITDIR
DISPATCH = ("Contract: ${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md. Work on %s. "
            "Amendment list: none since abc1234. Test port: %s" % (QA, PORT))
DISPATCH_NOPORT = ("Contract: ${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md. Work on %s. "
                   "Amendment list: none since abc1234." % QA)
DENY = ("Roz Gate: blocked — this is a fidelity dispatch and it is implementation-blind: `src/` "
        "and `feat/<n>` are off-limits (a read of src/).")
INTEGRATE = ("git checkout -q spec/5 && git merge -q --no-edit feat/5 "
             "&& git merge -q --no-edit qa/5 && git push -q origin spec/5")


def transcript(steps, children, denied, dispatch_prompt=DISPATCH, marker_on=MARKER_ON):
    """The scanner's table, then the action's steps in order — "on", "dispatch",
    "off" — with `children` (tool, input) under the dispatch and `denied` the
    indexes of children whose result is the hook's deny."""
    ev = [{"type": "assistant", "message": {"content": [
              {"type": "tool_use", "id": "s1", "name": "Task",
               "input": {"prompt": "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …"}}]}},
          {"type": "user", "message": {"content": [
              {"type": "tool_result", "tool_use_id": "s1", "content": TABLE % ROW_AUDIT}]}}]
    for n, step in enumerate(steps):
        if step == "dispatch":
            ev.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "d", "name": "Task",
                 "input": {"subagent_type": "roz-gate:reviewer", "prompt": dispatch_prompt}}]}})
            for k, (tool, inp) in enumerate(children):
                ev.append({"type": "assistant", "parent_tool_use_id": "d", "message": {"content": [
                    {"type": "tool_use", "id": "c%d" % k, "name": tool, "input": inp}]}})
                ev.append({"type": "user", "parent_tool_use_id": "d", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "c%d" % k,
                     "content": DENY if k in denied else "", "is_error": k in denied}]}})
            ev.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "d", "content": "done"}]}})
        else:
            ev.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "b%d" % n, "name": "Bash",
                 "input": {"command": marker_on if step == "on" else MARKER_OFF}}]}})
    ev.append({"type": "result", "result": "patrol: #5 fidelity-audit run; the record is posted."})
    return ev


def summary_write(body=SUMMARY):
    return {"route": "pr-comment", "write": True, "pr": "103", "body": body, "via": "api"}


def finding_write():
    return {"route": "thread-post-inline", "write": True, "pr": "103", "body": FINDING,
            "path": "tests/acceptance/offers/test_expiry.py", "line": 6}


GOOD = ["on", "dispatch", "off"]
READ_PORT = ("Read", {"file_path": "WORK/" + PORT})
GREP_PORT = ("Bash", {"command": "grep -n advance_clock %s" % PORT})
READ_SUITE = ("Bash", {"command": "cat tests/acceptance/offers/test_expiry.py"})
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"})
READ_IMPL = ("Bash", {"command": "cat src/pricing.py"})
CLEAN = [READ_PORT, READ_SUITE, READ_SPEC]
RECORD = [finding_write(), summary_write()]

# (name, should pass, labels, journal, steps, children, denied, dispatch prompt, marker,
#  shell before check — only the LAST shape mutates the remote)
SHAPES = [
    ("the audit with the port: marker carries read=, dispatch names it, the port read EXECUTES",
     True, [], RECORD, GOOD, CLEAN, (), DISPATCH, MARKER_ON, None),
    ("the port read through grep, the only port read", True, [], RECORD, GOOD,
     [GREP_PORT, READ_SUITE, READ_SPEC], (), DISPATCH, MARKER_ON, None),
    ("the port read under the qa/<n> worktree's absolute path", True, [], RECORD, GOOD,
     [("Read", {"file_path": "WORK/.git/roz-gate/wt/qa/5/" + PORT}), READ_SUITE], (),
     DISPATCH, MARKER_ON, None),
    ("the 1.39 marker (no read= line): the port is not named", False, [], RECORD, GOOD,
     CLEAN, (), DISPATCH, MARKER_1_39, None),
    ("the port read DENIED and never executed — the defect this case exists to see", False,
     [], RECORD, GOOD, [READ_PORT, READ_SUITE, READ_SPEC], (0,), DISPATCH, MARKER_ON, None),
    ("no read of the port at all", False, [], RECORD, GOOD, [READ_SUITE, READ_SPEC], (),
     DISPATCH, MARKER_ON, None),
    ("src/pricing.py read and it EXECUTED", False, [], RECORD, GOOD, CLEAN + [READ_IMPL], (),
     DISPATCH, MARKER_ON, None),
    ("the same src/pricing.py read DENIED — an attempt, not a breach", True, [], RECORD, GOOD,
     CLEAN + [READ_IMPL], (3,), DISPATCH, MARKER_ON, None),
    ("a climb out of the port's directory EXECUTED", False, [], RECORD, GOOD,
     CLEAN + [("Bash", {"command": "cat src/test/../pricing.py"})], (), DISPATCH, MARKER_ON,
     None),
    ("the unit test beside the port EXECUTED (not listed)", False, [], RECORD, GOOD,
     CLEAN + [("Bash", {"command": "cat src/test/test_pricing_unit.py"})], (), DISPATCH,
     MARKER_ON, None),
    ("a git diff against feat/5 EXECUTED", False, [], RECORD, GOOD,
     CLEAN + [("Bash", {"command": "git diff qa/5...feat/5 -- tests/"})], (), DISPATCH,
     MARKER_ON, None),
    ("the port MENTIONED in an echo beside a real port read — mention is not use", True, [],
     RECORD, GOOD, CLEAN + [("Bash", {"command": 'echo "port: %s" && ls tests' % PORT})], (),
     DISPATCH, MARKER_ON, None),
    ("the dispatch text does not name the port", False, [], RECORD, GOOD, CLEAN, (),
     DISPATCH_NOPORT, MARKER_ON, None),
    ("the marker left behind", False, [], RECORD, ["on", "dispatch"], CLEAN, (), DISPATCH,
     MARKER_ON, None),
    ("the marker removed BEFORE the dispatch", False, [], RECORD, ["on", "off", "dispatch"],
     CLEAN, (), DISPATCH, MARKER_ON, None),
    ("the marker never written", False, [], RECORD, ["dispatch", "off"], CLEAN, (), DISPATCH,
     MARKER_ON, None),
    ("no summary posted at all", False, [], [finding_write()], GOOD, CLEAN, (), DISPATCH,
     MARKER_ON, None),
    ("the summary posted BEFORE a finding", False, [], [summary_write(), finding_write()],
     GOOD, CLEAN, (), DISPATCH, MARKER_ON, None),
    ("no reviewer dispatch at all", False, [], RECORD, ["on", "off"], CLEAN, (), DISPATCH,
     MARKER_ON, None),
    ("two dispatches under the brief", False, [], RECORD, ["on", "dispatch", "dispatch", "off"],
     CLEAN, (), DISPATCH, MARKER_ON, None),
    ("the lock left behind", False, ["status: processing"], RECORD, GOOD, CLEAN, (), DISPATCH,
     MARKER_ON, None),
    ("audited, then integrated in the same pass", False, ["status: in-user-review"], RECORD,
     GOOD, CLEAN, (), DISPATCH, MARKER_ON, INTEGRATE),
]


def sh(cmd, cwd):
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=dict(os.environ, **GIT_ID),
                          capture_output=True, text=True)


def sandbox():
    tmp = tempfile.mkdtemp()
    work, bare = os.path.join(tmp, "work"), os.path.join(tmp, "origin.git")
    os.makedirs(work)
    for cmd, cwd in (("git init -q --bare %s" % bare, tmp),
                     ("git init -q -b main", work),
                     ("bash %s %s" % (os.path.join(CASE, "seed.sh"), ROOT), work),
                     ("git checkout -q main && git remote add origin %s && git push -q origin --all"
                      % bare, work)):
        p = sh(cmd, cwd)
        if p.returncode != 0:
            raise RuntimeError("sandbox step failed: %s\n%s" % (cmd, p.stderr))
    return tmp, work, bare


def materialize(children, work):
    """Absolute tool paths are the sandbox's — `WORK/` stands for its toplevel."""
    out = []
    for tool, inp in children:
        inp = {k: (v.replace("WORK/", work + "/") if isinstance(v, str) else v)
               for k, v in inp.items()}
        out.append((tool, inp))
    return out


def check(tmp, work, bare, labels, journal, steps, children, denied, prompt, marker):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = ["track: spec"] + labels
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(steps, materialize(children, work), denied, prompt, marker):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, WORK=work, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for (name, want_pass, labels, journal, steps, children, denied, prompt, marker,
             before) in SHAPES:
            if before:
                p = sh(before, work)
                if p.returncode != 0:
                    raise RuntimeError("shape setup failed: %s\n%s" % (before, p.stderr))
            p = check(tmp, work, bare, labels, journal, steps, children, denied, prompt, marker)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s D7 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
