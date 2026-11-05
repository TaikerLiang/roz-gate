#!/usr/bin/env bash
# C26 sandbox: F13's repo shape (the spec branch behind #5's CR, the local
# key `inbox_label: discuss`) plus the local key `patrol_issues_per_pass: 2`
# (#204). state.json: three `track: fast` issues at `status: ready-for-dev`
# (#6, #8, #9), each gate label applied by paul (`type` User) on a known
# date; #5 in-user-review and quiet; #7 a raw inbox idea. A pass may act on
# two of the three and must leave the third as seeded, with its wait in the
# report.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
printf '# Spec #5\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
python3 "$1/bin/roz-config" patrol_issues_per_pass 2 > /dev/null
grep -q '"patrol_issues_per_pass": "2"' .claude/roz-gate.local.json
