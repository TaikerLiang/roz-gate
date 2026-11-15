#!/usr/bin/env bash
# E15 sandbox: C32's rules and contract, before signing. Two open questions,
# both answered "demote it" (state.json): Q1 on R2's premise (about 2M rows —
# G2's p95 budget and S2 rest on it), Q2 on R1's premise (named debt for #7 —
# nothing depends on it). The fold must refuse Q1's demotion and ask once,
# and apply Q2's (#256).
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
- **[em] · Q1 · production row count**

  R2's premise — about 2M rows in `offers` — is not yet measured. Before signing:
  - (a) measure the production row count ← ✅ recommended
  - (b) demote it to an assumed-empirical premise with its risk named

  *why: G2's p95 budget and S2 are sized on that count.*
- **[em] · Q2 · legacy view debt**

  R1's note — the export still reads `offers_v1` — is not yet measured. Before signing:
  - (a) demote it to an assumed-empirical premise, the risk being #7's ← ✅ recommended
  - (b) measure it now

  *why: nothing in this spec reads that view; #7 retires it.*
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
