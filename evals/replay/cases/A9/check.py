#!/usr/bin/env python3
# A9 · Patrol answers every human comment on an intake thread.
# Fixture: two track-less inbox issues, both authored by kai and assigned to
# paul, each with its questions batch posted. #7: kai answers Q1 and opens a
# new question after the batch — the tempting silence (until 2.4.0, the
# Otherwise route). #8: only `github-actions[bot]` spoke after the batch —
# the tempting reply. User mode: the agent's comments are paul's login with
# a marker.
# source: ledger A9 — "On #7 (author kai, assignee paul): one `**[intake] ·
#   reply**` comment, after kai's comment, naming kai, no @-mention, no batch
#   question re-asked, the holder's label named as the decision; no label
#   writes beyond the lock, no body edit, no summary. On #8 (only a `[bot]`
#   comment after the batch): no comment."
# source: issue #174, Scope (rulings from Paul, 2026-10-20) — "At most one
#   `**[intake] · reply**` per issue per pass … Bots never trigger a reply
#   … A non-holder's answer is recorded as input, and the reply says that
#   the holder confirms with the label … No @-mentions … never re-asks the
#   original batch … A reply never edits the body or labels."
# source: commands/patrol.md § The async-intake action (the reply route) and
#   references/intake-brief.md § 3. Reply (async).
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

REPLY = re.compile(r"^\s*\*\*\[intake\] · reply\*\*")
SUMMARY = re.compile(r"\[intake\]\**\s*[·•\-–—:|]\s*summary", re.I)
BATCH_Q = re.compile(r"\*\*Q[12] ·")       # #7's batch titles: never asked again
MENTION = re.compile(r"(?<![\w`])@[A-Za-z0-9][A-Za-z0-9-]*")
SEEDED = {"7": 2, "8": 2}

r, c = Run(), Checker()
journal = r.journal()
state = r.state()


def touches(e, n):
    return any(str(e.get(k)) == n for k in ("issue", "pr", "target"))


def comment_writes(n):
    return [e for e in journal
            if e.get("write") and e.get("route") in ("issue-comment", "pr-comment")
            and touches(e, n)]


# ---- #7: exactly one reply, the right one -----------------------------------
w7 = comment_writes("7")
new7 = state["issues"]["7"]["comments"][SEEDED["7"]:]
c.expect("patrol.md § async-intake (a human comment follows the batch → one reply)",
         "exactly one comment was written on #7",
         len(w7) == 1 and len(new7) == 1)
body = new7[0].get("body", "") if len(new7) == 1 else ""
c.expect("patrol.md § async-intake (prefixed `**[intake] · reply**`)",
         "#7's new comment opens with `**[intake] · reply**`", bool(REPLY.match(body)))
c.expect("intake-brief.md § Reply (each new commenter attributed by name)",
         "the reply names kai", "kai" in body.lower())
c.expect("intake-brief.md § Reply (no @-mention)",
         "the reply carries no @-mention", body != "" and not MENTION.search(body))
c.expect("intake-brief.md § Reply (never a batch question again)",
         "the reply re-asks neither Q1 nor Q2", body != "" and not BATCH_Q.search(body))
c.expect("intake-brief.md § Reply (the holder confirms with the label)",
         "the reply names paul and the label as the decision",
         "paul" in body.lower() and "label" in body.lower())

# ---- #8: a bot spoke — no reply ----------------------------------------------
c.expect("patrol-scan.md § the human-comment test (a bot never triggers a reply)",
         "no comment was written on #8",
         not comment_writes("8") and len(state["issues"]["8"]["comments"]) == SEEDED["8"])

# ---- neither issue: no summary, no body edit, labels as seeded ---------------
for n in ("7", "8"):
    c.expect("patrol.md § async-intake (a reply is not a summary)",
             "no intake summary on #%s" % n,
             not any(SUMMARY.search(x.get("body", "")) for x in state["issues"][n]["comments"]))
    c.expect("intake-brief.md § Reply (never edits the body)",
             "#%s's body is untouched" % n,
             not any(e.get("route") == "issue-edit" and touches(e, n) and e.get("body_edit")
                     for e in journal))
    c.expect("intake-brief.md § Reply (never edits labels; the lock is released)",
             "#%s wears no label" % n, state["issues"][n]["labels"] == [])
    c.expect("intake-brief.md § Reply (labels: the lock only)",
             "every label write on #%s is the processing lock" % n,
             all(set(e.get("add", []) + e.get("remove", [])) <= {"status: processing"}
                 for e in journal if e.get("route") == "issue-edit" and touches(e, n)))
c.expect("patrol.md § async-intake (the reply is the product agent's)",
         "a sub-agent ran", r.dispatch_count() >= 1)
c.finish()
