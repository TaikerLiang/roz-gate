#!/usr/bin/env bash
# C30 sandbox: C13's shape twice (#207). Two issues, #5 and #6, each with
# both CRs merged and no status label — spec/<n> carries the integrated
# work; feat/<n> and qa/<n> sit at the same commit (a re-merge is "Already
# up to date"). No local `patrol_issues_per_pass`, so N=1: the pass may
# integrate one of the two and must leave the other as seeded, its row
# reading `queued: integrate` in the report.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
sed -i.bak \
  -e 's#^- test: true$#- test: python3 -m unittest discover -s tests -q#' \
  -e 's#^- acceptance_test: true$#- acceptance_test: python3 -m unittest discover -s tests/acceptance -q#' \
  CLAUDE.md && rm CLAUDE.md.bak
grep -q 'discover -s tests/acceptance -q' CLAUDE.md
git add CLAUDE.md
git -c user.email=paul@example.com -c user.name=paul commit -qm "C30: real test commands"

# ---- #5 · Offer expiry enforcement -------------------------------------------
git checkout -qb spec/5
mkdir -p docs/specs/5 src tests/acceptance
cat > docs/specs/5/spec.md <<'MD'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** — an offer past `expires_at` is
  excluded from price calculation at read time.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.
MD
cat > docs/specs/5/technical-spec.md <<'MD'
# Technical spec #5

**Test port** — none

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
MD
cat > docs/specs/5/test-spec.md <<'MD'
# Test spec #5
| Scenario | Test |
|---|---|
| S1 | test_expiry.py::test_s1_expired_offer_is_not_applied |
MD
cat > src/offers.py <<'PY'
def price(cart, now):
    """R4: an offer past expires_at is excluded at read time."""
    total = sum(item["price"] for item in cart["items"])
    for offer in cart.get("offers", []):
        if offer["expires_at"] < now:
            continue
        total -= offer["amount"]
    return total
PY
printf '__pycache__/\n' > .gitignore
: > tests/acceptance/__init__.py
cat > tests/acceptance/test_expiry.py <<'PY'
"""S1 — Given an offer expired yesterday, When the cart is priced, Then the
offer is not applied."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from offers import price  # noqa: E402


class TestExpiry(unittest.TestCase):
    def test_s1_expired_offer_is_not_applied(self):
        cart = {"items": [{"price": 100}],
                "offers": [{"amount": 10, "expires_at": 1}]}
        self.assertEqual(price(cart, now=2), 100)
PY
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "integrated #5 (spec + feat + qa merged)"
git branch -q feat/5
git branch -q qa/5
git checkout -q main

# ---- #6 · Free shipping over the threshold ------------------------------------
git checkout -qb spec/6
mkdir -p docs/specs/6 src tests/acceptance
cat > docs/specs/6/spec.md <<'MD'
# Spec #6 — Free shipping over the threshold

## Rules
- **R1 · Free shipping at 50** — a cart whose item total is 50 or more
  ships free; below it, shipping is 5.

## Scenarios
- S1 — Given items totalling 50, When shipping is computed, Then it is 0.
MD
cat > docs/specs/6/technical-spec.md <<'MD'
# Technical spec #6

**Test port** — none

## Contract
- `shipping(cart)` returns 0 when the item total is >= 50, else 5.
MD
cat > docs/specs/6/test-spec.md <<'MD'
# Test spec #6
| Scenario | Test |
|---|---|
| S1 | test_shipping.py::test_s1_threshold_ships_free |
MD
cat > src/shipping.py <<'PY'
def shipping(cart):
    """R1: 50 or more ships free; below it, 5."""
    total = sum(item["price"] for item in cart["items"])
    return 0 if total >= 50 else 5
PY
printf '__pycache__/\n' > .gitignore
: > tests/acceptance/__init__.py
cat > tests/acceptance/test_shipping.py <<'PY'
"""S1 — Given items totalling 50, When shipping is computed, Then it is 0."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from shipping import shipping  # noqa: E402


class TestShipping(unittest.TestCase):
    def test_s1_threshold_ships_free(self):
        self.assertEqual(shipping({"items": [{"price": 50}]}), 0)
PY
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "integrated #6 (spec + feat + qa merged)"
git branch -q feat/6
git branch -q qa/6
git checkout -q main
