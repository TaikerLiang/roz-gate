#!/usr/bin/env bash
# F15 sandbox: ConsoleAPI #28's shape (#205) — four gated issues whose forge
# relationships say what may run (state.json `blocked_by`): #10 and #11
# wait on open #9 (#11 also names closed #8), #12's only blocker (#8) is
# closed, and #13's lookup is refused (HTTP 403). The local key
# `inbox_label: discuss` keeps the blockers themselves (track-less, no
# `discuss`) out of the inbox, so the pass's one actionable row is #12.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
grep -q '"inbox_label"' .claude/roz-gate.local.json
