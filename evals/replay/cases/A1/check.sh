#!/usr/bin/env bash
# A1 · A human's ✅ acknowledgement reads as an agent marker.
# Fixture: latest top-level CR comment is the human's, body begins with a
# BARE ✅ (`✅ 看起來可以…`) — not the agent marker `✅ [`.
# source: ledger A1 — "Classified unheard → actionable. The agent marker is
#   `✅ [`, never a bare ✅." (the single highest-value message in the
#   channel was the one the predicate could not see)
# source: commands/patrol.md:56 — unheard = latest entry does not start
#   with `**[` or `✅ [`
# source: commands/review-answers.md:35 — the review turn opens by taking
#   the processing lock
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

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

expect "ledger A1 + patrol.md:56" \
  "the bare-✅ comment was classified unheard and acted on" \
  route_taken

finish
