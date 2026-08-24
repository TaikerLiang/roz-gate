#!/usr/bin/env bash
# A4 · in-user-review is a listening state, not a terminal one.
# Fixture: issue at in-user-review with an unanswered human top-level CR
# comment three days old (no agent marker anywhere after it).
# source: ledger A4 — "Actionable → review-answers. Not 'waiting on the
#   user'." (the original defect: comments sat unanswered while every pass
#   reported the loop was waiting on the human)
# source: commands/patrol.md:56 — an item whose latest entry does not start
#   with `**[` or `✅ [` is unheard → actionable → review-answers
# source: commands/review-answers.md:35 — the review-answers turn opens by
#   taking the processing lock (LABEL-ADD status: processing)
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

# The mechanical signature of the route being taken: either the
# review-answers lock was acquired on #5, or a marker-prefixed reply landed
# on CR 101. Silence on both = the A4 defect (classified as waiting).
route_taken() {
  python3 - "$RUN_DIR/forge/journal.jsonl" <<'PY'
import json,sys
lock=reply=False
for line in open(sys.argv[1]):
    e=json.loads(line)
    if e.get("route")=="issue-edit" and e.get("issue")=="5" \
       and any("processing" in a for a in e.get("add",[])): lock=True
    if e.get("write") and e.get("route") in ("pr-comment","thread-reply","thread-post-inline") \
       and (e.get("body","").startswith("**[") or e.get("body","").startswith("✅ [")): reply=True
sys.exit(0 if (lock or reply) else 1)
PY
}

expect "ledger A4 + patrol.md:56 + review-answers.md:35" \
  "the pass acted on the unheard comment (lock taken or marker reply posted)" \
  route_taken

finish
