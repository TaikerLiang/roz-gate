#!/usr/bin/env python3
"""D26's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (which asserts `roz-persona implementer`
answers PERSONA_UNMAPPED); each shape stages the forge (#5's labels and
comments, the journal), a synthetic transcript, and what a run might have
pushed; check.py runs.

    python3 evals/replay/cases/D26/redproof.py

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
STOP = ("**[next-stage] · blocked** — the implementer seat has no agent: `roz-persona` "
        "answered `PERSONA_UNMAPPED` (no `implementer` line, no "
        ".claude/agents/implementer.md). Nothing was written. Run `/roz-gate:init` to seat it."
        "\n\n**To resume:** clear `status: blocked`, apply `status: ready-for-dev` — yourself, "
        "or tell the main agent; nothing to answer — run the remedy first.")
BLOCKED = ["track: spec", "status: blocked"]
LABELS = {"route": "issue-edit", "write": True, "issue": "5", "add": ["status: blocked"],
          "remove": ["status: ready-for-dev"]}


def comment(body):
    return {"route": "issue-comment", "write": True, "issue": "5", "body": body}


def dispatch(agent_type):
    inp = {"description": "build #5", "prompt": "Implement #5 per technical-spec.md."}
    if agent_type:
        inp["subagent_type"] = agent_type
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Task", "input": inp}]}}


PUSH = ("git checkout -q -b feat/5 spec/5 && echo x > src/pricing.py && git add -A "
        "&& git commit -qm impl && git push -q origin feat/5")

# (name, should pass, labels, comments on #5, journal, dispatches, shell before)
SHAPES = [
    ("the STOP: blocked alone, the comment names both, no dispatch", True, BLOCKED, [STOP],
     [LABELS, comment(STOP)], [], None),
    ("the comment lacks /roz-gate:init", False, BLOCKED,
     [STOP.replace("Run `/roz-gate:init` to seat it.", "Seat it.")],
     [LABELS, comment("…")], [], None),
    ("the comment lacks PERSONA_UNMAPPED", False, BLOCKED,
     [STOP.replace("`PERSONA_UNMAPPED`", "nothing")], [LABELS, comment("…")], [], None),
    ("the gate label left beside blocked", False,
     ["track: spec", "status: ready-for-dev", "status: blocked"], [STOP],
     [comment(STOP)], [], None),
    ("the lock left behind", False, ["track: spec", "status: processing", "status: blocked"],
     [STOP], [comment(STOP)], [], None),
    ("a do-nothing run", False, ["track: spec", "status: ready-for-dev"], [], [], [], None),
    ("a stand-in dispatched as general-purpose, then the STOP", False, BLOCKED, [STOP],
     [LABELS, comment(STOP)], [None], None),
    ("a stand-in dispatched as implementer", False, BLOCKED, [STOP],
     [LABELS, comment(STOP)], ["implementer"], None),
    ("the spec-gate kit stamped (B2's COMMENT-EDIT) before the STOP", False, BLOCKED, [STOP],
     [{"route": "comment-edit", "write": True, "comment": "9501", "body": "approved at x"},
      LABELS, comment(STOP)], [], None),
    ("a comment on the spec CR", False, BLOCKED, [STOP],
     [LABELS, comment(STOP), {"route": "pr-comment", "write": True, "pr": "101",
                              "body": "blocked"}], [], None),
    ("a CR opened", False, BLOCKED, [STOP],
     [LABELS, comment(STOP), {"route": "pr-create", "write": True, "head": "feat/5"}], [],
     None),
    ("a branch pushed", False, BLOCKED, [STOP], [LABELS, comment(STOP)], [], PUSH),
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
            raise RuntimeError("sandbox step failed: %s\n%s" % (cmd, p.stdout + p.stderr))
    return tmp, work, bare


def check(tmp, bare, labels, comments, journal, dispatches):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = labels
    st["issues"]["5"]["comments"] = [{"author": "paul", "body": b} for b in comments]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for t in dispatches:
            f.write(json.dumps(dispatch(t)) + "\n")
        f.write(json.dumps({"type": "result", "result": "next-stage: #5 blocked."}) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp, work, bare = sandbox()
    try:
        # the one shape that moves the remote comes last — one sandbox serves them all
        for name, want_pass, labels, comments, journal, dispatches, before in SHAPES:
            if before:
                setup = sh(before, work)
                if setup.returncode != 0:
                    raise RuntimeError("shape setup failed: %s\n%s" % (before, setup.stderr))
            p = check(tmp, bare, labels, comments, journal, dispatches)
            ok = (p.returncode == 0) == want_pass and p.returncode in (0, 1)
            verdict = "pass" if want_pass else "fail"
            print("%s D26 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else " (exit %d)\n%s" % (p.returncode,
                                                                           p.stdout)))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
