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
# is now guard-gate rule D (hooks/guard_gate.py: a `git commit` is denied
# while a technical-spec.md under specs_dir carries the section) and lint
# E2 (evals/lint/run_lint.py) holds the three literals identical.
# source: hooks/guard_gate.py rule D — "A `git commit` never carries a
#   `technical-spec.md` under the project's `specs_dir` that still holds
#   an open-questions section"
#
# Amendment (#410, ruled 2026-11-20): "copy it verbatim" measured 0/6 over
# two haiku55 sweeps — every run moved the question and reworded it. A
# faithful paraphrase passes: the relocated item, and its thread, is
# tagged with the raising role and names `now` and both options (the DB and
# the API caller). A6 still says verbatim. Folding the question into
# another seat's item with a pointer (2026-11-19 r1) fails: the question
# has its own item. The verbatim needle stays for technical-spec.md — a
# copy left behind is the seat's own text. Red-proof: redproof.py.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
spec = r.remote_file("spec/5", "docs/specs/5/spec.md") or ""
tech = r.remote_file("spec/5", "docs/specs/5/technical-spec.md") or ""
# The fixture question's body, not its title (seed.sh: "Which clock does
# `now` come from — the DB's or the API caller's?").
QUESTION = re.compile(r"which clock does .?now.? come from", re.I)
TITLE = re.compile(r"^\s*(?:[-*] +)?\*\*\[", re.M)
NAMES = (r"\bnow\b", r"\b(?:DB|database)\b", r"\bcaller\b")


def items(text):
    """The question items of a text, each from its `**[role]` title line to
    the next one."""
    starts = [m.start() for m in TITLE.finditer(text)]
    return [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)])]


def relocated(item):
    """The fixture question as its own item: the implementer's tag on the
    title line, `now` and both options in the item."""
    return ("[implementer]" in item.strip().split("\n", 1)[0]
            and all(re.search(name, item, re.I) for name in NAMES))


open_q = re.search(r"^## Open Questions\b.*?(?=^## |\Z)", spec, re.I | re.M | re.S)

c.expect("ledger E2 + next-stage.md:176-178",
         "the §9 question was relocated into spec.md's Open Questions",
         any(relocated(i) for i in items(open_q.group(0) if open_q else "")))
c.expect("next-stage.md:176-181 (move: the section goes)",
         "technical-spec.md no longer carries an open-questions section",
         not re.search(r"^#+ .*open questions", tech, re.I | re.M))
c.expect("next-stage.md:178-181 (move: at most a pointer, never the body)",
         "the question text is gone from technical-spec.md",
         QUESTION.search(tech) is None)
c.expect("ledger E2 (a question outside the threads blocks nothing)",
         "a thread was posted for the relocated question",
         any(e.get("route") == "thread-post-inline"
             and relocated(e.get("body", "")) for e in r.journal()))
c.finish()
