#!/usr/bin/env bash
# F9 sandbox: a plain gated repo; the forge state carries three issues in
# three states (see state.json). The spec branch exists so #5's CR is real.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
# What #6 presupposes (#328, C26's shape): an HTTP client pinned below 3.2
# in a lockfile. On a base without it a seat rightly STOPs #6 as undoable.
# The name is one no package index can hold (#408): a project name starts
# with a letter or digit, so a seat's index lookup has nothing to contradict
# the pin with — `httpclient` is a real PyPI project with no 3.x.
printf '_acme_httpclient==3.1\n' > requirements.lock
# And the suite #6's "the suite stays green" runs (#367, C26's shape):
# seed-common's `test: true` is the shell builtin over no test files, and a
# seat at C4 STOPs on "no test suite". A real command over one real test.
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
git checkout -qb spec/5
mkdir -p docs/specs/5
printf '# Spec #5\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' > docs/specs/5/spec.md
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
