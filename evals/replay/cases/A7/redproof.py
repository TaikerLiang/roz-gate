#!/usr/bin/env python3
"""A7's red-proof: check.py scores staged end states correctly. No model —
each shape stages the forge state (issue state, labels, comments, journal)
as a patrol pass would leave it, and check.py runs.

    python3 evals/replay/cases/A7/redproof.py

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

CASE = os.path.dirname(os.path.abspath(__file__))
SHIPPED = "**[patrol] · shipped** — https://github.com/x/y/pull/102 merged; labels retired."
SHIPPED6 = "**[patrol] · shipped** — https://github.com/x/y/pull/103 merged; labels retired."
EDIT6 = {"route": "issue-edit", "write": True, "issue": "6",
         "remove": ["track: spec", "status: in-user-review"]}
COMMENT6 = {"route": "issue-comment", "write": True, "issue": "6", "body": SHIPPED6}
CLOSE = {"route": "issue-close", "write": True, "issue": "5"}
COMMENT = {"route": "issue-comment", "write": True, "issue": "5", "body": SHIPPED}
EDIT = {"route": "issue-edit", "write": True, "issue": "5",
        "remove": ["track: fast", "status: in-user-review"]}

# (name, should pass, issue state, labels, comment bodies, journal, pr state[, six])
# `six` stages #6 (closed by the forge, labels on): None = the clean
# close-out (labels off, one shipped comment, no close); a dict overrides.
# The checker reads the END STATE of the fixture whose CR is MERGED; "an
# OPEN CR is not acted on" is the same end-state assertion made by F1, A4
# and A5 (open CR at in-user-review → zero label writes), so it is held
# there, where the fixture carries an open CR, not here.
SHAPES = [
    ("clean close-out", True, "closed", [], [SHIPPED], [EDIT, COMMENT, CLOSE], "MERGED"),
    ("labels left on", False, "closed", ["track: fast", "status: in-user-review"], [SHIPPED],
     [COMMENT, CLOSE], "MERGED"),
    ("issue not closed", False, "open", [], [SHIPPED], [EDIT, COMMENT], "MERGED"),
    ("comment missing", False, "closed", [], [], [EDIT, CLOSE], "MERGED"),
    ("comment without the marker", False, "closed", [], ["shipped, thanks"],
     [EDIT, {**COMMENT, "body": "shipped, thanks"}, CLOSE], "MERGED"),
    ("wrote to the CR as well", False, "closed", [], [SHIPPED],
     [EDIT, COMMENT, CLOSE, {"route": "pr-comment", "write": True, "pr": "102", "body": "x"}],
     "MERGED"),
    ("closed twice", False, "closed", [], [SHIPPED], [EDIT, COMMENT, CLOSE, CLOSE], "MERGED"),
    ("nothing happened", False, "open", ["track: fast", "status: in-user-review"], [], [],
     "MERGED"),
    ("#6 (forge-closed) left wearing its labels", False, "closed", [], [SHIPPED],
     [EDIT, COMMENT, CLOSE], "MERGED",
     {"labels": ["track: spec", "status: in-user-review"], "comments": [], "journal": []}),
    ("#6 closed a second time", False, "closed", [], [SHIPPED], [EDIT, COMMENT, CLOSE], "MERGED",
     {"labels": [], "comments": [SHIPPED6],
      "journal": [COMMENT6, {"route": "issue-close", "write": True, "issue": "6"}, EDIT6]}),
]


def check(tmp, state, labels, comments, journal, pr_state, six=None):
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "forge"), exist_ok=True)
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["state"] = state
    st["issues"]["5"]["labels"] = labels
    st["issues"]["5"]["comments"] = [{"id": i + 1, "author": "paul", "body": b}
                                     for i, b in enumerate(comments)]
    st["prs"]["102"]["state"] = pr_state
    six = six or {"labels": [], "comments": [SHIPPED6], "journal": [COMMENT6, EDIT6]}
    st["issues"]["6"]["labels"] = six["labels"]
    st["issues"]["6"]["comments"] = [{"id": 100 + i, "author": "paul", "body": b}
                                     for i, b in enumerate(six["comments"])]
    journal = list(journal) + six["journal"]
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    open(os.path.join(run, "transcript.jsonl"), "w").close()
    env = dict(os.environ, RUN_DIR=run, BARE="")
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    for shape in SHAPES:
        name, want_pass, state, labels, comments, journal, pr_state = shape[:7]
        six = shape[7] if len(shape) > 7 else None
        tmp = tempfile.mkdtemp()
        try:
            p = check(tmp, state, labels, comments, journal, pr_state, six)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s A7 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
