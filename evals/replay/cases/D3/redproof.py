#!/usr/bin/env python3
"""D3's red-proof: check.py scores staged runs correctly. No model, no
sandbox — D3 reads the transcript's dispatch payloads and the forge state;
each shape stages a product dispatch and #9's comments, and check.py runs.

    python3 evals/replay/cases/D3/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
BRIEF = ("Read the intake brief and follow it exactly: "
         "${CLAUDE_PLUGIN_ROOT}/references/intake-brief.md")
ROW = ("You are the product seat for issue #9. Your R&R row (workflow.md): Owns: actors, "
       "scenarios (Given/When/Then), consistency, user-facing gaps. Never: architecture, code, "
       "impl tests. " + BRIEF)
# D3/run-1 of the 2026-11-15 sweep: the Never column in prose (#330).
PARAPHRASE = ("You are the product seat for issue #9. Your role & responsibilities (R&R row): "
              "actors, scenarios (Given/When/Then: happy/edge/failure), consistency, user-facing "
              "gaps. Architecture, code and implementation tests are NOT yours.\n\n" + BRIEF)
OWNS_ONLY = ("You are the product seat for issue #9. Your R&R row: actors, scenarios, "
             "consistency, user-facing gaps. " + BRIEF)
NO_CODE = PARAPHRASE.replace("Architecture, code and implementation tests",
                             "Architecture and implementation tests")
NO_TESTS = PARAPHRASE.replace("Architecture, code and implementation tests",
                              "Architecture and code")
NO_ROW = "You are the product seat for issue #9. " + BRIEF
BATCH = "**[intake]**\n\n**3 questions** · Discuss freely below.\n\n1. Who receives it? (a) …"

# (name, should pass, dispatch prompt or None, #9's comments)
SHAPES = [
    ("the dispatch carries the row verbatim, the batch posted", True, ROW, [BATCH]),
    ("the Never column in prose: architecture, code and implementation tests (#330)", True,
     PARAPHRASE, [BATCH]),
    ("no R&R row in the payload at all (D3/run-3)", False, NO_ROW, [BATCH]),
    ("only the Owns column", False, OWNS_ONLY, [BATCH]),
    ("the Never column without code", False, NO_CODE, [BATCH]),
    ("the Never column without implementation tests", False, NO_TESTS, [BATCH]),
    ("no product dispatch at all", False, None, [BATCH]),
    ("the row carried, but no intake batch posted", False, ROW, []),
]


def transcript(prompt):
    ev = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "s0", "name": "Task",
         "input": {"subagent_type": "general-purpose",
                   "prompt": "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …"}}]}}]
    if prompt is not None:
        ev.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "p1", "name": "Task",
             "input": {"subagent_type": "roz-gate:product", "prompt": prompt}}]}})
    ev.append({"type": "result", "result": "patrol: #9 intake batch posted."})
    return ev


def check(tmp, prompt, comments):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["9"]["comments"] = [{"id": 901 + i, "author": "paul", "body": b,
                                      "createdAt": "2026-08-24T12:00:00Z"}
                                     for i, b in enumerate(comments)]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    open(os.path.join(run, "forge", "journal.jsonl"), "w").close()
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(prompt):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE="")
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp = tempfile.mkdtemp()
    try:
        for name, want_pass, prompt, comments in SHAPES:
            p = check(tmp, prompt, comments)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s D3 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
