#!/usr/bin/env bash
# F11 sandbox: F9's gated repo (the spec branch behind #5's CR) plus the
# spec branch behind #8's CR, and the local key `inbox_label: discuss` so the
# report's filter line has something to say (state.json: six issues the
# scanner lists, one track-less issue outside the filter).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
for n in 5 8; do
  git checkout -qb "spec/$n"
  mkdir -p "docs/specs/$n"
  printf '# Spec #%s\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' "$n" > "docs/specs/$n/spec.md"
  git add -A
  git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #$n"
  git checkout -q main
done
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
