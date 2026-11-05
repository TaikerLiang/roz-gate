#!/usr/bin/env bash
# F14 sandbox: ConsoleAPI #27's shape (#209) — spec/5 already carries the
# merged implementation, the QA CR is open, audited and thread-clean, and
# the holder applied `status: ready-for-dev` again after Path B had
# consumed it (state.json: the label's latest `labeled` event is paul's,
# after the implementation CR merged).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
git checkout -qb spec/5
mkdir -p docs/specs/5 src tests/acceptance
printf '# Spec #5\n\n## Rules\n- **R1 · Expired offers do not apply**\n\n## Scenarios\n- S1 — Given an expired offer, When the cart is priced, Then it is not applied.\n' > docs/specs/5/spec.md
printf '# Technical spec #5\n\n**Test port** — none\n\n## Contract\n- `price(cart, now)` excludes offers with `expires_at < now`.\n' > docs/specs/5/technical-spec.md
cat > src/offers.py <<'PY'
def price(cart, now):
    total = sum(item["price"] for item in cart["items"])
    for offer in cart.get("offers", []):
        if offer["expires_at"] < now:
            continue
        total -= offer["amount"]
    return total
PY
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec #5 + merged implementation (feat/5)"
git branch -q feat/5
git checkout -qb qa/5
: > tests/acceptance/__init__.py
printf 'import unittest\n\n\nclass TestExpiry(unittest.TestCase):\n    def test_s1(self):\n        pass\n' > tests/acceptance/test_expiry.py
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "qa #5: black-box suite"
git checkout -q main
