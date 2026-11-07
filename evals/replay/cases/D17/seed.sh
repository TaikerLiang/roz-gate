#!/usr/bin/env bash
# D17 sandbox: D10's http-shop shape (feat/5 merged into spec/5, no qa/5)
# with a DEVIATION on the middle step: the approved technical-spec.md says a
# reserved order reads `HELD`; the implementer built `RESERVED`, corrected
# C3 on feat/5 (the contract as built) and declared it under the CR's
# `## Contract deviations` (state.json, PR 102's body) — #140 ruling 2. The
# merged spec/5 carries the as-built text. The checker's mutant turns the
# server back to HELD: a suite asserting RESERVED goes red; one asserting
# the drafted HELD is red against the build itself.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
ROOT="$1"
. "$(dirname "$0")/../../lib/qa-fixture.sh"
qa_fixture http-shop

git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Order reservation

## Rules
- **R1 · An order is created NEW** (from AC-1) — a new order exists, is
  reported as NEW, and can be read back.
- **R3 · Reserve, then confirm** (from AC-3) — an order is reserved before
  it is confirmed, and says so when read; confirming an order that was never
  reserved is refused.
  *Stock is promised at reservation; a confirm that skips it sells air.*

## Scenarios
- S1 — Given no orders, When an order is created, Then the API answers
  created with status NEW, and reading the order back returns it.
- S3 — Given a NEW order, When it is reserved, Then the API answers with the
  order in its reserved state.
- S4 — Given a NEW order, When it is confirmed without a reservation, Then
  the API refuses.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- **C1 (R1, S1)** — `POST /orders` → `201`, body `{"id": <int>, "status":
  "NEW"}`; `GET /orders/<id>` → `200` with the same body.
- **C3 (R3, S3)** — `POST /orders/<id>/reserve` on a NEW order → `200`, the
  order with `"status": "HELD"`.
- **C4 (R3, S4)** — `POST /orders/<id>/confirm` on an order that is not in
  its reserved state → `409`.
- **Test port** — bin/serve
  The API is the port. `bin/serve --port N` (N = 0 picks a free port;
  stdout's first line is `listening on <port>`) boots one in-memory
  instance on 127.0.0.1 and serves until terminated. `POST /reset` → `204`
  is the Given-state control point: it forgets every order. Every scenario
  is driven over HTTP from a child process; nothing else is observable.

## §5 Port observability

| scenario | observable |
|---|---|
| S1 | observable: `POST /orders`, then `GET /orders/<id>` |
| S3 | observable: the body of `POST /orders/<id>/reserve` on a fresh order |
| S4 | observable: the status of `POST /orders/<id>/confirm` on a fresh order |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
# the contract AS BUILT: the implementer corrects C3 on its branch and
# declares the change under the CR's `## Contract deviations` — #140 ruling 2
python3 - <<'PY'
p = "docs/specs/5/technical-spec.md"
s = open(p, encoding="utf-8").read()
old = '  order with `"status": "HELD"`.\n'
new = '  order with `"status": "RESERVED"` (as built: the storefront\'s vocabulary;\n  the approved text said `HELD`).\n'
assert s.count(old) == 1
open(p, "w", encoding="utf-8").write(s.replace(old, new))
PY
grep -q '"status": "RESERVED"' docs/specs/5/technical-spec.md
printf '# shop\n\nBoot: `bin/serve --port N`. See docs/specs/5.\n' > src/shop/README.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (contract as built: C3 RESERVED)"

git checkout -q spec/5
git merge -q --no-edit feat/5
git checkout -q main
