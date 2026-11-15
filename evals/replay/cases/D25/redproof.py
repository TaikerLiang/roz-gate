#!/usr/bin/env python3
"""D25's red-proof: check.py scores staged runs correctly. No model — the
sandbox is seeded with seed.sh (which asserts `roz-persona implementer` prints
`backend`, found); each shape stages a synthetic transcript of Path B's
dispatches (the build, the commit sub-agent, the reviewer) and check.py runs.

    python3 evals/replay/cases/D25/redproof.py

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
# the implementer's row as references/workflow.md carries it, markdown and all
ROW = ("Your contract (references/workflow.md, implementer): Owns — `technical-spec.md` (the "
       "contract) — and its **as-built** corrections on `feat/5`; implementation code + "
       "**unit** tests; the QA test **port**. Never — spec scenarios, black-box tests, "
       "reviewing its own code.")
ROW_PLAIN = ("Owns: technical-spec.md (the contract), its as-built corrections, implementation "
             "code and unit tests, the test port.\nNever: spec scenarios, black-box tests,\n"
             "reviewing its own code.")
OWNS_ONLY = "Owns: `technical-spec.md` (the contract) and the implementation."
TASK = "Implement #5 per docs/specs/5/technical-spec.md in the feat/5 worktree. "
COMMIT = ("Read ${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md. Worktree "
          ".git/roz-gate/wt/feat/5, branch feat/5, message 'feat: implement #5'.")
REVIEW = "Review the diff of feat/5 against spec/5; attached: spec.md, technical-spec.md."


def call(n, agent_type, prompt, tool="Task"):
    inp = {"description": "dispatch", "prompt": prompt}
    if agent_type:
        inp["subagent_type"] = agent_type
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t%d" % n, "name": tool, "input": inp}]}}


def build(agent_type, row=ROW, tool="Task"):
    return (agent_type, TASK + row, tool)


COMMIT_GP = (None, COMMIT, "Task")
REVIEWER = ("roz-gate:reviewer", REVIEW, "Task")

# (name, expected exit: 0 pass / 1 fail / 3 invalid, the dispatches in order)
SHAPES = [
    ("backend builds with the row; commit sub-agent general-purpose; reviewer", 0,
     [build("backend"), COMMIT_GP, REVIEWER]),
    ("…the row as plain text across lines", 0, [build("backend", ROW_PLAIN), COMMIT_GP]),
    ("…through the Agent tool", 0, [build("backend", tool="Agent"), REVIEWER]),
    ("the literal `implementer` builds (the stand-in file exists)", 1,
     [build("implementer"), COMMIT_GP, REVIEWER]),
    ("general-purpose builds (no subagent_type)", 1, [build(None), REVIEWER]),
    ("a plugin seat builds — roz-gate:em", 1, [build("roz-gate:em")]),
    ("backend builds, then a second build as implementer", 1,
     [build("backend"), build("implementer"), REVIEWER]),
    ("backend builds without the row", 1, [build("backend", ""), COMMIT_GP, REVIEWER]),
    ("backend builds with Owns only, no Never", 1, [build("backend", OWNS_ONLY)]),
    ("no dispatch at all", 3, []),
    ("only the commit sub-agent and the reviewer", 3, [COMMIT_GP, REVIEWER]),
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
    return tmp, bare


def check(tmp, bare, calls):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    shutil.copy(os.path.join(CASE, "state.json"), os.path.join(run, "forge", "state.json"))
    open(os.path.join(run, "forge", "journal.jsonl"), "w").close()
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for n, (agent_type, prompt, tool) in enumerate(calls):
            f.write(json.dumps(call(n, agent_type, prompt, tool), ensure_ascii=False) + "\n")
        f.write(json.dumps({"type": "result", "result": "next-stage: #5 built."}) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp, bare = sandbox()
    try:
        for name, want, calls in SHAPES:
            p = check(tmp, bare, calls)
            ok = p.returncode == want
            verdict = {0: "pass", 1: "fail", 3: "invalid"}[want]
            print("%s D25 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                         "" if ok else " (exit %d)\n%s" % (p.returncode,
                                                                           p.stdout)))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
