#!/usr/bin/env bash
# A5 · The fast track resolves to its own CR.
# Fixture: track: fast + in-user-review, unanswered comment on fast/5's CR.
# No spec CR exists anywhere in the fixture.
# source: ledger A5 — "CR resolves to fast/<n> and the item is detected."
#   (the row said "spec CR", so the A4 fix would have covered only half
#   the tracks)
# source: commands/patrol.md:56 — "`spec/<n>` for `track: spec`,
#   `fast/<n>` for `track: fast`"
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "patrol.md:56" "the fast CR's channels were read (CR 102, head fast/5)" \
  grep -q '"route": "cr-comments-list".*"target": "102"' "$RUN_DIR/forge/journal.jsonl"

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

expect "ledger A5 + patrol.md:56" \
  "the fast-track comment was detected and acted on" \
  route_taken

finish
