#!/usr/bin/env bash
# D7 sandbox: C17's shape — spec/5 (docs), feat/5 (impl), qa/5 (suite), the
# QA CR without a fidelity summary so patrol runs the audit — plus the
# contract's TEST PORT: a driver that lives in an existing unit-test file
# under src/test/… (ADMC #11's layout), outside acceptance_dir, declared on
# technical-spec.md's `**Test port** — <path>` line. The suite drives the
# port; the blind reviewer must be able to read it and nothing else under
# src/.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
mkdir -p src/test
cat > src/test/offer_port.py <<'EOF'
"""The test port for offer expiry (technical-spec #5): the acceptance suite's
front door — control and observation points, nothing internal."""
from datetime import datetime

from src.pricing import price  # the implementation lands at stage (3)


class OfferPort:
    def __init__(self):
        self.now = datetime(2026, 1, 1)

    def advance_clock(self, days):
        self.now = self.now.replace(day=self.now.day + days)

    def price_cart(self, cart):
        return price(cart, self.now)

    def offer_state(self, offer):
        return "expired" if offer.expires_at < self.now else "active"
EOF
cat > src/test/test_pricing_unit.py <<'EOF'
# a unit test beside the port — NOT the port, never the reviewer's to read
def test_placeholder():
    assert True
EOF
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "seed (test port)"

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
- **C1 (R4)** — `price(cart, now)` excludes offers with `expires_at < now`.
- **Test port** — src/test/offer_port.py
  `OfferPort.advance_clock(days)` and `OfferPort.price_cart(cart)` drive
  pricing; `OfferPort.offer_state(offer)` observes an offer's state.
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
cat > src/pricing.py <<'EOF'
def price(cart, now):
    return sum(i.cost for i in cart if not i.offer or i.offer.expires_at >= now)
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5"

git checkout -q spec/5
git checkout -qb qa/5
mkdir -p tests/acceptance/offers
cat > tests/acceptance/offers/test_expiry.py <<'EOF'
# trace: S1 — drives the contract's test port (src/test/offer_port.py)
from src.test.offer_port import OfferPort


def test_expired_offer():
    port = OfferPort()
    assert port.price_cart([]) == 0  # TODO: seed an expired offer and assert exclusion
EOF
cat > docs/specs/5/test-spec.md <<'EOF'
# Test spec #5
| Scenario | Test |
|---|---|
| S1 | test_expiry.py::test_expired_offer |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "qa suite #5"
git checkout -q main
