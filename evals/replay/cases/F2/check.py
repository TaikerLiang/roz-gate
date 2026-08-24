#!/usr/bin/env python3
# F2 · One review turn answers exactly what was asked.
# Fixture: three unheard items across all three channels — one inline
# thread, one review body, one top-level comment.
# source: ledger F2 — "Exactly three prefixed replies, each citing its
#   item's URL; zero threads resolved; lock taken and released;
#   in-user-review retained." (two replies = an item dropped silently;
#   four = one answered twice; a resolved thread = the agent closed a
#   question that was not its own)
# source: commands/review-answers.md:57-63 — every write starts with the
#   marker, cites the URL it answers, never resolves the thread
# source: commands/review-answers.md:34-36,160 — lock taken; every exit
#   removes it; in-user-review stays
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Run, Checker

r, c = Run(), Checker()
c.expect("ledger F2 (counts are the assertion)",
         "exactly three marker-prefixed replies", r.marker_replies() == 3)
c.expect("ledger F2 + review-answers.md:63", "zero threads resolved",
         r.journal_writes(r"^thread-resolve$") == 0)
c.expect("review-answers.md:34-36", "lock taken and released (processing absent at end)",
         not r.has_label("5", "status: processing"))
c.expect("ledger F2", "in-user-review retained",
         r.has_label("5", "status: in-user-review"))
c.expect("review-answers.md:57 (writes are marker-prefixed)",
         "no unmarked forge comment posted", r.unmarked_comment_writes() == 0)
c.finish()
