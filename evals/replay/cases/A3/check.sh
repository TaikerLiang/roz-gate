#!/usr/bin/env bash
# A3 · Top-level comments are read as a channel.
# Fixture: unanswered top-level comment on the CR; every inline thread
# already carries an agent marker as its last entry.
# source: ledger A3 — "Actionable. Top-level is the default affordance on
#   the PR page and the only one usable from a phone."
# source: commands/patrol.md:56 — all three channels, CR-COMMENTS-LIST
#   included
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "patrol.md:56" "CR-COMMENTS-LIST was actually read" \
  grep -q '"route": "cr-comments-list"' "$RUN_DIR/forge/journal.jsonl"

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

expect "ledger A3 + patrol.md:56" \
  "the unanswered top-level comment was classified unheard and acted on" \
  route_taken

finish
