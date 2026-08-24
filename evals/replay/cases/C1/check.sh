#!/usr/bin/env bash
# C1 · A STOP strips the gate label.
# Fixture: Path B entry at ready-for-dev STOPs on an `(unverified)` claim.
# source: ledger C1 — "Labels become blocked alone — never ready-for-dev +
#   blocked." (patrol treats a gate label as unconditionally actionable;
#   leaving it re-invokes the command every pass)
# source: commands/next-stage.md:218-227 — the unverified-claim check is
#   the STOP exit
# source: references/workflow.md:270-271 — STOP: "replace the issue's
#   status labels with `blocked` alone"
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

labels() { state_query 'sorted(l for l in st["issues"]["5"]["labels"] if l.startswith("status:"))'; }

expect "workflow.md:270-271" "status labels are blocked ALONE" \
  test "$(labels)" = "['status: blocked']"

expect "ledger C1" "the gate label ready-for-dev is gone" \
  test "$(state_query '"status: ready-for-dev" in st["issues"]["5"]["labels"]')" = "False"

expect "workflow.md:272 (STOP obligation 3)" "an issue comment names the evidence" \
  test "$(state_query 'any("unverified" in c["body"] for c in st["issues"]["5"]["comments"])')" = "True"

finish
