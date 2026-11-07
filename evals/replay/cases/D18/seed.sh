#!/usr/bin/env bash
# D18 sandbox: D8's shape on the pricing fixture — feat/5 MERGED into spec/5
# (the implementation CR merged, its code-review record current), no qa/5
# yet. src/pricing.py is the declared test port (readable), src/internal.py
# is NOT: a read of it under the QA dispatch is what rule E denies — and in
# the frame, what fails the case. The build meets C1; the checker's mutant
# ignores expiry (price returns 7 for the expired cart).
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
ROOT="$1"
. "$(dirname "$0")/../../lib/qa-fixture.sh"
qa_fixture pricing

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
git merge -q --no-edit feat/5
git checkout -q main
