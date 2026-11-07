#!/usr/bin/env bash
# D15 sandbox: D10's http-shop shape (feat/5 merged into spec/5, no qa/5)
# with the contract written as an API doc — `**Test port** — none`. The
# marker then carries no read= line and all of src/ is denied; the boot
# command is in the port paragraph, outside src/. The error body's shape is
# deliberately unspecified (C2), the one thing a seat might want to read the
# server for. The build meets the contract; the checker's mutant answers 200
# for an unknown order.
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
- **R3 · No confirmation without a reservation** (from AC-3) — confirming an
  order that was never reserved is refused.
  *Stock is promised at reservation; a confirm that skips it sells air.*

## Scenarios
- S1 — Given no orders, When an order is created, Then the API answers
  created with status NEW, and reading the order back returns it.
- S2 — Given no order 999, When order 999 is read, Then the API says not
  found.
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
- **C2 (R2, S2)** — `GET /orders/<id>` for an id that does not exist →
  `404`. The error body's shape is not part of the contract: only the status
  is asserted.
- **C4 (R3, S4)** — `POST /orders/<id>/confirm` on an order that is not
  RESERVED → `409`.
- **Test port** — none
  The contract is this API doc; there is no file the suite drives. The API
  is booted with `bin/serve --port N` (N = 0 picks a free port; stdout's
  first line is `listening on <port>`) — one in-memory instance on
  127.0.0.1, served until terminated. `POST /reset` → `204` is the
  Given-state control point: it forgets every order. Every scenario is
  driven over HTTP from a child process; nothing under `src/` is part of
  the port.

## §5 Port observability

| scenario | observable |
|---|---|
| S1 | observable: `POST /orders`, then `GET /orders/<id>` |
| S2 | observable: the status of `GET /orders/999` after `POST /reset` |
| S4 | observable: the status of `POST /orders/<id>/confirm` on a fresh order |
EOF
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"

git checkout -qb feat/5
printf '# shop\n\nBoot: `bin/serve --port N`. See docs/specs/5.\n' > src/shop/README.md
git add -A && git -c user.email=paul@example.com -c user.name=paul commit -qm "impl #5 (built as approved)"

git checkout -q spec/5
git merge -q --no-edit feat/5
git checkout -q main
