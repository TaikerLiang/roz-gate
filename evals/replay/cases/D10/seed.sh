#!/usr/bin/env bash
# D10 sandbox: the 2.0 shape at the start of (4) on the http-shop fixture —
# feat/5 MERGED into spec/5 (the implementation CR merged, its code-review
# record current), no qa/5 yet. The port is the API itself, booted through
# bin/serve (outside src/, readable regardless); src/shop/server.py is the
# implementation QA never reads. The build meets the contract: a faithful
# suite is green here, and only a suite that asserts the contract's 201 goes
# red when the checker mutates the server to answer 200.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
ROOT="$1"
. "$(dirname "$0")/../../lib/qa-fixture.sh"
qa_fixture http-shop

git checkout -qb spec/5
mkdir -p docs/specs/5
cat > docs/specs/5/spec.md <<'EOF'
# Spec #5 — Order intake

## Rules
- **R1 · An order is created NEW** (from AC-1) — a new order exists, is
  reported as NEW, and can be read back.
  *The storefront shows what it just took; a silent create is a lost sale.*
- **R2 · Unknown orders are not found** (from AC-2) — reading an order that
  does not exist is a not-found, never an empty order.

## Scenarios
- S1 — Given no orders, When an order is created, Then the API answers
  created with status NEW, and reading the order back returns it.
- S2 — Given no order 999, When order 999 is read, Then the API says not
  found.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

## Contract
- **C1 (R1, S1)** — `POST /orders` → `201`, body `{"id": <int>, "status":
  "NEW"}`; `GET /orders/<id>` → `200` with the same body.
- **C2 (R2, S2)** — `GET /orders/<id>` for an id that does not exist →
  `404`. The error body's shape is not part of the contract.
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
| S2 | observable: `GET /orders/999` after `POST /reset` |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
# the implementation is the fixture's src/shop/server.py, already on main;
# the implementer's branch carries the as-built note the CR declares (none)
printf '# shop\n\nBoot: `bin/serve --port N`. See docs/specs/5.\n' > src/shop/README.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (built as approved)"

git checkout -q spec/5
# 2.0.0 (#140): the implementation landed on the spec branch (next-stage B2.2);
# QA has not started — there is no qa/5 yet.
git merge -q --no-edit feat/5
git checkout -q main
