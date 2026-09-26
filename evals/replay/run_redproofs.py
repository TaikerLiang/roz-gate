#!/usr/bin/env python3
"""Run every replay case's red-proof: evals/replay/cases/*/redproof.py.

    python3 evals/replay/run_redproofs.py

A red-proof shows a checker scoring simulated runs correctly — seeded
sandboxes, staged end states, real tool output — with no model and no
tokens, so it can run on every push. A red-proof recorded only in a commit
message cannot be re-run; one here can, and goes red the moment a checker
or seed change breaks what it proved. Cases without a redproof.py are
skipped (red-proofed in their commit messages, the older convention).

Prints each red-proof's own PASS/FAIL lines, then `N passed, M failed` over
the red-proofs run. Stdlib only; run by .githooks/pre-push and CI.
"""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    proofs = sorted(glob.glob(os.path.join(HERE, "cases", "*", "redproof.py")))
    passed = failed = 0
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
