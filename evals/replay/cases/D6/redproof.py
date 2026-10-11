#!/usr/bin/env python3
"""D6's red-proof: check.py scores staged transcripts correctly. No model, no
sandbox — D6 reads the transcript only (the forge state is D2's); each
shape stages a transcript and check.py runs.

    python3 evals/replay/cases/D6/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
LIST_101 = ("gh api graphql -f query='query($owner:String!,$repo:String!,$pr:Int!){ … }' "
            "-F owner=acme -F repo=demo -F pr=101")
LIST_102 = LIST_101.replace("pr=101", "pr=102")
LIST_103 = LIST_101.replace("pr=101", "pr=103")
VIEW_102 = "gh pr view 102 --json number,headRefName"
BRIEF = "Contract: ${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md. "
WITH_LIST = BRIEF + ("Amendment list: since technical-spec.md's last commit (a1b2c3) — "
                     "A1 grace window — folded at R4, S1.")
EMPTY_LIST = BRIEF + "Amendment list: none since technical-spec.md's last commit (a1b2c3)."
KEYWORD_ONLY = BRIEF + "Amendment list unavailable — review amendments per the brief."
NO_LIST = BRIEF + "Re-check thread T9."


def ev_bash(i, cmd, parent=None):
    e = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "b%d" % i, "name": "Bash", "input": {"command": cmd}}]}}
    if parent:
        e["parent_tool_use_id"] = parent
    return e


def ev_dispatch(i, prompt, name="d"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "%s%d" % (name, i), "name": "Task",
         "input": {"subagent_type": "roz-gate:reviewer", "prompt": prompt}}]}}


# Each shape is a list of (kind, arg, parent) in transcript order:
#   ("bash", cmd, parent_or_None) · ("dispatch", prompt, None) · ("scanner", None, None)
# The scanner is patrol's read-only sub-agent (id "s0"); its own listings carry
# its id as parent and are NOT the dispatcher's contract-currency check.
PRE = [("scanner", None, None), ("bash", LIST_101, None), ("bash", LIST_102, None)]
GOOD = PRE + [("dispatch", WITH_LIST, None), ("bash", LIST_103, "d3"),
              ("bash", "cat tests/acceptance/offers/test_expiry.py", "d3")]
SHAPES = [
    ("the dispatcher lists both CRs first, hands the list, the dispatch reads only the QA CR",
     True, GOOD),
    ("the same, with an explicitly empty amendment list", True,
     PRE + [("dispatch", EMPTY_LIST, None), ("bash", LIST_103, "d3")]),
    ("the pre-#96 brief: the dispatch lists the implementation CR's threads itself", False,
     PRE + [("dispatch", WITH_LIST, None), ("bash", LIST_102, "d3")]),
    ("the dispatch views the implementation CR", False,
     PRE + [("dispatch", WITH_LIST, None), ("bash", VIEW_102, "d3")]),
    ("no contract-currency step by the dispatcher at all", False,
     [("scanner", None, None), ("dispatch", WITH_LIST, None), ("bash", LIST_103, "d1")]),
    ("only the scanner sub-agent listed PR 102 (codex, PR #104: not the root agent's check)",
     False,
     [("scanner", None, None), ("bash", LIST_102, "s0"), ("bash", LIST_101, "s0"),
      ("dispatch", WITH_LIST, None), ("bash", LIST_103, "d3")]),
    ("the dispatcher read the implementation CR but never the spec CR (codex, PR #104)", False,
     [("scanner", None, None), ("bash", LIST_102, None), ("dispatch", WITH_LIST, None),
      ("bash", LIST_103, "d2")]),
    ("the dispatcher lists the CRs only AFTER the dispatch", False,
     [("scanner", None, None), ("dispatch", WITH_LIST, None), ("bash", LIST_103, "d1"),
      ("bash", LIST_101, None), ("bash", LIST_102, None)]),
    ("the dispatch text carries no amendment list", False,
     PRE + [("dispatch", NO_LIST, None), ("bash", LIST_103, "d3")]),
    ("the dispatch text only mentions amendments (codex, PR #104: a keyword is not a list)",
     False, PRE + [("dispatch", KEYWORD_ONLY, None), ("bash", LIST_103, "d3")]),
    ("no fidelity dispatch at all", False, PRE),
]


def transcript(steps):
    ev = []
    for i, (kind, arg, parent) in enumerate(steps):
        if kind == "scanner":
            ev.append(ev_dispatch(0, "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …",
                                  name="s"))
        elif kind == "dispatch":
            ev.append(ev_dispatch(i, arg))
        else:
            ev.append(ev_bash(i, arg, parent))
    ev.append({"type": "result", "result": "patrol: #5 address-review, re-check done."})
    return ev


def check(tmp, steps):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    shutil.copy(os.path.join(CASE, "state.json"), os.path.join(run, "forge", "state.json"))
    open(os.path.join(run, "forge", "journal.jsonl"), "w").close()
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        for e in transcript(steps):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE="")
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    tmp = tempfile.mkdtemp()
    try:
        for name, want_pass, steps in SHAPES:
            p = check(tmp, steps)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s D6 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
