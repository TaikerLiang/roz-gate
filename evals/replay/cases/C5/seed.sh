#!/usr/bin/env bash
# C5 sandbox: the post-integration shape — spec/5 already contains the
# merged implementation and QA work; the issue re-entered (2a) from (7).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5 src tests/acceptance/offers
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (from Q1) — an offer past `expires_at`
  is excluded from price calculation at read time.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
- **[em] · Q3 · grace window** — open, thread on the spec CR.
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
EOF
echo "def price(cart, now): ..." > src/offers.py
echo "# S1 acceptance" > tests/acceptance/offers/test_expiry.py
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "integrated #5 (spec + feat + qa merged)"
git branch -q feat/5
git branch -q qa/5
git checkout -q main
