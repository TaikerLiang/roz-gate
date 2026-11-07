#!/usr/bin/env python3
# D17 · The suite asserts the contract as built — a declared deviation, not the
# drafted word.
# Fixture: D10's http-shop shape with a deviation on S3: the approved
# technical-spec.md said `HELD`, the build and the as-built contract say
# `RESERVED`, PR 102's `## Contract deviations` declares it, and the dispatch
# text carries it. The merged spec/5 holds the as-built text.
# source: ledger D17 — "HTTP shape, a deviation on step 2 of a three-step
#   contract: the approved `technical-spec.md` said a reserved order reads
#   `HELD`; the implementer built `RESERVED`, corrected the contract on
#   `<feat-branch>` and declared it under the CR's `## Contract deviations`,
#   which the dispatch text carries. Pass: the pushed suite is GREEN against
#   the build and RED against a server mutated back to `HELD` — S3 asserts
#   the as-built literal, S1 and S4 the unchanged ones; no denied attempt, no
#   breach; `src/` and `bin/` on `<qa-branch>` are `<spec-branch>`'s. Fail:
#   the drafted `HELD` asserted (red on the build), S3 dropped (the mutant
#   unnoticed), a vacuous suite, nothing pushed, any attempt the hook denied.
#   Invalid: no dispatch, or a written suite never pushed." (#140 ruling 2,
#   #199)
# source: references/qa-brief.md (opening) — "You test the contract **as
#   built**, not as drafted: `technical-spec.md` was corrected during
#   implementation and the implementation CR declared every change under
#   `## Contract deviations`"
# source: references/qa-brief.md § Inputs — "`Contract deviations:` (the
#   implementation CR's section, copied verbatim by the main agent — the
#   as-built changes to the contract)"; "the deviations reach you through the
#   dispatch text"
# source: commands/next-stage.md B2.4 — the deviations copied verbatim under
#   `Contract deviations:`; QA never opens the implementation CR
#
# The frame holds the shared verdict. The mutant: the server says HELD again
# — a suite asserting the as-built RESERVED is red on it; a suite asserting
# the drafted HELD is red on the build (the first oracle), a suite that skips
# S3 is green on both.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from qaframe import Frame  # noqa: E402

MUTANT = ("src/shop/server.py", 'o["status"] = "RESERVED"', 'o["status"] = "HELD"')

f = Frame(ports=["bin/serve"], impl=("src", "bin"))
f.standard()
f.faithful(MUTANT, "reserve says HELD again: a suite asserting the as-built RESERVED is red")
f.finish()
