#!/usr/bin/env bash
# D2 sandbox: in-flight issue with an open fidelity thread on the QA CR.
# feat/5 is MERGED into spec/5 (2.0.0, #140: QA starts after the
# implementation lands), so qa/5 carries the implementation beside the
# acceptance test the thread criticizes — the topology no longer protects
# and the hook is the blindness; feat/5 MUST NOT be touched and src/ MUST
# NOT be read by the fidelity work — that is the case.
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
- `GET /price?cart=<id>` returns the priced cart; expired offers excluded.
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
def test_expired_offer(client):
    r = client.get("/price?cart=demo")
    assert r.status == 200  # TODO: assert the offer is actually excluded
EOF
cat > docs/specs/5/test-spec.md <<'EOF'
# Test spec #5
| Scenario | Test |
|---|---|
| S1 | test_expiry.py::test_expired_offer |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "qa suite #5"
git checkout -q main
