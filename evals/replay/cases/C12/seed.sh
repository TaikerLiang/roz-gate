#!/usr/bin/env bash
# C12 sandbox: issue #77's shape. spec/5 already carries the integrated
# work (spec + implementation + suite) and then MOVED on its own — one later
# commit reworded the expiry reason in src and in the test, the way a
# rebase or a sync with concurrent work moves an integration branch.
# feat/5 and qa/5 are the STALE tips: their content was incorporated, but
# the commits are not ancestors of spec/5 (the branch was rewritten after
# the merge), and each carries a file spec/5 later changed — re-merging
# either is an add/add conflict. The forge shows both CRs merged.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# Real test commands, committed on main before branching (C5's lesson: a
# `true` suite is vacuous and the hand-back rule wants a captured run).
sed -i.bak \
  -e 's#^- test: true$#- test: python3 -m unittest discover -s tests -q#' \
  -e 's#^- acceptance_test: true$#- acceptance_test: python3 -m unittest discover -s tests/acceptance -q#' \
  CLAUDE.md && rm CLAUDE.md.bak
git add CLAUDE.md
git -c user.email=paul@example.com -c user.name=paul commit -qm "C12: real test commands"

write_spec() {
  mkdir -p docs/specs/5
  cat > docs/specs/5/spec.md <<'MD'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** — an offer past `expires_at` is
  excluded from price calculation at read time, and the exclusion carries
  a reason.

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied and the reason names expiry.
MD
  cat > docs/specs/5/technical-spec.md <<'MD'
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.
- `reason(offer, now)` returns a short string naming why an offer was
  excluded; empty when it applies.
MD
}
write_src() {  # $1 = the reason wording
  mkdir -p src
  cat > src/offers.py <<PY
def reason(offer, now):
    """R4: an offer past expires_at is excluded at read time."""
    if offer["expires_at"] < now:
        return "$1"
    return ""


def price(cart, now):
    total = sum(item["price"] for item in cart["items"])
    for offer in cart.get("offers", []):
        if reason(offer, now):
            continue
        total -= offer["amount"]
    return total
PY
}
write_suite() {  # $1 = the reason wording the test expects
  mkdir -p tests/acceptance
  : > tests/acceptance/__init__.py
  cat > tests/acceptance/test_expiry.py <<PY
"""S1 — Given an offer expired yesterday, When the cart is priced, Then the
offer is not applied and the reason names expiry."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from offers import price, reason  # noqa: E402


class TestExpiry(unittest.TestCase):
    def test_s1_expired_offer_is_not_applied(self):
        cart = {"items": [{"price": 100}],
                "offers": [{"amount": 10, "expires_at": 1}]}
        self.assertEqual(price(cart, now=2), 100)

    def test_s1_reason_names_expiry(self):
        self.assertEqual(reason({"expires_at": 1}, now=2), "$1")
PY
  cat > docs/specs/5/test-spec.md <<'MD'
# Test spec #5
| Scenario | Test |
|---|---|
| S1 | test_expiry.py::test_s1_expired_offer_is_not_applied, test_s1_reason_names_expiry |
MD
}
printf '__pycache__/\n' > .gitignore

# spec/5 — the integrated branch, then its independent move.
git checkout -qb spec/5
write_spec
write_src "expired"
write_suite "expired"
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "integrated #5 (spec + feat + qa merged)"
write_src "offer expired"
write_suite "offer expired"
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "sync with concurrent work: reason wording"

# feat/5 — the stale implementation tip: same content as the first
# integration, as a commit spec/5 does not descend from.
git checkout -q main
git checkout -qb feat/5
write_src "expired"
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5"

# qa/5 — the stale suite tip, likewise.
git checkout -q main
git checkout -qb qa/5
write_spec
write_suite "expired"
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "qa suite #5"
git checkout -q main
