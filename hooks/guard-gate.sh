#!/usr/bin/env bash
# Roz Gate enforcement — layer 1: prefilter.
#
# Runs on every Bash tool call in every repo where the plugin is enabled, so
# it must be near-zero cost. Escalates to guard-gate.py (one python startup,
# possibly one forge API call) only when the raw hook input mentions a
# guarded pattern: the intake marker or a gate-label name.
set -u

input=$(cat)

# Marker tokens (`**[` / `✅ [`) escalate for the quote-open rule; the ✅ may
# arrive JSON-escaped as ✅ depending on the caller's encoder. body-file
# forms escalate marker-blind: their body (and so the marker) lives outside
# the command text.
if ! printf '%s' "$input" | grep -qE '\[intake\]|ready-for-(spec|dev)|\*\*\[|✅ \[|\\u2705 \[|body-file|-F '; then
  exit 0
fi

exec python3 "${BASH_SOURCE[0]%/*}/guard-gate.py" <<EOF
$input
EOF
