#!/usr/bin/env python3
# E2 · A seat's questions reach the holder from any document.
# Fixture: the implementer (scripted double) leaves its question in
# technical-spec.md §9 and does not return it in its report.
# source: ledger E2 — "Relocated verbatim into spec.md's Open Questions,
#   tagged with the raising role, before threads are posted." (threads are
#   the only objects the gates count; a question outside the threaded
#   surface blocks nothing)
# source: commands/next-stage.md:175-185 (A6) — sweep the other spec docs
#   for question-shaped content, MOVE it (copy verbatim into spec.md, delete
#   it from the source document), then post one thread per item
#
# Amendment (live opus sweep, 5/5): the needle was the item's TITLE
# (`clock source`, case-sensitive) — two runs were failed for title-casing
# it (`Q9 · Clock source`) while the relocation was correct. The needle is
# now the question's distinctive body text, case-insensitive: the title is
# the model's to shape, the question is the fixture's. And all five runs
# COPIED rather than moved: technical-spec.md kept its §9 with the question
# in it. "relocate it verbatim" read as copy; Paul ruled relocate = move
# (the copy is B3-class duplication that drifts) and A6 now says so. The
# no-section assertion stays, backed by the clarified prose, and the
# question text itself must be gone from the source document.
#
# Teeth (1.15.0): the explicit prose measured 0/5 — every run copied,
# threaded, and never touched the source again. The no-section predicate
# is now guard-gate rule D (hooks/guard-gate.py: a `git commit` is denied
# while a technical-spec.md under specs_dir carries the section) and lint
# E2 (evals/lint/run_lint.py) holds the three literals identical.
# source: hooks/guard-gate.py rule D — "A `git commit` never carries a
#   `technical-spec.md` under the project's `specs_dir` that still holds
#   an open-questions section"
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md") or ""
tech = r.remote_file("spec/5", "docs/specs/5/technical-spec.md") or ""
# The fixture question's body, not its title (seed.sh: "Which clock does
# `now` come from — the DB's or the API caller's?").
QUESTION = re.compile(r"which clock does .?now.? come from", re.I)

c.expect("ledger E2 + next-stage.md:176-178",
         "the §9 question was relocated into spec.md's Open Questions",
         QUESTION.search(spec) is not None)
c.expect("next-stage.md:176-181 (move: the section goes)",
         "technical-spec.md no longer carries an open-questions section",
         not re.search(r"^#+ .*open questions", tech, re.I | re.M))
c.expect("next-stage.md:178-181 (move: at most a pointer, never the body)",
         "the question text is gone from technical-spec.md",
         QUESTION.search(tech) is None)
c.expect("ledger E2 (a question outside the threads blocks nothing)",
         "a thread was posted for the relocated question",
         any(e.get("route") == "thread-post-inline"
             and QUESTION.search(e.get("body", "")) for e in r.journal()))
c.finish()
