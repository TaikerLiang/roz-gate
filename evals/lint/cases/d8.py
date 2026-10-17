"""D8 · the QA dispatch is blind by the hook and may run its suite  (#140, 2.0.0)
Since 2.0.0 qa/<n> is cut after the implementation landed on the spec
branch, so the branch carries the code and the topology no longer protects:
the QA dispatch runs under guard-blind rule E's marker with `seat=qa`. The
predicate is unchanged (the four D2 regexes); running `acceptance_test`
names no src/ operand and is never denied; the deny message names the
dispatch and its brief. hooks/tests prove the shapes end to end; replay D8
measures a run.
"""

import os

from cases.d2 import _TOP, _gb
from lib.lintkit import c, src

META = {
    "id": 'D8',
}


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        return _gb.marker_seat(path)
    finally:
        os.remove(path)

src("D8: B2.4 arms the marker with seat=qa", "commands/next-stage.md",
    "`seat=qa` here\n  (the hook names the dispatch in its deny message)")
src("D8: B2.4 — QA may run, may not read", "commands/next-stage.md",
    "QA may run `acceptance_test` in its worktree all\n  it likes; it may not read the code it "
    "runs against")
src("D8: the QA brief states the blindness rule", "references/qa-brief.md",
    "guard-blind rule E (the marker's `seat=qa` line) denies every\nread of `src/` outside "
    "`<acceptance_dir>` and the declared port")
src("D8: the QA brief — run the suite", "references/qa-brief.md",
    "Run config `acceptance_test` for the feature in your worktree")
src("D8: workflow (4) — blindness is the hook's", "references/workflow.md",
    "blindness is the hook's, not\n  the topology's")
src("D8: the hook parses the seat line", "hooks/guard_blind.py", "def marker_seat(path):")
src("D8: the hook's QA opening", "hooks/guard_blind.py",
    'QA_OPEN = "Roz Gate: blocked — this is a QA dispatch"')
src("D8: the hook's fidelity opening survives (lint D2, the D2/D7 checkers pair by it)",
    "hooks/guard_blind.py", 'FIDELITY_OPEN = "Roz Gate: blocked — this is a fidelity dispatch"')
src("D8: hooks/README's marker snippet carries seat=", "hooks/README.md",
    "seat=qa for the QA dispatch (next-stage B2.4), seat=reviewer for the fidelity dispatch (B2.7)")
src("D8: README's rule E row names QA's dispatch", "README.md", "or QA's own (`seat=qa`)")
src("D8: the index's rule E row names QA's dispatch", "docs/index.html",
    "or QA's own since 2.0.0")
src("D8: the hook suite carries the seat=qa class", "hooks/tests/test_guard_blind.py",
    "class RuleE_QaDispatchSeat(HookTest):")
_PORT = "src/pricing.py"
c.expect("hook rule E (#140: running the suite is never a read of src/)",
         "D8 pattern: `python3 run_acceptance.py tests/acceptance` and `./mvnw test -Dtest=…` are "
         "not violations",
         _gb.violation("Bash", {"command": "python3 run_acceptance.py tests/acceptance"}, "feat/5",
                       [_PORT], _TOP) is None
         and _gb.violation("Bash", {"command": "./mvnw -q test -Dtest=OfferAcceptanceTest"},
                           "feat/5", [_PORT], _TOP) is None)
c.expect("hook rule E (#140: the port is readable, the rest of src/ is not)",
         "D8 pattern: `cat src/pricing.py` passes with the port as a root; `cat src/internal.py` "
         "is a read",
         _gb.violation("Bash", {"command": "cat %s" % _PORT}, "feat/5", [_PORT], _TOP) is None
         and _gb.violation("Bash", {"command": "cat src/internal.py"}, "feat/5", [_PORT], _TOP)
         == "a read of src/")
c.expect("hook rule E (#140: the seat line is read, normalized, unknown → fidelity)",
         "D8 pattern: marker_seat reads qa / reviewer, strips quotes and case, ignores others",
         (lambda d: (_write(d, "issue=5\nseat=qa\n") == "qa"
                     and _write(d, "issue=5\nseat=`QA`\n") == "qa"
                     and _write(d, "issue=5\nseat=reviewer\n") == "reviewer"
                     and _write(d, "issue=5\nseat=product\n") is None
                     and _write(d, "issue=5\n") is None))(
             os.path.join(os.environ.get("TMPDIR", "/tmp"), "roz-d8-marker")))
