#!/usr/bin/env bash
# D26 sandbox: D25's Path B entry — spec/5 approved, the spec CR (#101) open
# with its spec-gate kit, #5 `ready-for-dev` (state.json) — with the
# implementer seat unmapped: no `implementer` line in the personas block and
# no .claude/agents/implementer.md. bin/roz-persona answers PERSONA_UNMAPPED
# (#198 ruling 1); the run must STOP before it writes, never seat a stand-in.
# lib/seed-common.sh is not edited — the block changes here.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
sed -i.bak \
  -e '/^- implementer: implementer$/d' \
  -e 's#^- test: true$#- test: python3 -m unittest discover -s tests -q#' \
  CLAUDE.md && rm CLAUDE.md.bak
if grep -q '^- implementer:' CLAUDE.md; then exit 1; fi
grep -q '^- test: python3 -m unittest discover -s tests -q$' CLAUDE.md
git rm -q .claude/agents/implementer.md
python3 "$1/bin/roz-persona" implementer 2>/dev/null | grep -q '"failure": "PERSONA_UNMAPPED"'
printf '__pycache__/\n' > .gitignore
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "personas: no implementer seat"

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
- S2 — Given an offer that expires tomorrow, When the cart is priced, Then
  the offer is applied.

## Open Questions
(none)
EOF
cat > docs/specs/5/technical-spec.md <<'EOF'
# Technical spec #5

**Test port** — src/pricing.py

## Contract
- **C1 (R4, S1, S2)** — `price(cart, now)` sums item costs; an item's offer
  discount applies while `now < expires_at` and is excluded once
  `expires_at <= now`. A cart is a list of
  `{"cost": int, "offer": {"discount": int, "expires_at": int} | None}`;
  times are epoch seconds.

## §5 Port observability

| scenario | control point | observation point |
|---|---|---|
| S1 | the `now` argument, past `expires_at` | the return value |
| S2 | the `now` argument, before `expires_at` | the return value |
EOF
git add -A
git -c user.email=paul@example.com -c user.name=paul commit -qm "spec docs #5"
git checkout -q main
