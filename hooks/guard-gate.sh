#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter.
#
# Runs on every Bash tool call in every repo where the plugin is enabled, so
# it must be near-zero cost. Escalates to guard_gate.py (one python startup,
# possibly one forge API call) only when the raw hook input mentions a
# guarded pattern: the intake marker or a gate-label name.
set -u

input=$(cat)

# Marker tokens (`**[` / `✅ [`) escalate for the quote-open rule; the ✅ may
# arrive JSON-escaped as ✅ depending on the caller's encoder. body-file
# forms escalate marker-blind: their body (and so the marker) lives outside
# the command text. `git … commit` escalates for rule D (the open-questions
# section check), `pr create` / `mr create` for rule H (the contract
# deviations section), `roz-gate/wt` for rule J (the loop's worktree add
# runs alone) — the python side confirms the segment shape.
if ! printf '%s' "$input" | grep -qE '\[intake\]|ready-for-(spec|dev)|\*\*\[|✅ \[|\\u2705 \[|Q[0-9]+ (·|\\u00b7)|body-file|-F |git .*commit|roz-gate/wt|pr create|mr create'; then
  exit 0
fi

exec python3 "${BASH_SOURCE[0]%/*}/guard_gate.py" <<EOF
$input
EOF
