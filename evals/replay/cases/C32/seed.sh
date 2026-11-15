#!/usr/bin/env bash
# C32 sandbox: an approved spec branch with two `(unverified)` premises.
# R2's — the production `offers` table holds about 2M rows — is what G2's
# p95 budget and S2 rest on; R1's — named debt for #7 — backs no guarantee,
# scenario or acceptance criterion. Path B's entry check must STOP and review
# each hit (#256). E15 seeds the same rules and contract.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF2'
# Spec #5 — Offer lookup at checkout

## Rules
- **R1 · Expired offers don't count** (from AC-1) — an offer past
  `expires_at` is excluded from price calculation at read time. *Named
  debt: the nightly export still reads the legacy `offers_v1` view
  (unverified); retiring it is #7, and nothing in this spec reads that view.*
- **R2 · Offer lookup stays fast at production scale** (from AC-2) — pricing
  a cart looks up its offers within the budget G2 sets. *The production
  `offers` table holds about 2M rows (unverified), so one indexed query
  meets the budget without a cache.*

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the offer is not applied.
- S2 — Given 2M offers in the table, When a cart is priced, Then the price returns within 1 s at p95.

## Open Questions
none
EOF2
cat > docs/specs/5/technical-spec.md <<'EOF2'
# Technical spec #5

## Guarantees
- G1 · `price(cart, now)` excludes offers with `expires_at < now` (R1, S1).
- G2 · p95 ≤ 1 s for `price(cart, now)` at production scale (R2, S2).

## Contract
- C1 · `price(cart, now) -> Money` — one indexed query on `offers(sku, expires_at)`.

**Test port** — none

## §5 Port observability
| Scenario | Observability |
|---|---|
| S1 | observable |
| S2 | observable |
EOF2
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
