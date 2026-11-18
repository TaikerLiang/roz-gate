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
# The scanner brief as the 2026-11-15 runs wrote it (#327): it names
# patrol-scan.md and says "fidelity", because the scan classifies
# fidelity-audit rows.
SCANNER_FIDELITY = ("You are the patrol SCANNER for the Roz Gate loop. You are READ-ONLY. "
                    "Step 1 — Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md; classify "
                    "every row, fidelity-audit rows included, and return the table.")
# D6/run-3 of the 2026-11-17/18 sweep (#384): the commit helper's brief carries a commit
# message that says "fidelity". It is no seat dispatch and never carries the list.
COMMIT_HELPER = ("You are the COMMIT sub-agent. Your brief is the file "
                 "${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md — read it first.\n"
                 "1. Worktree path: .git/roz-gate/wt/spec/5\n2. Branch checked out there: spec/5\n"
                 "4. Commit message, verbatim (use a heredoc):\nspec: #5 QA questions Q1-Q2 "
                 "(open)\n\nRaised by qa in the fidelity/contract review of the QA suite: Q1 "
                 "(offer-applied response shape) and Q2 (expired-offer seed port).")
# A QA seat dispatch whose text never says "fidelity" or "qa/5" is still one: the seat
# selects it (#384).
QA_NO_LIST = ("Seat: qa. Your contract: ${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md — read "
              "it first. Address the open thread on the QA CR in your worktree.")


def ev_bash(i, cmd, parent=None):
    e = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "b%d" % i, "name": "Bash", "input": {"command": cmd}}]}}
    if parent:
        e["parent_tool_use_id"] = parent
    return e


def ev_dispatch(i, prompt, name="d", seat="roz-gate:reviewer"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "%s%d" % (name, i), "name": "Task",
         "input": {"subagent_type": seat, "prompt": prompt}}]}}


# Each shape is a list of (kind, arg, parent) in transcript order:
#   ("bash", cmd, parent_or_None) · ("dispatch", prompt, seat_or_None — the reviewer)
#   · ("scanner", prompt_or_None, None) · ("helper", prompt, None — a general-purpose agent)
# The scanner is patrol's read-only sub-agent (id "s0"); its own listings carry
# its id as parent and are NOT the dispatcher's contract-currency check, and
# its dispatch is NOT a fidelity dispatch even when its brief says "fidelity".
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
    ("the scanner's brief says fidelity and it reads PR 102, before the root listings "
     "(#327: the scanner is not a fidelity dispatch)", True,
     [("scanner", SCANNER_FIDELITY, None), ("bash", LIST_102, "s0"), ("bash", LIST_101, "s0"),
      ("bash", LIST_101, None), ("bash", LIST_102, None), ("dispatch", WITH_LIST, None),
      ("bash", LIST_103, "d5")]),
    ("only the scanner's brief says fidelity — no seat dispatch (#327)", False,
     [("scanner", SCANNER_FIDELITY, None), ("bash", LIST_102, "s0"),
      ("bash", LIST_101, None), ("bash", LIST_102, None)]),
    ("the list handed, then the commit helper commits a message saying fidelity (#384, "
     "D6/run-3)", True, GOOD + [("helper", COMMIT_HELPER, None)]),
    ("the list handed to the reviewer, a QA seat dispatched without it (#384: the seat "
     "selects)", False, GOOD + [("dispatch", QA_NO_LIST, "roz-gate:qa")]),
]


def transcript(steps):
    ev = []
    for i, (kind, arg, parent) in enumerate(steps):
        if kind == "scanner":
            prompt = arg or "Read ${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md …"
            ev.append(ev_dispatch(0, prompt, name="s", seat="general-purpose"))
        elif kind == "dispatch":
            ev.append(ev_dispatch(i, arg, seat=parent or "roz-gate:reviewer"))
        elif kind == "helper":
            ev.append(ev_dispatch(i, arg, name="h", seat="general-purpose"))
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
