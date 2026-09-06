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

# Codex review, PR #1: a count alone is spoofable — three replies to the
# SAME thread passes while two items go unanswered. The mapping is the
# assertion: each reply binds to a DISTINCT requested item, one per
# channel (review-answers.md:63 — every write cites the URL of the
# comment it answers). Items: inline thread databaseId 9001, review 501,
# top-level comment 800.
def one_reply_per_item():
    thread_ok = sum(1 for e in r.journal()
                    if e.get("route") == "thread-reply"
                    and e.get("base") == 9001
                    and e.get("body", "").startswith(("**[", "✅ ["))) == 1
    top = [e.get("body", "") for e in r.journal()
           if e.get("route") == "pr-comment" and e.get("write")
           and e.get("body", "").startswith(("**[", "✅ ["))]
    review_cited = sum(1 for b in top
                       if "pullrequestreview-501" in b or "mid-session" in b)
    comment_cited = sum(1 for b in top
                        if "#issuecomment-800" in b or "now 參數" in b)
    return thread_ok and review_cited == 1 and comment_cited == 1

c.expect("ledger F2 + review-answers.md:63 (the mapping, not the total)",
         "each reply binds to a distinct item across the three channels",
         one_reply_per_item)
c.expect("ledger F2 + review-answers.md:63", "zero threads resolved",
         r.journal_writes(r"^thread-resolve$") == 0)
c.expect("review-answers.md:34-36", "lock taken and released (processing absent at end)",
         not r.has_label("5", "status: processing"))
c.expect("ledger F2", "in-user-review retained",
         r.has_label("5", "status: in-user-review"))
c.expect("review-answers.md:57 (writes are marker-prefixed)",
         "no unmarked forge comment posted", r.unmarked_comment_writes() == 0)
c.finish()
