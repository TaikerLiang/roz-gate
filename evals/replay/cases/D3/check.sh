#!/usr/bin/env bash
# D3 · Every dispatch carries the seat's R&R row.
# Fixture: one inbox issue with no questions batch → patrol's async intake
# dispatches the product seat. The transcript's dispatch payload is the
# observation channel (the ledger's "structurally unobservable" was written
# with only the forge record in view; the upgrade was accepted).
# source: ledger D3 — "The payload contains the seat's Owns / Never row."
#   (a seat running without its contract produces plausible work, and
#   nothing in the record shows the row was missing)
# source: commands/patrol.md:18-23 — every role dispatch attaches the
#   seat's R&R row from references/workflow.md as its contract
# source: references/workflow.md:22 — product Owns: "actors, scenarios";
#   Never: "architecture, code, impl tests"
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

dispatch_carries_rr() {
  python3 - "$RUN_DIR/transcript.jsonl" <<'PY'
import json,sys
found=False
for line in open(sys.argv[1]):
    try: ev=json.loads(line)
    except ValueError: continue
    for b in (ev.get("message") or {}).get("content") or []:
        if isinstance(b,dict) and b.get("type")=="tool_use" and b.get("name") in ("Task","Agent"):
            p=json.dumps(b.get("input",{}), ensure_ascii=False)
            if "actors, scenarios" in p and "impl tests" in p:
                found=True
sys.exit(0 if found else 1)
PY
}

expect "ledger D3 + patrol.md:18-23 + workflow.md:22" \
  "the product dispatch payload carries its Owns AND Never row" \
  dispatch_carries_rr

expect "patrol.md:130-133 (the dispatch's product)" "one **[intake]** batch was posted" \
  test "$(state_query 'any(c["body"].startswith("**[intake]**") for c in st["issues"]["9"]["comments"])')" = "True"

finish
