#!/usr/bin/env bash
# C2 sandbox (A4's shape): gated repo with spec/5 and its docs; the CR
# itself is CLOSED in the forge fixture — the no-blocked-exit case.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (from Q1) — an offer past `expires_at`
  is excluded from price calculation at read time.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
(none — all resolved)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`. `now` is the
  pricing call's clock, passed by the caller.
EOF
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
