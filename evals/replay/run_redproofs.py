#!/usr/bin/env python3
"""Run every replay case's red-proof: evals/replay/cases/*/redproof.py.

    python3 evals/replay/run_redproofs.py

A red-proof shows a checker scoring simulated runs correctly — seeded
sandboxes, staged end states, real tool output — with no model and no
tokens, so it can run on every push. A red-proof recorded only in a commit
message cannot be re-run; one here can, and goes red the moment a checker
or seed change breaks what it proved.

Every case must ship one. The cases below predate the rule — red-proofed in
their commit messages — and are the only exemptions; the list only
shrinks. A new case missing redproof.py fails here, and so does an
exemption that is no longer needed (the case gained one) or names no case.

Prints each red-proof's own PASS/FAIL lines, then `N passed, M failed` over
the red-proofs run and the presence check. Stdlib only; run by
.githooks/pre-push and CI.
"""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Predate the rule (2026-09-26). Port one, delete its line — never add one.
LEGACY = {"A1", "A2", "A3", "A4", "A5", "C1", "C2", "C5", "D2", "D3",
          "E2", "E5", "F1", "F2", "F3", "F4", "F5", "F6"}


def presence():
    """Every case has a redproof.py or a LEGACY exemption; LEGACY is exact."""
    cases = {os.path.basename(os.path.dirname(p))
             for p in glob.glob(os.path.join(HERE, "cases", "*", "case.json"))}
    has = {c for c in cases if os.path.isfile(os.path.join(HERE, "cases", c, "redproof.py"))}
    problems = ["%s has no redproof.py (every new replay case must ship one — "
                "evals/CONTRIBUTING.md)" % c for c in sorted(cases - has - LEGACY)]
    problems += ["%s is exempt in LEGACY but now ships redproof.py — delete its "
                 "LEGACY entry" % c for c in sorted(LEGACY & has)]
    problems += ["LEGACY names %s, which is not a case" % c for c in sorted(LEGACY - cases)]
    return problems


def main():
    proofs = sorted(glob.glob(os.path.join(HERE, "cases", "*", "redproof.py")))
    passed = failed = 0
    problems = presence()
    for problem in problems:
        print("FAIL redproof presence: %s" % problem)
    if problems:
        failed += 1
    else:
        passed += 1
        print("PASS redproof presence: every case ships redproof.py or is LEGACY "
              "(%d legacy left)" % len(LEGACY))
    for proof in proofs:
        case = os.path.basename(os.path.dirname(proof))
        p = subprocess.run([sys.executable, proof], capture_output=True, text=True)
        lines = [line for line in (p.stdout + p.stderr).splitlines()
                 if line.startswith(("PASS ", "FAIL ")) or p.returncode != 0]
        print("\n".join(lines))
        if p.returncode == 0:
            passed += 1
        else:
            failed += 1
            print("FAIL redproof %s (exit %d)" % (case, p.returncode))
    print("\n%d passed, %d failed (red-proofs: %s)"
          % (passed, failed, ", ".join(os.path.basename(os.path.dirname(p)) for p in proofs)
             or "none"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
