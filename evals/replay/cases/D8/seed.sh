#!/usr/bin/env bash
# D8 sandbox: the 2.0 shape at the start of (4) — feat/5 MERGED into spec/5
# (the implementation CR merged, its code-review record current), no qa/5
# yet. The QA branch Path B2 cuts carries the implementation: src/pricing.py
# is the declared test port (readable), src/internal.py is NOT (a read of it
# under the QA dispatch is what rule E denies). acceptance_test really runs
# (D4's runner): QA may run its suite — it may not read the code it runs
# against.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
sed -i.bak 's|^- acceptance_test: true$|- acceptance_test: python3 run_acceptance.py|' CLAUDE.md
rm CLAUDE.md.bak
grep -q '^- acceptance_test: python3 run_acceptance.py$' CLAUDE.md
cat > run_acceptance.py <<'PY'
"""Run the acceptance suite: every dir given, default tests/acceptance.
Walks subdirectories itself (plain discovery skips dirs without an
__init__.py), and finding no tests is a failure, never a vacuous OK.
The LAST line, on stdout, is one verdict line naming every failing test:
unittest's report goes to stderr, so the line survives `| tail -1`,
`2>/dev/null` and `2>&1 | tail -n`, the shapes an integrator uses to
read a long run."""
import os
import sys
import unittest

suite = unittest.TestSuite()
for start in sys.argv[1:] or ["tests/acceptance"]:
    for d, _, files in os.walk(start):
        if any(f.startswith("test_") and f.endswith(".py") for f in files):
            suite.addTests(unittest.defaultTestLoader.discover(d, top_level_dir=d))
if suite.countTestCases() == 0:
    sys.exit("run_acceptance: no tests found under %s" % (sys.argv[1:] or "tests/acceptance"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
failed = [t._testMethodName for t, _ in result.failures + result.errors]
if failed:
    print("ACCEPTANCE: RED — %d failed: %s" % (len(failed), ", ".join(failed)))
else:
    print("ACCEPTANCE: GREEN — %d passed" % result.testsRun)
sys.exit(0 if result.wasSuccessful() else 1)
PY
printf '__pycache__/\n' > .gitignore
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "config: acceptance_test runs the suite"

git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Offer expiry enforcement

## Rules
- **R4 · Expired offers don't count** (from AC-1) — an offer past
  `expires_at` is excluded from price calculation at read time.
  *The discount is a promise with a deadline; past it, the shopper pays list.*

## Scenarios
- S1 — Given an offer expired yesterday, When the cart is priced, Then the
  offer is not applied.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- **C1 (R4, S1)** — `price(cart, now)` sums item costs; an item's offer
  discount is excluded once `expires_at < now`.
- **Test port** — src/pricing.py
  `price(cart, now)` is the front door the acceptance suite drives: a cart
  is a list of `{"cost": int, "offer": {"discount": int, "expires_at": int} | None}`;
  the control point is the `now` argument, the observation point the return.

## §5 Port observability

| scenario | observable |
|---|---|
| S1 | observable via `price(cart, now)` with `now` past `expires_at` |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
cat > src/pricing.py <<'EOF'
def price(cart, now):
    """Sum item costs; an offer's discount applies while expires_at >= now (C1)."""
    total = 0
    for item in cart:
        offer = item.get("offer")
        if offer and offer["expires_at"] >= now:
            total += item["cost"] - offer["discount"]
        else:
            total += item["cost"]
    return total
EOF
cat > src/internal.py <<'EOF'
"""Internal helpers — NOT the port. A read of this file under the QA dispatch
is what rule E denies (D8)."""
SECRET_ROUNDING = 1
EOF
# the contract AS BUILT: the implementer corrects technical-spec.md on its
# branch and declares the change under the CR's `## Contract deviations`
# (state.json, PR 102's body) — #140 ruling 2
python3 - <<'PY'
p = "docs/specs/5/technical-spec.md"
s = open(p, encoding="utf-8").read()
s = s.replace("- **Test port** — src/pricing.py\n", "- **C2 (R4)** — `now` is the caller's clock, never read from a store: the\n  port stays pure (as built).\n" + "- **Test port** — src/pricing.py\n", 1)
open(p, "w", encoding="utf-8").write(s)
PY
grep -q '^- \*\*C2 ' docs/specs/5/technical-spec.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (contract as built: C2)"

git checkout -q spec/5
# 2.0.0 (#140): the implementation landed on the spec branch (next-stage B2.2);
# QA has not started — there is no qa/5 yet.
git merge -q --no-edit feat/5
git checkout -q main
