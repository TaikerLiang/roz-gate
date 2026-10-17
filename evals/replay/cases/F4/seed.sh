#!/usr/bin/env bash
# F4 sandbox: the pre-integration shape (2.0, #140: feat/5 merged into
# spec/5 with its code-review record before qa/5 is cut) — spec/5 (docs +
# impl), qa/5 (acceptance tests) off that tip, cleanly mergeable.
# config test / acceptance_test are `true`, so the verdict is green.
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
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
mkdir -p src
cat > src/pricing.py <<'EOF'
def price(cart, now):
    return sum(i.cost for i in cart if not i.offer or i.offer.expires_at >= now)
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5"

git checkout -q spec/5
# 2.0.0 (#140): the implementation lands on the spec branch BEFORE qa/<n>
# is cut — the QA branch carries the code; the hook is the blindness.
git merge -q --no-edit feat/5
git checkout -qb qa/5
mkdir -p tests/acceptance/offers
cat > tests/acceptance/offers/test_expiry.py <<'EOF'
# trace: S1
def test_expired_offer():
    assert True  # exercised via config acceptance_test in this fixture
EOF
cat > docs/specs/5/test-spec.md <<'EOF'
# Test spec #5
| Scenario | Test |
|---|---|
| S1 | test_expiry.py::test_expired_offer |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "qa suite #5"
git checkout -q main
