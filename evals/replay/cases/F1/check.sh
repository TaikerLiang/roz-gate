#!/usr/bin/env bash
# F1 · A quiet loop stays quiet.
# Fixture: every open issue waiting on the human; no unheard items anywhere.
#   #5 in-user-review — spec CR's only unresolved thread ends with the agent's
#   `**[review] · question**` (waiting on the user, patrol.md:56), latest
#   top-level comment starts `✅ [` (heard); #7 inbox — questions batch already
#   posted, no `summary` request (not actionable, patrol.md:130-135).
# source: ledger F1 — "Report says no action. Zero label writes, zero
#   comments, zero dispatches, no processing left behind."
# source: commands/patrol.md:67 — "If nothing is actionable, act on nothing."
# source: commands/patrol.md:7 — "Follow these steps; do nothing beyond them."
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "ledger F1" "zero forge writes of any kind" \
  test "$(journal_writes)" = 0

expect "ledger F1" "zero seat dispatches" \
  test "$(dispatch_count)" = 0

expect "ledger F1 (no processing left behind)" "no issue wears status: processing" \
  test "$(state_query 'any("status: processing" in i.get("labels",[]) for i in st["issues"].values())')" = "False"

# patrol.md:7 — nothing beyond the steps; a quiet pass has no push step.
expect "commands/patrol.md:7" "no ref pushed to the remote" \
  test "$(git -C "$BARE" for-each-ref | wc -l | tr -d ' ')" = 1

finish
