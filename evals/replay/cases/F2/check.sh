#!/usr/bin/env bash
# F2 · One review turn answers exactly what was asked.
# Fixture: three unheard items across all three channels — one inline
# thread, one review body, one top-level comment.
# source: ledger F2 — "Exactly three prefixed replies, each citing its
#   item's URL; zero threads resolved; lock taken and released;
#   in-user-review retained." (two replies = an item dropped silently;
#   four = one answered twice; a resolved thread = the agent closed a
#   question that was not its own)
# source: commands/review-answers.md:57-63 — every write starts with the
#   marker, cites the URL it answers, never resolves the thread
# source: commands/review-answers.md:34-36,160 — lock taken; every exit
#   removes it; in-user-review stays
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

marker_replies() {
  python3 - "$RUN_DIR/forge/journal.jsonl" <<'PY'
import json,sys
n=0
for line in open(sys.argv[1]):
    e=json.loads(line)
    if e.get("write") and e.get("route") in ("pr-comment","thread-reply") \
       and (e.get("body","").startswith("**[") or e.get("body","").startswith("✅ [")): n+=1
print(n)
PY
}

expect "ledger F2 (counts are the assertion)" "exactly three marker-prefixed replies" \
  test "$(marker_replies)" = 3

expect "ledger F2 + review-answers.md:63" "zero threads resolved" \
  test "$(journal_writes '^thread-resolve$')" = 0

expect "review-answers.md:34-36" "lock taken and released (processing absent at end)" \
  test "$(state_query '"status: processing" in st["issues"]["5"]["labels"]')" = "False"

expect "ledger F2" "in-user-review retained" \
  test "$(state_query '"status: in-user-review" in st["issues"]["5"]["labels"]')" = "True"

expect "review-answers.md:57 (writes are marker-prefixed)" "no unmarked forge comment posted" \
  python3 -c '
import json,sys
for line in open("'$RUN_DIR'/forge/journal.jsonl"):
    e=json.loads(line)
    if e.get("write") and e.get("route") in ("pr-comment","thread-reply","issue-comment"):
        b=e.get("body","")
        if not (b.startswith("**[") or b.startswith("✅ [")): sys.exit(1)
sys.exit(0)'

finish
