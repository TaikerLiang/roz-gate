#!/usr/bin/env bash
# D5 sandbox: D2's shape under a branch_template — `{type}/{user}/{n}/{seq}`,
# issue #5 labelled `type: fix`, branch_user paul. The implementation branch
# is fix/paul/5/1 (not a feat/ ref — D2's literal alone would read every
# touch of it as blind); the QA branch is test/paul/5/1; the spec branch
# spec/paul/5/1. fix/paul/5/1 MUST NOT be touched by the fidelity work.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
printf -- '- branch_template: {type}/{user}/{n}/{seq}\n' >> CLAUDE.md
grep -q '^- branch_template: {type}/{user}/{n}/{seq}$' CLAUDE.md
mkdir -p .claude && printf '{"branch_user": "paul"}\n' > .claude/roz-gate.local.json
grep -q '"branch_user": "paul"' .claude/roz-gate.local.json
printf '.claude/roz-gate.local.json\n' >> .git/info/exclude
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "seed (branch_template)"
git checkout -qb spec/paul/5/1
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

git checkout -qb fix/paul/5/1
mkdir -p src
cat > src/pricing.py <<'EOF'
def price(cart, now):
    return sum(i.cost for i in cart if not i.offer or i.offer.expires_at >= now)
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5"

git checkout -q spec/paul/5/1
git checkout -qb test/paul/5/1
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
