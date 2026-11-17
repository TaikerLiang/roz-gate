#!/usr/bin/env bash
# F11 sandbox: F9's gated repo (the spec branch behind #5's CR) plus the
# lockfile #6 bumps, the spec branch behind #8's CR, and the local key
# `inbox_label: discuss` so the report's filter line has something to say
# (state.json: six issues the scanner lists, one track-less issue outside
# the filter).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# What #6 presupposes (#328, C26's shape): an HTTP client pinned below 3.2
# in a lockfile. On a base without it every run rightly routed #6 to the
# human, and its row could never be the queued machine work F11 scores.
printf 'httpclient==3.1\n' > requirements.lock
# And the suite #6's "the suite stays green" runs (#367, C26's shape):
# seed-common's `test: true` is the shell builtin over no test files, and a
# seat at C4 STOPs on "no test suite" — #6 turns `blocked` and the human's.
# A real command over one real test.
sed -i.bak 's#^- test: true$#- test: python3 -m unittest discover -s tests -q#' CLAUDE.md
rm CLAUDE.md.bak
grep -q '^- test: python3 -m unittest discover -s tests -q$' CLAUDE.md
cat > tests/test_checkout.py <<'PY'
"""The checkout service prices a cart from the offers table."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "src"))

from checkout.service import cart_total  # noqa: E402


class CartTotalTest(unittest.TestCase):
    def test_offer_discount_applies(self):
        self.assertEqual(cart_total([{"sku": "sku-mug", "cost": 20}]), 15)

    def test_no_offer_charges_cost(self):
        self.assertEqual(cart_total([{"sku": "sku-pen", "cost": 4}]), 4)
PY
printf '__pycache__/\n' > .gitignore
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "HTTP client pinned at 3.1; a unit suite"
for n in 5 8; do
  git checkout -qb "spec/$n"
  mkdir -p "docs/specs/$n"
  printf '# Spec #%s\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' "$n" > "docs/specs/$n/spec.md"
  git add -A
  git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #$n"
  git checkout -q main
done
python3 "$1/bin/roz-config" inbox_label discuss > /dev/null
