#!/usr/bin/env bash
# C13 sandbox: one issue, both CRs merged, no status label — the state after
# a human cleared an integrate STOP (or stripped in-user-review to re-verify
# a spec branch they moved). spec/5 carries the integrated work; feat/5 and
# qa/5 sit at the same commit (a clean already-merged shape: a re-merge is
# "Already up to date", so the pass's end state does not depend on C12's
# rule — this case measures the scanner's row and the route it takes).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
sed -i.bak \
  -e 's#^- test: true$#- test: python3 -m unittest discover -s tests -q#' \
  -e 's#^- acceptance_test: true$#- acceptance_test: python3 -m unittest discover -s tests/acceptance -q#' \
  CLAUDE.md && rm CLAUDE.md.bak
git add CLAUDE.md
git -c user.email=paul@example.com -c user.name=paul commit -qm "C13: real test commands"
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
