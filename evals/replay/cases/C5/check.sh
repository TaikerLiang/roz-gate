#!/usr/bin/env bash
# C5 · Post-integration re-entry has a branch of its own.
# Fixture: in-spec-review re-entered from (7); feat/5 and qa/5 both MERGED,
# spec CR open with the holder's answer waiting in a thread.
# source: ledger C5 — "Folds, re-runs if behaviour changed, returns the
#   issue to in-user-review." (without it the first-pass branch fires and
#   tells a shipped feature it is ready to move to implementation)
# source: commands/spec-answers.md:139-149 — post-integration re-entry:
#   fold, hand-back re-run, LABEL-REMOVE in-spec-review+processing,
#   LABEL-ADD in-user-review
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "spec-answers.md:147-148" "issue returned to in-user-review" \
  test "$(state_query '"status: in-user-review" in st["issues"]["5"]["labels"]')" = "True"

expect "spec-answers.md:147" "in-spec-review removed" \
  test "$(state_query '"status: in-spec-review" in st["issues"]["5"]["labels"]')" = "False"

expect "spec-answers.md:147" "processing lock not left behind" \
  test "$(state_query '"status: processing" in st["issues"]["5"]["labels"]')" = "False"

# The wrong branch announces "ready for approval to move to implementation"
# (spec-answers.md:130-131) — on a shipped feature that is the C5 defect.
expect "ledger C5 (never back to implementation)" "no ready-for-implementation announcement" \
  test "$(state_query 'any("move to implementation" in c["body"] for c in st["issues"]["5"]["comments"])')" = "False"

expect "spec-answers.md:93-95" "the thread was resolved with the ✅ marker" \
  grep -q '"route": "thread-resolve"' "$RUN_DIR/forge/journal.jsonl"

finish
