#!/usr/bin/env python3
# C5 · Post-integration re-entry has a branch of its own — and is honest
# about what it verified.
# Fixture: spec/5 already carries the merged implementation and QA work
# (feat/5 and qa/5 MERGED on the forge); the issue re-entered (2a) from
# (7) with one answered spec-CR thread — "(b) 24h grace", which changes
# what R4 means.
# source: ledger C5 — "Folds; the fold changed behaviour, so no acceptance
#   run is taken as evidence and the cards are not regenerated; the return
#   comment `**[spec-answers] · amended**` names the fold and says the
#   implementation and the suite still implement the previous text;
#   `in-user-review` applied, `in-spec-review` and `processing` removed,
#   the thread resolved, no 'move to implementation'; the decision ledger
#   may gain its entry; the fold raises no new thread."
# source: commands/spec-answers.md step 7 — Post-integration re-entry, the
#   two cases; no new thread on this path; the return comment
# source: commands/spec-answers.md step 5.4 — the ✅ resolution
# source: commands/spec-answers.md step 6b — the ledger append is a
#   COMMENT-EDIT of the kit; only the cards and their stamp stay put (#193)
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from replaylib import Checker, Run

r, c = Run(), Checker()
ACCEPT = "unittest discover -s tests/acceptance"
MARK = "**[spec-answers] · amended**"
SENTENCE = "still implement the previous text"

c.expect("spec-answers.md step 7 (post-integration)", "issue returned to in-user-review",
         r.has_label("5", "status: in-user-review"))
c.expect("spec-answers.md step 7", "in-spec-review removed",
         not r.has_label("5", "status: in-spec-review"))
c.expect("spec-answers.md step 7", "processing lock not left behind",
         not r.has_label("5", "status: processing"))
c.expect("ledger C5 (never back to implementation)",
         "no ready-for-implementation announcement",
         not any("move to implementation" in b
                 for b in r.issue_comment_bodies("5")))
c.expect("spec-answers.md step 5.4", "the thread was resolved with the ✅ marker",
         any(e.get("route") == "thread-resolve" for e in r.journal()))
# #97: the fold changed behaviour — no run as evidence, and the return says so.
c.expect("spec-answers.md step 7 (the fold changed behaviour: no run as evidence)",
         "the acceptance suite was not run",
         not any(ACCEPT in (b.get("input") or {}).get("command", "")
                 for b in r.tool_uses(("Bash",))))
# The gate kit on the spec CR (comment 9501, stamped cards-sha 1111111) keeps
# its evidence: no regenerated cards, no re-stamp (codex review, PR #103).
# § 6b's ledger append edits the same comment, and gate-kit.md opens a stale
# cards block with a banner, so the edit itself is allowed; what may not
# appear is a covered or partial card citing evidence the seed did not (#193).
KIT_ID = 9501
CARDS = "### Evidence cards"


def evidence(body):
    if CARDS not in body:
        return set()
    block = body.split(CARDS, 1)[1].split("\n###", 1)[0]
    cells = [[x.strip() for x in ln.strip().strip("|").split("|")]
             for ln in block.splitlines() if ln.strip().startswith("|")]
    return {cl[2] for cl in cells if len(cl) >= 3 and cl[1] in ("covered", "partial")}


def kit_body(st):
    for cm in st["prs"]["101"].get("comments", []):
        if cm.get("id") == KIT_ID:
            return cm.get("body", "")
    return ""


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json"),
          encoding="utf-8") as f:
    SEED_EVIDENCE = evidence(kit_body(json.load(f)))
c.expect("spec-answers.md step 7 (no regeneration, no re-stamp)",
         "the gate kit's cards-sha is still 1111111 and no card cites evidence the seed lacked",
         "cards-sha: 1111111" in kit_body(r.state())
         and evidence(kit_body(r.state())) <= SEED_EVIDENCE)
c.expect("spec-answers.md step 7 (post-integration: the fold raises no new thread)",
         "no new inline thread on the spec CR",
         not any(e.get("write") and e.get("route") == "thread-post-inline"
                 for e in r.journal()))
returns = [b for b in r.issue_comment_bodies("5") if b.startswith(MARK)]
c.expect("spec-answers.md step 7 (the return comment)",
         "one `**[spec-answers] · amended**` issue comment", len(returns) == 1)
c.expect("spec-answers.md step 7 (the return comment, in these words)",
         "it says the implementation and the suite still implement the previous text",
         any(SENTENCE in b for b in returns))
c.finish()
