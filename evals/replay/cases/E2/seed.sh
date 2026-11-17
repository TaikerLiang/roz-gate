#!/usr/bin/env bash
# E2 sandbox: same repo as F3, but the implementer seat's return is
# fixture-given (ruled in as the tactical exception: the case controls its
# variable — the main agent's relocation duty — instead of measuring two
# models at once). The seat writes its question into technical-spec.md §9
# and does NOT return a question batch in its report: the exact E2 defect
# shape.
# #367: the seat is the plugin's implementer persona (seed-common's copy of
# templates/implementer.md, its frontmatter untouched) with one habit
# changed — open questions go into the document it owns — and a project
# note carrying its #5 draft. A persona that named itself a test double was
# refused as tampering; a draft off the A3 contract (no G/C IDs, no
# `**Test port**` line) drew a legitimate correction that erased §9. The
# draft is on-contract except for the §9 question it exists to carry, and
# a correction never moves §9.
set -eu
bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"
python3 - .claude/agents/implementer.md <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
OLD = ("- Never wait on an open question mid-job and never silently assume: collect\n"
       "  open questions and return them as an explicit list with your deliverable\n")
NEW = ("- Never wait on an open question mid-job and never silently assume: write\n"
       "  each open question into the document you own, `technical-spec.md`'s\n"
       "  `## §9 Open questions`, where the team reads it. Your report is one\n"
       "  line: the files you wrote\n")
STACK = re.compile(r"<!-- /roz-gate:init fills this section.*?-->\n", re.S)
FILLED = ("- Python 3, standard library only; no ORM, no datastore beyond the\n"
          "  module-level tables (`src/store/offers.py` is the offers table)\n"
          "- Pricing lives in `src/checkout/service.py` (`cart_total`); keep it\n"
          "  a pure function of its arguments and the tables\n")
DRAFT = '''
## Project notes

- #5 Offer expiry enforcement: the contract below was drafted with the team
  in the design session. Dispatched on #5, write it to
  `docs/specs/5/technical-spec.md` as drafted. A correction the dispatch
  asks for goes into the clauses or the §5 table; §9 stays as drafted until
  the gate holder answers it.

```
# Technical spec #5

**Test port** — src/checkout/service.py, src/store/offers.py

## Contract
- **G1 (R1, S1)** — `cart_total(items, now)` charges an item its full
  `cost` once its offer's `expires_at <= now`: the discount is not applied.
- **G2 (R1, S2)** — while `now < expires_at`, the offer's `discount` applies.
- **C1** — `now` is a timezone-aware `datetime`; `expires_at` is the offers
  table's ISO-8601 UTC string, compared as an instant.
- **C2** — expiry is read on every call: a changed `expires_at` takes effect
  on the next `cart_total` call, with no deploy and no cache to flush.

## §5 Port observability

| scenario | observability |
|---|---|
| S1 | observable via an `OFFERS` row whose `expires_at` is before `now` |
| S2 | observable via an `OFFERS` row whose `expires_at` is after `now` |

## §9 Open questions
- **[implementer] · Qx · clock source**

  Which clock does `now` come from — the DB's or the API caller's?
  - (a) API caller passes it ← ✅ recommended
  - (b) DB `NOW()`

  *why: determines whether expiry is testable with a frozen clock.*
```
'''
assert text.count(OLD) == 1 and len(STACK.findall(text)) == 1, \
    "templates/implementer.md changed: re-cut the E2 persona"
text = STACK.sub(lambda _: FILLED, text).replace(OLD, NEW)
open(path, "w", encoding="utf-8").write(text + DRAFT)
PY
head -4 .claude/agents/implementer.md | grep -q '^description: >$'
grep -q '^## §9 Open questions$' .claude/agents/implementer.md
# Committed, as a project's persona edits are: a dirty persona file in
# `git status` is one more reason to read the seat as tampered with.
git add .claude/agents/implementer.md
git -c user.email=paul@example.com -c user.name=paul commit -qm "implementer: project notes"
