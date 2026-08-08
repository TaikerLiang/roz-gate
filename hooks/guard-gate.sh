#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter.
#
# Runs on every Bash tool call in every repo where the plugin is enabled, so
# it must be near-zero cost. Escalates to guard-gate.py (one python startup,
# possibly one forge API call) only when the raw hook input mentions a
# guarded pattern: the intake marker or a gate-label name.
set -u

input=$(cat)

if ! printf '%s' "$input" | grep -qE '\[intake\]|ready-for-(spec|dev)'; then
  exit 0
fi

exec python3 "${BASH_SOURCE[0]%/*}/guard-gate.py" <<EOF
$input
EOF
