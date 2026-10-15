"""C3 · `processing` coexists with a phase label             (preventive)
Oracle (patrol.md's coexistence sentence, executable): `processing` is a
mutex; all other `status:` labels are phases, at most one at a time.
"""

import re

from lib.lintkit import c, dirs_text

META = {
    "id": 'C3',
    "title": '`processing` coexists with a phase label',
    "tier": 'lint (preventive)',
    "ledger": None,
}

MUTEX = "processing"
PHASES = ("ready-for-spec", "in-spec-review", "ready-for-dev",
          "in-user-review", "blocked")
TRACKS = ("spec", "fast")


def legal(labels):
    """Space-separated status label names -> True legal / False illegal."""
    n = 0
    for lab in labels.split():
        if lab == MUTEX:
            continue
        if lab not in PHASES:
            return False
        n += 1
    return n <= 1


c.expect("oracle", "C3: phase + processing is legal (a stale pair names the death stage)",
         legal("in-spec-review processing"))
c.expect("oracle", "C3: two phase labels are illegal",
         not legal("in-spec-review in-user-review"))
c.expect("oracle", "C3: an unknown status label is illegal",
         not legal("shipping"))
# Completeness — the drift alarm: every backticked label literal in the
# sources must be in the oracle, or the suite goes red on the new label.
label_text = dirs_text("commands", "references", "templates", "agents")
drift = []
for m in sorted(set(re.findall(r"`status: ([a-z-]+)`", label_text))):
    if m not in PHASES and m != MUTEX:
        drift.append("`status: %s`" % m)
for m in sorted(set(re.findall(r"`track: ([a-z]+)`", label_text))):
    if m not in TRACKS:
        drift.append("`track: %s`" % m)
if not drift:
    c.passed += 1
    c.ok("C3 completeness: every source label is in the oracle")
else:
    c.fails += 1
    c.fail("C3 completeness", "labels missing from the oracle: %s"
           % " ".join(drift))
