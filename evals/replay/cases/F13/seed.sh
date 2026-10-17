#!/usr/bin/env bash
# F13 sandbox: F11's repo shape — the spec branch behind #5's CR and the
# local key `inbox_label: discuss` — with two gate labels the forge's
# timeline attributes to a bot (state.json: #6's `ready-for-dev`, #7's
# `ready-for-spec`, both by `roz-bot[bot]`). User mode: `bot_login` is
# empty, so the audit has only the forge's bot shape to go on — the foreign
# agent the hook never saw.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
printf '# Spec #5\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
grep -q '"inbox_label"' .claude/roz-gate.local.json
