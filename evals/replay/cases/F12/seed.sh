#!/usr/bin/env bash
# F12 sandbox: a spec branch whose spec CR (#101, state.json) is open with
# every thread resolved and nothing unheard — the (2) → (3) gate is the
# human's `ready-for-dev`. tip must say so and write nothing.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF2'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (assumed) — an offer past `expires_at`
  is excluded from price calculation at read time.
- **R5 · Open-cart expiry is re-checked at checkout** (from Q1) — an offer
  that expires while the cart is open is re-evaluated when the cart is
  checked out.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.
- S2 — Given an offer that expires while the cart is open, When the cart is
  checked out, Then the offer is not applied.

## Open Questions
(none)
EOF2
cat > docs/specs/5/technical-spec.md <<'EOF2'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
- `checkout(cart, now)` re-prices with the same rule before committing.
EOF2
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
