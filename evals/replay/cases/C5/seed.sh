#!/usr/bin/env bash
# C5 sandbox: the post-integration shape — spec/5 already contains the
# merged implementation and QA work; the issue re-entered (2a) from (7).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# Live opus sweep, 4/5: seed-common's `test: true` is the shell builtin —
# a vacuous suite — and the hand-back rule (spec-answers.md:145-149,
# workflow.md:166-168) wants a captured green run; four runs STOPPED on
# "true is not a test run", one proceeded with a flag. Both defensible,
# neither is what C5 measures (the re-entry BRANCH). A real minimal test
# behind real commands lets the rule be honoured honestly. The vacuous-
# config question itself (STOP or proceed-with-flag) is an open rule
# question for Paul, deliberately not resolved here.
sed -i.bak \
  -e 's#^- test: true$#- test: python3 -m unittest discover -s tests -q#' \
  -e 's#^- acceptance_test: true$#- acceptance_test: python3 -m unittest discover -s tests/acceptance -q#' \
  CLAUDE.md && rm CLAUDE.md.bak
git checkout -qb spec/5
mkdir -p docs/specs/5 src tests/acceptance
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (from Q1) — an offer past `expires_at`
  is excluded from price calculation at read time.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
- **[em] · Q3 · grace window** — open, thread on the spec CR.
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
EOF
cat > src/offers.py <<'EOF'
def price(cart, now):
    """R4: an offer past expires_at is excluded at read time."""
    total = sum(item["price"] for item in cart["items"])
    for offer in cart.get("offers", []):
        if offer["expires_at"] < now:
            continue
        total -= offer["amount"]
    return total
EOF
printf '__pycache__/\n' > .gitignore
: > tests/acceptance/__init__.py
cat > tests/acceptance/test_expiry.py <<'EOF'
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
EOF
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "integrated #5 (spec + feat + qa merged)"
git branch -q feat/5
git branch -q qa/5
git checkout -q main
