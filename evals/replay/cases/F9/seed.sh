#!/usr/bin/env bash
# F9 sandbox: a plain gated repo; the forge state carries three issues in
# three states (see state.json). The spec branch exists so #5's CR is real.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# What #6 presupposes (#328, C26's shape): an HTTP client pinned below 3.2
# in a lockfile. On a base without it a seat rightly STOPs #6 as undoable.
printf 'httpclient==3.1\n' > requirements.lock
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "HTTP client pinned at 3.1"
git checkout -qb spec/5
mkdir -p docs/specs/5
printf '# Spec #5\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
