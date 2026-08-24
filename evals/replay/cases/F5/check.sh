#!/usr/bin/env bash
# F5 · A STOP leaves nothing half-done.
# Fixture: Path B entry with an `(unverified)` claim in the spec (same
# fixture as C1 — C1 pins the label discipline, F5 the whole-run STOP).
# source: ledger F5 — "Labels are blocked alone; an issue comment names the
#   claims and the remedy; no branch pushed, no CR opened, no remote write
#   of any kind." (five obligations in one paragraph; four of five
#   honoured looks like success in every log)
# source: commands/next-stage.md:218-227 — STOP lists the claims,
#   recommendation: measure or demote
# source: references/workflow.md:269-273 — the STOP protocol's obligations
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

labels() { state_query 'sorted(l for l in st["issues"]["5"]["labels"] if l.startswith("status:"))'; }

expect "workflow.md:270-271" "status labels are blocked ALONE" \
  test "$(labels)" = "['status: blocked']"

expect "next-stage.md:219-220 (lists the claims)" "the STOP comment names the unverified claim" \
  test "$(state_query 'any("unverified" in c["body"] for c in st["issues"]["5"]["comments"])')" = "True"

expect "next-stage.md:220-221 (the remedy)" "the STOP comment carries the measure-or-demote recommendation" \
  test "$(state_query 'any(("measure" in c["body"].lower() or "assumed-empirical" in c["body"]) for c in st["issues"]["5"]["comments"])')" = "True"

expect "ledger F5 (no CR opened)" "zero CRs created" \
  test "$(journal_writes '^pr-create$')" = 0

# Seeded refs are main + spec/5; a STOP pushes nothing new.
expect "ledger F5 (no branch pushed, no remote write)" "no new ref on the remote" \
  test "$(git -C "$BARE" for-each-ref | wc -l | tr -d ' ')" = 2

finish
