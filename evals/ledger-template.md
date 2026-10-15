# The ledger — every case, one index

The eval ledger's cases live in three places: lint cases as one file each
under `lint/cases/` (`b1.py`, `c19.py`, …), replay cases as
`replay/cases/<ID>/`, and the judgment corpus in `judgment/criteria.json`.
This page indexes all of them — **rendered by `tools/ledger.py`** from the
cases' own metadata (a lint file's `META`, a replay `case.json`'s `tier` and
`ledger_text`, `ledger-deferred.json` for a case with no checker yet) into
`ledger-template.md`, which holds this prose. Never edit it by hand: edit
the case, rerun the tool; `--check` goes red in CI and pre-push while it is
stale (issue #131).

**Provenance.** The original ledger document is not in the repository.
This index was reconstructed on 2026-09-26 from what the repository does
hold:

- **Titles** come from each lint case's `META` and each replay case's
  `case.json`.
- **Ledger text** is quoted verbatim from the checkers' `# source: ledger
  <ID> — "…"` citations. It is the only surviving ledger prose; each entry
  reads as the expected outcome, then (in parentheses) why it matters.
  Lint cases carry no such quote.
- **Family descriptions** were inferred from the titles and confirmed by
  Paul on 2026-09-26; they are this page's, not recovered.

A new case is written in its metadata first — the row is the case's, and
this page renders it. A checker's `source: ledger` quote copies that row,
never the other way round.

## IDs

A letter names the family, the number the order a case was added — a
number is never reused. Rule letters in `hooks/README.md` (rules A–E) are
a separate namespace: hook rule D is unrelated to ledger case D2.

| family | what it guards |
|---|---|
| **A** | patrol sees every channel a human can speak through |
| **B** | the text conventions of agent-written comments — tags and markers |
| **C** | the label state machine and each command's exits |
| **D** | what a dispatched seat receives, and what it must not see |
| **E** | a question reaches the gate holder; an answer lands where it belongs |
| **F** | the loop end to end — whole commands, whole sessions |
| **J** | the judgment tier's own instrument (lint only) |
| **L** | the human-facing pages (lint only) |

## Cases

`lint` = static check on every push · `replay` = headless runs, pass^k ·
`hook` = enforced by a hook, proven in `hooks/tests/`.

### A · patrol sees every channel

| ID | title | tier | ledger text |
|---|---|---|---|
<!-- rows A -->

### B · agent-written text conventions

| ID | title | tier | ledger text |
|---|---|---|---|
<!-- rows B -->

### C · labels and exits

| ID | title | tier | ledger text |
|---|---|---|---|
<!-- rows C -->

### D · what a seat receives, and what it must not see

| ID | title | tier | ledger text |
|---|---|---|---|
<!-- rows D -->

### E · questions and answers reach the right place

| ID | title | tier | ledger text |
|---|---|---|---|
<!-- rows E -->

### F · the loop end to end

| ID | title | tier | ledger text |
|---|---|---|---|
<!-- rows F -->

**Amendment — F6.** The original text measured turns 1, 3, 5 and 10. The
driver (`replay/cases/F6/drive.py`, `MEASURED`) runs a 12-turn session and
measures 1, 3, 5, 8 and 12 — past the published median first omission
around step four — and both eval READMEs report that curve. The ledger
text follows the experiment; the driver's citation was updated to match.

### J, L · lint-only

| ID | title | tier |
|---|---|---|
<!-- rows J L -->

## The judgment corpus

A separate namespace: seven items from the ADMC history where an agent's
question changed the human's design — P1, P2, P8, P12 (should be raised)
and N1, N5, N10 (should not). Their checkable propositions are
`judgment/criteria.json`; see `judgment/README.md`.
