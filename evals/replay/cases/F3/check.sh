#!/usr/bin/env bash
# F3 · Spec refinement lands a complete set.
# Fixture: a gated issue at ready-for-spec; Path A runs end to end.
# source: ledger F3 — "Both spec documents exist; the CR is open; the
#   number of posted threads equals the number of entries in Open
#   Questions; labels flipped exactly once; no question left in any other
#   document." (the thread count catches a question written but never
#   surfaced — the E2 failure, detected by arithmetic)
# source: commands/next-stage.md:170-186 — A5 opens the CR; A6 posts one
#   thread per Open Questions item, body = the item verbatim
# source: commands/next-stage.md:201-203 — A7 flips ready-for-spec+
#   processing → in-spec-review only after CR and threads exist
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "next-stage.md (A3/A4)" "both spec docs exist on the pushed spec/5" \
  bash -c 'git -C "$BARE" show spec/5:docs/specs/5/spec.md >/dev/null 2>&1 \
        && git -C "$BARE" show spec/5:docs/specs/5/technical-spec.md >/dev/null 2>&1'

expect "next-stage.md:170-173 (A5)" "exactly one CR opened, head spec/5" \
  test "$(state_query 'sum(1 for p in st["prs"].values() if p["headRefName"]=="spec/5")')" = 1

# The arithmetic assertion: posted threads == Open Questions entries.
counts_match() {
  local threads qcount
  threads=$(journal_writes '^thread-post-inline$')
  qcount=$(git -C "$BARE" show spec/5:docs/specs/5/spec.md | \
    python3 -c '
import re,sys
txt=sys.stdin.read()
m=re.search(r"##\s*Open Questions(.*?)(?:\n##\s|\Z)", txt, re.S)
sec=m.group(1) if m else ""
print(len(re.findall(r"\*\*\[[^\]]+\]\s*·\s*Q\d+", sec)))')
  [ "$threads" -gt 0 ] && [ "$threads" = "$qcount" ]
}
expect "ledger F3 + next-stage.md:181-186 (A6)" \
  "posted threads == Open Questions entries (and > 0)" counts_match

labels() { state_query 'sorted(l for l in st["issues"]["5"]["labels"] if l.startswith("status:"))'; }
expect "next-stage.md:201-203 (A7)" "labels: in-spec-review alone" \
  test "$(labels)" = "['status: in-spec-review']"

expect "ledger F3 + next-stage.md:175-180 (A6 sweep)" \
  "no question-shaped section left in technical-spec.md" \
  bash -c '! git -C "$BARE" show spec/5:docs/specs/5/technical-spec.md | grep -qiE "^#+ .*(open questions|TBD)"'

finish
