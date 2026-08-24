#!/usr/bin/env bash
# Smoke S1: the SUT can read a repo file through this harness.
# Plumbing proof, not a behavioural assertion — no ledger source applies.
set -u
python3 - "$RUN_DIR/transcript.jsonl" <<'PY'
import json,sys
last=None
for line in open(sys.argv[1]):
    try: ev=json.loads(line)
    except ValueError: continue
    if ev.get("type")=="result": last=ev
sys.exit(0 if last and "XENOLITH" in (last.get("result") or "") else 1)
PY
