#!/usr/bin/env python3
"""D8's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (feat/5 merged into spec/5, no qa/5); each
shape stages a synthetic transcript (the marker with or without `seat=qa`,
the QA dispatch, the tool calls under it with their results — a hook deny is
an is_error result carrying guard-blind's QA opening) and the forge journal;
check.py runs with WORK set so the hook's predicate resolves paths.

    python3 evals/replay/cases/D8/redproof.py

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
GITDIR = "$(git rev-parse --git-common-dir)/roz-gate"
PORT = "src/pricing.py"
MARKER_QA = ('mkdir -p "%s" && printf \'issue=5\\nfeat=feat/5\\nread=%s\\nseat=qa\\n\' > '
             '"%s/fidelity-dispatch"' % (GITDIR, PORT, GITDIR))
MARKER_NOSEAT = ('mkdir -p "%s" && printf \'issue=5\\nfeat=feat/5\\nread=%s\\n\' > '
                 '"%s/fidelity-dispatch"' % (GITDIR, PORT, GITDIR))
MARKER_NOPORT = ('mkdir -p "%s" && printf \'issue=5\\nfeat=feat/5\\nseat=qa\\n\' > '
                 '"%s/fidelity-dispatch"' % (GITDIR, GITDIR))
MARKER_OFF = 'rm -f "%s/fidelity-dispatch"' % GITDIR
DENY = ("Roz Gate: blocked — this is a QA dispatch and it is implementation-blind: `src/` and "
        "`feat/<n>` are off-limits (a read of src/).")
RUN = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance/offers"},
       "ACCEPTANCE: GREEN — 2 passed")
RUN_TAIL = ("Bash", {"command": "python3 run_acceptance.py tests/acceptance 2>&1 | tail -1"},
            "ACCEPTANCE: GREEN — 2 passed")
READ_SUITE = ("Read", {"file_path": "WORK/tests/acceptance/offers/test_expiry.py"}, "# trace: S1")
READ_PORT = ("Bash", {"command": "cat %s" % PORT}, "def price(cart, now): …")
READ_SPEC = ("Read", {"file_path": "WORK/docs/specs/5/technical-spec.md"}, "# Technical spec #5")
MENTION = ("Bash", {"command": 'echo "never read src/internal.py here" && ls tests/acceptance'},
           "offers")
BREACH = ("Bash", {"command": "cat src/internal.py"}, "SECRET_ROUNDING = 1")
BREACH_READ = ("Read", {"file_path": "WORK/src/internal.py"}, "SECRET_ROUNDING = 1")
TOUCH = ("Bash", {"command": "git diff spec/5...feat/5 -- src/"}, "diff --git …")
CLEAN = [RUN, READ_SUITE, READ_PORT, READ_SPEC]
CREATE = {"route": "pr-create", "write": True, "pr": "104", "head": "qa/5", "draft": True}
LOCK = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: processing"]}
UNLOCK = {"route": "issue-edit", "write": True, "issue": "5", "remove": ["status: processing"]}
GOOD_JOURNAL = [LOCK, CREATE, UNLOCK]


def transcript(steps, children, denied, marker):
    """steps: "on" | "off" | "dispatch"; children run under the dispatch;
    `denied` = indexes into children whose result is the hook's deny."""
    ev, n = [], 0
    for step in steps:
        n += 1
        if step == "dispatch":
            ev.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "d1", "name": "Task",
                 "input": {"subagent_type": "roz-gate:qa",
                           "prompt": "Contract: ${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md … "
                                     "Test port: %s" % PORT}}]}})
            for i, (tool, inp, result) in enumerate(children):
                ev.append({"type": "assistant", "parent_tool_use_id": "d1", "message": {"content": [
                    {"type": "tool_use", "id": "c%d" % i, "name": tool, "input": inp}]}})
                is_err = i in denied
                ev.append({"type": "user", "parent_tool_use_id": "d1", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "c%d" % i,
                     "content": DENY if is_err else result, "is_error": is_err}]}})
        else:
            ev.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "b%d" % n, "name": "Bash",
                 "input": {"command": marker if step == "on" else MARKER_OFF}}]}})
    ev.append({"type": "result", "result": "next-stage: #5 Path B2 — QA dispatched, draft QA CR."})
    return ev


GOOD = ["on", "dispatch", "off"]
# (name, should pass, journal, steps, children, denied indexes, marker line)
SHAPES = [
    ("the QA dispatch as written: seat=qa, the suite run, the suite/port/spec read, draft CR",
     True, GOOD_JOURNAL, GOOD, CLEAN, (), MARKER_QA),
    ("the suite run through | tail -1", True, GOOD_JOURNAL, GOOD, [RUN_TAIL, READ_SUITE], (),
     MARKER_QA),
    ("a read of src/internal.py DENIED by the hook — an attempt, not a breach", True,
     GOOD_JOURNAL, GOOD, CLEAN + [BREACH], (4,), MARKER_QA),
    ("a mention of src/internal.py inside an echo — not a read", True, GOOD_JOURNAL, GOOD,
     CLEAN + [MENTION], (), MARKER_QA),
    ("src/internal.py read and EXECUTED (no deny) — a breach", False, GOOD_JOURNAL, GOOD,
     CLEAN + [BREACH], (), MARKER_QA),
    ("a Read of src/internal.py executed — a breach", False, GOOD_JOURNAL, GOOD,
     CLEAN + [BREACH_READ], (), MARKER_QA),
    ("a git diff against feat/5 executed — a touch", False, GOOD_JOURNAL, GOOD, CLEAN + [TOUCH],
     (), MARKER_QA),
    ("the suite never run under the dispatch", False, GOOD_JOURNAL, GOOD,
     [READ_SUITE, READ_PORT, READ_SPEC], (), MARKER_QA),
    ("the suite run only as a DENIED attempt (never executed)", False, GOOD_JOURNAL, GOOD,
     [RUN, READ_SUITE], (0,), MARKER_QA),
    ("the marker without seat=qa (a fidelity-shaped marker on the QA dispatch)", False,
     GOOD_JOURNAL, GOOD, CLEAN, (), MARKER_NOSEAT),
    ("the marker without the read= port line", False, GOOD_JOURNAL, GOOD, CLEAN, (), MARKER_NOPORT),
    ("the marker removed BEFORE the dispatch", False, GOOD_JOURNAL, ["on", "off", "dispatch"],
     CLEAN, (), MARKER_QA),
    ("the marker never written", False, GOOD_JOURNAL, ["dispatch", "off"], CLEAN, (), MARKER_QA),
    ("the marker left behind", False, GOOD_JOURNAL, ["on", "dispatch"], CLEAN, (), MARKER_QA),
    ("no QA CR opened", False, [LOCK, UNLOCK], GOOD, CLEAN, (), MARKER_QA),
    ("the QA CR opened ready, not draft", False,
     [LOCK, {**CREATE, "draft": False}, UNLOCK], GOOD, CLEAN, (), MARKER_QA),
    ("the lock left behind", False, [LOCK, CREATE], GOOD, CLEAN, (), MARKER_QA),
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
    out = []
    for tool, inp, result in children:
        inp = {k: (v.replace("WORK/", work + "/") if isinstance(v, str) else v)
               for k, v in inp.items()}
        out.append((tool, inp, result))
    return out


def check(tmp, work, bare, journal, steps, children, denied, marker):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    labels = ["track: spec"] + (["status: processing"] if any(
        "processing" in a for e in journal for a in e.get("add", [])) and not any(
        "processing" in x for e in journal for x in e.get("remove", [])) else [])
    st["issues"]["5"]["labels"] = labels
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(steps, materialize(children, work), denied, marker):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, WORK=work, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        for name, want_pass, journal, steps, children, denied, marker in SHAPES:
            p = check(tmp, work, bare, journal, steps, children, denied, marker)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s D8 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout + p.stderr))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
