#!/usr/bin/env bash
# E5 · An answer folds into the document that owns it.
# Fixture: a resolved [implementer] thread whose ruling (caller-passed
# clock) changes a contract clause that currently says "open question".
# source: ledger E5 — "technical-spec.md is modified. The spec.md entry
#   records the resolution and points at the clause." (folded as prose
#   beside the question instead, the contract never changes, QA derives
#   from the unchanged contract, and the defect ships with a resolved
#   thread pointing at it)
# source: commands/spec-answers.md:60-64 — fold the decision into the
#   document the raising seat owns: technical-spec.md for [implementer]
#   questions; a fold that lands as prose near the question while the
#   contract text stays unchanged ships the defect
# source: commands/spec-answers.md:93-95 — reply `✅ [<role>] resolved`
#   then THREAD-RESOLVE
set -u
. "$(dirname "$0")/../../lib/checklib.sh"

expect "spec-answers.md:60-62 (the owning document changed)" \
  "a pushed commit beyond the seed touches technical-spec.md" \
  bash -c 'test "$(git -C "$BARE" log spec/5 --oneline --follow -- docs/specs/5/technical-spec.md | wc -l | tr -d " ")" -ge 2'

expect "ledger E5 (the contract learned the answer)" \
  "the contract clause no longer defers the clock source" \
  bash -c '! git -C "$BARE" show spec/5:docs/specs/5/technical-spec.md | grep -q "open question"'

expect "spec-answers.md:93-95" "the thread was resolved" \
  grep -q '"route": "thread-resolve"' "$RUN_DIR/forge/journal.jsonl"

expect "spec-answers.md:93-94" "the resolution reply opens with ✅ [" \
  bash -c 'grep "\"route\": \"thread-reply\"" "$RUN_DIR/forge/journal.jsonl" | grep -q "\"body\": \"✅ \["'

finish
