"""J1 · the judgment fixtures are frozen at T                (preventive)
Contamination is that tier's whole game: every forge comment after the
question's timestamp contains the answer. materialize.py's check runs
here on every push so a re-materialization (or a hand edit) that lets a
later comment in goes red before it can score a run. Red-proofed by
planting one post-T comment (names fixture, issue, comment id). The
blindness files must exist and be complete before any recorded run.
"""

import json
import os
import sys

from lib.lintkit import R, c, read, src

META = {
    "id": 'J1',
    "title": 'the judgment fixtures are frozen at T',
    "tier": 'lint (preventive)',
    "ledger": None,
}

sys.path.insert(0, os.path.join(R, "evals", "judgment"))
from materialize import check_frozen  # noqa: E402

_frozen_bad = check_frozen(os.path.join(R, "evals", "judgment", "cases"))
c.expect("judgment/materialize.py check_frozen",
         "J1: every judgment fixture's forge state is frozen at its T%s"
         % ("" if not _frozen_bad else " — " + "; ".join(_frozen_bad)), not _frozen_bad)
_crit = json.loads(read("evals/judgment/criteria.json"))
c.expect("judgment/criteria.json", "J1: all seven corpus items have a criterion",
         all(k in _crit for k in ("P1", "P2", "P8", "P12", "N1", "N5", "N10")))
src("J1: the judge prompt carries the criterion slot",
    "evals/judgment/judge-prompt.md", "{criterion}")
src("J1: the judge prompt carries the document slot",
    "evals/judgment/judge-prompt.md", "{document}")
