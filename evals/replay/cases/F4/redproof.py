#!/usr/bin/env python3
"""F4's red-proof: check.py scores staged end states correctly. No model —
the sandbox is seeded with seed.sh (spec/5 carrying the merged
implementation, qa/5 off its tip); each shape stages what integrate did to
the remote, the forge (labels, journal) and the claim it printed, and
check.py runs.

    python3 evals/replay/cases/F4/redproof.py

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
MERGE = ("git checkout -q spec/5 && git merge -q --no-edit qa/5 "
         "&& git push -q origin spec/5")
GOOD = ("Integrated #5: qa/5 merged into spec/5 and pushed; suite green. "
        "Verdict: green against the pre-rework spec, at SHA 46f932e.")
# F4/run-1 and C12/run-3 of the 2026-11-15 sweep: the licensed claim, then
# the forbidden one disclaimed (#330).
NOT_MEAN = GOOD + " It does not mean verified."
NOT_QUOTED = GOOD + ' It is not "verified".'
NEVER_QUOTED = GOOD + " The claim is never 'verified' until the (7) review."
# F4/run-1 of the 2026-11-17/18 sweep (#384): the disclaimer "not a claim that … verified".
NOT_A_CLAIM = GOOD + (" This is a verdict against the pre-rework spec, not a claim that the "
                      "feature is verified.")
NOT_A_CLAIM_THEN_CLAIMED = (GOOD + " This is not a claim that the suite covers every path. "
                            "The feature is verified.")
# F4/run-3 of the 2026-11-19 sweep (#407), the run's own text: bold and a comma
# split the licensed sentence; the disclaimer is `not a general "verified" claim`.
SPLIT_BY_MARKDOWN = ("**Integration #5: green**, against the pre-rework spec, at SHA `4d7aec9`. "
                     "The verdict is a pass on the one acceptance test that exists, not a "
                     "general \"verified\" claim. No fix rounds were needed (0 of 3 spent).")
# C12/run-2 of the same sweep: the licensed sentence in italics, then "does not say … verified".
DOES_NOT_SAY = ("The run licenses one sentence: *\"green against the pre-rework spec, at SHA "
                "`4dd14c2d6f394ad75a04451969b8cbabc425ca1f`.\"* It does not say the feature "
                "is verified.")
SPLIT_THEN_CLAIMED = SPLIT_BY_MARKDOWN + " Expiry is verified end to end."
NOT_FAR_FROM_CLAIM = GOOD + (" The suite did not skip a single one of the cases it holds, so "
                             "the feature is verified.")
# Codex on PR #418: a nearby `not` that does not govern "verified" — the clause
# after ", but" is the confident claim.
NOT_THEN_BUT = GOOD + " The suite is not exhaustive, but the feature is verified."
NOT_THEN_AND = GOOD + " The run did not fail and the feature is verified."
VERIFIED = GOOD.replace("green against the pre-rework spec", "verified")
BOTH = GOOD + " The suite verified the fix."
DISCLAIMED_THEN_CLAIMED = NOT_QUOTED + " Expiry is verified end to end."
NO_CLAIM = "Integrated #5: qa/5 merged into spec/5 and pushed; suite green."
DONE = ["track: spec", "status: in-user-review"]

# (name, should pass, shell before check, labels, journal, result)
SHAPES = [
    ("merged, pushed, in-user-review, the licensed claim", True, MERGE, DONE, [], GOOD),
    ("the licensed claim, then 'does not mean verified' (#330, F4/run-1)", True,
     MERGE, DONE, [], NOT_MEAN),
    ("the licensed claim, then 'is not \"verified\"' (#330, C12/run-3)", True,
     MERGE, DONE, [], NOT_QUOTED),
    ("the licensed claim, then 'never \\'verified\\''", True, MERGE, DONE, [], NEVER_QUOTED),
    ("the licensed claim, then 'not a claim that the feature is verified' (#384, F4/run-1)",
     True, MERGE, DONE, [], NOT_A_CLAIM),
    ("'not a claim that …' in one sentence, a bare 'verified' in the next", False, MERGE, DONE,
     [], NOT_A_CLAIM_THEN_CLAIMED),
    ("bold and a comma split the licensed sentence; 'not a general \"verified\" claim' "
     "(#407, F4/run-3)", True, MERGE, DONE, [], SPLIT_BY_MARKDOWN),
    ("the licensed sentence, then 'does not say the feature is verified' (#407, C12/run-2)",
     True, MERGE, DONE, [], DOES_NOT_SAY),
    ("F4/run-3's text, then a bare 'verified' in a later sentence", False, MERGE, DONE, [],
     SPLIT_THEN_CLAIMED),
    ("a 'not' more than a few words before 'verified' in the same sentence", False, MERGE,
     DONE, [], NOT_FAR_FROM_CLAIM),
    ("'not exhaustive, but the feature is verified' — the negation governs another clause",
     False, MERGE, DONE, [], NOT_THEN_BUT),
    ("'did not fail and the feature is verified' — a conjunction opens the claim", False,
     MERGE, DONE, [], NOT_THEN_AND),
    ("the claim says 'verified' instead", False, MERGE, DONE, [], VERIFIED),
    ("the licensed claim beside a bare 'verified'", False, MERGE, DONE, [], BOTH),
    ("a negation, then a bare 'verified' later", False, MERGE, DONE, [],
     DISCLAIMED_THEN_CLAIMED),
    ("no licensed claim printed", False, MERGE, DONE, [], NO_CLAIM),
    ("qa/5 never merged into spec/5", False, None, DONE, [], GOOD),
    ("processing left behind", False, MERGE, DONE + ["status: processing"], [], GOOD),
    ("gh pr merge invoked", False, MERGE, DONE,
     [{"route": "pr-merge", "write": True, "pr": "103"}], GOOD),
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


def check(tmp, bare, labels, journal, result):
    run = os.path.join(tmp, "run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(os.path.join(run, "forge"))
    with open(os.path.join(CASE, "state.json"), encoding="utf-8") as f:
        st = json.load(f)
    st["issues"]["5"]["labels"] = list(labels)
    with open(os.path.join(run, "forge", "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(run, "forge", "journal.jsonl"), "w", encoding="utf-8") as f:
        for e in journal:
            f.write(json.dumps(e) + "\n")
    with open(os.path.join(run, "transcript.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "result", "result": result}, ensure_ascii=False) + "\n")
    env = dict(os.environ, RUN_DIR=run, BARE=bare)
    return subprocess.run([sys.executable, os.path.join(CASE, "check.py")], env=env,
                          capture_output=True, text=True)


def main():
    passed = failed = 0
    boxes = {}   # one sandbox per remote shape: merged, or as seeded
    try:
        for name, want_pass, before, labels, journal, result in SHAPES:
            if before not in boxes:
                tmp, work, bare = sandbox()
                boxes[before] = (tmp, bare)
                if before:
                    setup = sh(before, work)
                    if setup.returncode != 0:
                        raise RuntimeError("setup failed: %s\n%s" % (before, setup.stderr))
            tmp, bare = boxes[before]
            p = check(tmp, bare, labels, journal, result)
            ok = (p.returncode == 0) == want_pass
            verdict = "pass" if want_pass else "fail"
            print("%s F4 %s → %s%s" % ("PASS" if ok else "FAIL", name, verdict,
                                        "" if ok else "\n" + p.stdout))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        for tmp, _ in boxes.values():
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
