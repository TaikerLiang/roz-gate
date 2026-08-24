#!/usr/bin/env bash
# D2 · The fidelity dispatch is blind by topology.
# Fixture: the QA CR carries an open fidelity thread (human's answer last);
# the implementation CR is thread-clean. Address-review dispatches the QA
# side; the fidelity re-check must live on qa/5 and never touch feat/5.
# source: ledger D2 — "Checkout is qa/<n>; abort if the context ever
#   touched feat/<n>. Blindness asserted in a prompt is a request;
#   blindness enforced by which branch is checked out is a fact."
# source: commands/patrol.md:83-91 — QA CR fidelity threads → dispatch qa
#   on qa/<n>; re-checks use a fresh implementation-blind dispatch on
#   qa/<n> only
# source: commands/next-stage.md:305-310 (B5b) — the qa/<n> checkout is
#   what makes the dispatch structurally implementation-blind
#
# Stated limit (README, cannot-see list): this observes the ABSENCE of any
# feat/5 touch in the transcript; in-context leakage through text already
# in the session is invisible to any transcript check.
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "patrol.md:84-85 (the work happens on qa/5)" "qa/5 was checked out" \
  python3 -c '
import json,sys
for line in open("'$RUN_DIR'/transcript.jsonl"):
    try: ev=json.loads(line)
    except ValueError: continue
    for b in (ev.get("message") or {}).get("content") or []:
        if isinstance(b,dict) and b.get("type")=="tool_use" and b.get("name")=="Bash" \
           and "qa/5" in json.dumps(b.get("input",{})) and "checkout" in json.dumps(b.get("input",{})):
            sys.exit(0)
sys.exit(1)'

expect "ledger D2 + next-stage.md:305-310" "no tool call ever references feat/5" \
  python3 -c '
import json,sys
for line in open("'$RUN_DIR'/transcript.jsonl"):
    try: ev=json.loads(line)
    except ValueError: continue
    for b in (ev.get("message") or {}).get("content") or []:
        if isinstance(b,dict) and b.get("type")=="tool_use" \
           and "feat/5" in json.dumps(b.get("input",{}), ensure_ascii=False):
            sys.exit(1)
sys.exit(0)'

finish
