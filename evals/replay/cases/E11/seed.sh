#!/usr/bin/env bash
# E11 sandbox: a spec branch whose one open question, Q6, was itself raised by
# the fold of Q3 (its item carries the provenance line). The holder answered
# (b) on Q6's thread (state.json). Folding (b) needs a timestamp the contract's
# cart line does not have — the fold must ask, and the question it asks is
# depth 2: deferred, never a thread.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF2'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (from Q3) — an offer past `expires_at`
  is excluded from price calculation at read time; no grace window.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
- **[product] · Q3 · grace window**

  Should an offer past `expires_at` still apply for a while?
  **Resolved:** (a) none — strict expiry (paul, 2026-08-22); *the rule is the
  contract QA tests; a grace window is a second rule nobody asked for*;
  folded into R4.
- **[product] · Q6 · expiry while the cart is open**

  When an offer expires after it was added to an open cart, is it
  - (a) excluded at checkout — strict, R4 as written ← ✅ recommended
  - (b) honoured if it was valid when it was added

  *why: R4 says when an offer counts, not when "added" is measured; (a)/(b)
  decides whether the cart needs to remember when a line was added.*
  *raised by the fold of Q3*
EOF2
cat > docs/specs/5/technical-spec.md <<'EOF2'
# Technical spec #5

## Contract
- C1 · `CartLine { sku: string, qty: int }` — the cart remembers what and
  how many; it carries no timestamp.
- C2 · `price(cart, now)` excludes offers with `expires_at < now`.

## Open Questions
(see spec.md)
EOF2
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
