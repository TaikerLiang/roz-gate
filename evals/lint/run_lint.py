#!/usr/bin/env python3
"""Lint tier of the eval ledger — static checks on the plugin's own sources.

Every case guards against failure mode 2: the RULE ITSELF is broken, so
every stage faithfully executes it and reports green. Cases that guard a
runtime check (a grep the model executes from prose) get two layers:
  pattern proof — the canonical pattern, held in the case, runs against fixtures;
  source conformance — the prose must carry that same pattern verbatim.
Either layer alone is a hole: pattern-only proves a pattern nobody ships;
conformance-only ships an unproven pattern. See evals/README.md.

One case is one file: `cases/<id>.py` (`b1.py`, `c19.py`, …), its header a
docstring and its `META` the ledger row (`tools/ledger.py` renders
`evals/LEDGER.md` from it). This runner discovers the files, imports them
in ID order — a case's checks run at import against the shared checker in
`evals/lib/lintkit.py` — and prints one PASS/FAIL line per check, then
the tally. Two PRs that each add a case add two files and never touch the
same line (issue #131).

Ported one-to-one from run-lint.sh (bash). The language is a design
constraint, not a preference: the suite's owner reads Python, not shell
(evals/README.md § Language). Stdlib-only; runs on every push.
"""

import importlib
import os
import re
import sys

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(S))  # evals/  → lib.lintkit, lib.checkkit
sys.path.insert(0, S)  # evals/lint/ → cases.<id>

CASE = re.compile(r"^([a-z])(\d+)\.py$")


def case_modules():
    """Every `cases/<id>.py`, in ID order: family letter, then number."""
    found = []
    for name in os.listdir(os.path.join(S, "cases")):
        m = CASE.match(name)
        if m:
            found.append((m.group(1), int(m.group(2)), name[:-3]))
    return [n for _, _, n in sorted(found)]


def main():
    from lib.lintkit import c

    for mod in case_modules():
        importlib.import_module("cases." + mod)
    c.finish()


if __name__ == "__main__":
    main()
