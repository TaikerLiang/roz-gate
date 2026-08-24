#!/usr/bin/env bash
# C2 · Stage (7) has no blocked exit.
# Fixture: review-answers cannot complete the item — the spec CR is CLOSED
# while status: in-user-review persists.
# source: ledger C2 — "in-user-review is retained; no blocked. The failure
#   is a prefixed comment." (blocked exists to stop the machine, not to
#   inform the human; at (7) there is no machine to stop)
# source: commands/review-answers.md:27-28 — "Missing or closed while the
#   label persists → report it and act on nothing."
# source: references/workflow.md:276-282 — (7) has no blocked exit; a
#   failure is a `**[review] · question**`, never a label
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "ledger C2 + workflow.md:276-282" "status: blocked was never applied" \
  test "$(journal_writes)" = 0 -o "$(state_query '"status: blocked" in st["issues"]["5"]["labels"]')" = "False"

expect "ledger C2" "in-user-review is retained" \
  test "$(state_query '"status: in-user-review" in st["issues"]["5"]["labels"]')" = "True"

# review-answers.md:28 — act on NOTHING: no labels, no comments, no merges.
expect "review-answers.md:28" "no forge write at all on the closed-CR path" \
  test "$(journal_writes)" = 0

finish
