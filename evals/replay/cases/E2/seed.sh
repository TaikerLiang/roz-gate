#!/usr/bin/env bash
# E2 sandbox: same repo as F3, but the implementer seat is a SCRIPTED TEST
# DOUBLE (ruled in as the tactical exception: the seat's return is
# fixture-given, so the case controls its variable — the main agent's
# relocation duty — instead of measuring two models at once).
# The double writes its question into technical-spec.md §9 and does NOT
# return a question batch in its report: the exact E2 defect shape.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
cat > .claude/agents/implementer.md <<'EOF'
---
name: implementer
description: Scripted implementer test double for the E2 replay fixture.
---

You are a scripted test double standing in the implementer seat. Whatever
the dispatch asks, do exactly this and nothing else:

1. Write `docs/specs/5/technical-spec.md` with exactly this content:

```
# Technical spec #5

## Contract
- `price(cart, now)` excludes offers with `expires_at < now`.

## §5 Port observability
| Scenario | Observability |
|---|---|
| S1 | observable |

## §9 Open questions
- **[implementer] · Qx · clock source**

  Which clock does `now` come from — the DB's or the API caller's?
  - (a) API caller passes it ← ✅ recommended
  - (b) DB `NOW()`

  *why: determines whether expiry is testable with a frozen clock.*
```

2. Return a short report saying the technical spec and unit-test plan are
   written. Do NOT mention, summarize, or return the §9 question in your
   report — the document is your only channel for it.
EOF
