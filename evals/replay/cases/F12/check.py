#!/usr/bin/env python3
# F12 · tip names the next move and writes nothing.
# Fixture: #5 track: spec + in-spec-review; spec CR #101 open with its one
# thread resolved and nothing unheard — the (2) → (3) gate is the human's.
# source: ledger F12 — "The answer names `status: ready-for-dev` as the
#   human's move and `next-stage` as the loop's, and links the spec CR; the
#   journal carries zero writes, no dispatch happened, #5's labels are as
#   seeded, the remote's refs are byte-identical." (a read-only command
#   measured as one: the tempting write is the label it recommends — #121)
# source: commands/tip.md — "**Read-only.** This command writes nothing: no
#   label, no comment, no commit, no branch, no lock."
# source: commands/tip.md §2 — in-spec-review, every thread resolved,
#   nothing unheard → yours: apply `status: ready-for-dev`; the loop's:
#   nothing until the label; then `next-stage` launches (3)+(4)
# source: commands/tip.md §4 — every bullet that names a CR carries its url
# source: references/workflow.md — owner table: `in-spec-review` →
#   `ready-for-dev` (all threads resolved) is **you**
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
text = r.result_text()

# ---- the answer (the model's own prose — the only place a tip lives) ------
c.expect("tip.md §2 (in-spec-review, every thread resolved)",
         "the answer names `ready-for-dev` as the human's move", "ready-for-dev" in text)
c.expect("tip.md §2 (the loop's)", "the answer names `next-stage` as the loop's move",
         "next-stage" in text)
c.expect("tip.md §4 (every bullet carries its url)", "the answer links the spec CR #101",
         "pull/101" in text)

# ---- vacuity guard: the forge was read, not guessed --------------------------
c.expect("tip.md §1 (ISSUE-VIEW)", "#5 was read from the forge",
         any(e.get("route") == "issue-view" and str(e.get("issue")) == "5"
             for e in r.journal()))

# ---- read-only: nothing written anywhere. The journal sees every stub write;
# the state checks catch a write that reached the forge some other way. -------
c.expect("tip.md (Read-only)", "zero forge writes in the journal — no label, no lock, no comment",
         r.journal_writes() == 0)
c.expect("ledger F12 (labels as seeded)", "#5 wears exactly the seeded labels",
         sorted(r.state()["issues"]["5"]["labels"]) == ["status: in-spec-review", "track: spec"])
c.expect("tip.md (no comment)", "no issue comment posted", r.issue_comment_bodies("5") == [])
c.expect("tip.md §1 (no dispatch)", "no sub-agent dispatched", r.dispatch_count() == 0)
# Seeded refs: main + spec/5. Neither moved, neither vanished, nothing added.
c.expect("ledger F12 (refs unchanged)", "exactly the two seeded refs on the remote",
         r.remote_ref_count() == 2)
c.expect("ledger F12 (refs unchanged)", "spec/5 still carries the seeded spec",
         (r.remote_file("spec/5", "docs/specs/5/spec.md") or "").startswith(
             "# Spec #5 — Offer expiry enforcement"))
c.finish()
