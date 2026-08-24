#!/usr/bin/env bash
# Assertion helpers for replay checkers. Each expect names its source —
# the ledger case or the owning prose — because assertions derive from
# the ledger and the prose, never from observed runs.
FAILS=0

expect() { # "source" "description" cmd...
  local src="$1" desc="$2"; shift 2
  if "$@" >/dev/null 2>&1; then
    echo "ok   $desc"
  else
    echo "FAIL $desc  [source: $src]"
    FAILS=$((FAILS+1))
  fi
}

finish() { [ "$FAILS" -eq 0 ]; exit $?; }

# journal_writes [route-regex] — count of write entries (optionally by route)
journal_writes() {
  python3 - "$RUN_DIR/forge/journal.jsonl" "${1:-.}" <<'PY'
import json,re,sys
n=0
for line in open(sys.argv[1]):
    e=json.loads(line)
    if e.get("write") and re.search(sys.argv[2], e.get("route","")): n+=1
print(n)
PY
}

# dispatch_count — Task/agent tool_use events in the transcript
dispatch_count() {
  python3 - "$RUN_DIR/transcript.jsonl" <<'PY'
import json,sys
n=0
for line in open(sys.argv[1]):
    try: ev=json.loads(line)
    except ValueError: continue
    for b in (ev.get("message") or {}).get("content") or []:
        if isinstance(b,dict) and b.get("type")=="tool_use" and b.get("name") in ("Task","Agent"):
            n+=1
print(n)
PY
}

# state_query 'python-expr over st' — prints eval result against final state
state_query() {
  python3 - "$RUN_DIR/forge/state.json" "$1" <<'PY'
import json,sys
st=json.load(open(sys.argv[1]))
print(eval(sys.argv[2], {"st": st}))
PY
}
