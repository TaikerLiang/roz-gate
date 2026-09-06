#!/usr/bin/env bash
# C1/F5 sandbox: an approved spec branch whose spec still carries an
# `(unverified)` empirical claim — Path B's entry check must STOP.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (from Q1) — an offer past `expires_at`
  is excluded from price calculation at read time. *The DB already rejects
  expired rows at the storage layer (unverified), so the API mirrors it.*

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
- **[em] · Q1 · lock strategy** — resolved.
  **Resolved:** (a) row lock — paul, 2026-08-18. *Bounds contention.* Folded
  into R4.
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.

## §5 Port observability
| Scenario | Observability |
|---|---|
| S1 | observable |
EOF
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
