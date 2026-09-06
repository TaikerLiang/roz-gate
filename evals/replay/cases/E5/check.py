#!/usr/bin/env python3
# E5 · An answer folds into the document that owns it.
# Fixture: a resolved [implementer] thread whose ruling (caller-passed
# clock) changes a contract clause that currently says "open question".
# source: ledger E5 — "technical-spec.md is modified. The spec.md entry
#   records the resolution and points at the clause." (folded as prose
#   beside the question instead, the contract never changes, QA derives
#   from the unchanged contract, and the defect ships with a resolved
#   thread pointing at it)
# source: commands/spec-answers.md:60-64 — fold the decision into the
#   document the raising seat owns: technical-spec.md for [implementer]
#   questions; a fold that lands as prose near the question while the
#   contract text stays unchanged ships the defect
# source: commands/spec-answers.md:93-95 — reply `✅ [<role>] resolved`
#   then THREAD-RESOLVE
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("spec-answers.md:60-62 (the owning document changed)",
         "a pushed commit beyond the seed touches technical-spec.md",
         r.remote_commits_touching("spec/5", "docs/specs/5/technical-spec.md") >= 2)
c.expect("ledger E5 (the contract learned the answer)",
         "the contract clause no longer defers the clock source",
         "open question" not in
         (r.remote_file("spec/5", "docs/specs/5/technical-spec.md") or "open question"))
c.expect("spec-answers.md:93-95", "the thread was resolved",
         any(e.get("route") == "thread-resolve" for e in r.journal()))
c.expect("spec-answers.md:93-94", "the resolution reply opens with ✅ [",
         any(e.get("route") == "thread-reply"
             and e.get("body", "").startswith("✅ [") for e in r.journal()))
c.finish()
