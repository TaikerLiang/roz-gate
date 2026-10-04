#!/usr/bin/env bash
# E6 sandbox: a spec branch with no open question left; the human opened a
# thread on spec.md themselves saying what the spec misses (state.json).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF2'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (assumed) — an offer past `expires_at`
  is excluded from price calculation at read time.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
(none)
EOF2
cat > docs/specs/5/technical-spec.md <<'EOF2'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
EOF2
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
