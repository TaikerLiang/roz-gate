#!/usr/bin/env bash
# E5 sandbox: spec branch whose technical-spec contract does NOT yet state
# the clock source; the [implementer] thread's ruling must land there.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** — an offer past `expires_at` is
  excluded from price calculation at read time.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
- **[implementer] · Q2 · clock source**

  Which clock does `now` come from — the DB's or the API caller's?
  - (a) API caller passes it ← ✅ recommended
  - (b) DB `NOW()`

  *why: determines whether expiry is testable with a frozen clock.*
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
- The source of `now` is an open question (Q2, see spec.md).
EOF
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
