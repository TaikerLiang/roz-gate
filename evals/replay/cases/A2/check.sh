#!/usr/bin/env bash
# A2 · A review whose whole content is its body is invisible.
# Fixture: one CHANGES_REQUESTED review with a non-empty body, zero inline
# comments, zero issue comments — it appears in neither THREADS-LIST nor
# the comments endpoint.
# source: ledger A2 — "Detected as unheard via REVIEWS-LIST." (a repository
#   could scan perfectly clean while a reviewer had blocked the change)
# source: commands/patrol.md:56 — the CR is read on all three channels
# source: references/forge-github.md:114-125 — REVIEWS-LIST; a non-empty
#   body counts on all three states
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "patrol.md:56 + forge-github.md:114" "REVIEWS-LIST was actually read" \
  grep -q '"route": "reviews-list"' "$RUN_DIR/forge/journal.jsonl"

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

expect "ledger A2 + patrol.md:56" \
  "the body-only review was classified unheard and acted on" \
  route_taken

finish
