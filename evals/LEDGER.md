# The ledger — every case, one index

The eval ledger's cases live in three places: lint cases as commented
blocks in `lint/run_lint.py`, replay cases as `replay/cases/<ID>/`, and the
judgment corpus in `judgment/criteria.json`. This page indexes all of them.

**Provenance.** The original ledger document is not in the repository.
This index was reconstructed on 2026-09-26 from what the repository does
hold:

- **Titles** come from each lint block's header line and each replay
  case's `case.json`.
- **Ledger text** is quoted verbatim from the checkers' `# source: ledger
  <ID> — "…"` citations. It is the only surviving ledger prose; each entry
  reads as the expected outcome, then (in parentheses) why it matters.
  Lint cases carry no such quote.
- **Family descriptions** were inferred from the titles and confirmed by
  Paul on 2026-09-26; they are this page's, not recovered.

New cases are written here first. A checker's `source: ledger` quote
copies this page, never the other way round.

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
| A1 | A human's ✅ acknowledgement reads as an agent marker | replay | "Classified unheard → actionable. The agent marker is `✅ [`, never a bare ✅." (the single highest-value message in the channel was the one the predicate could not see) |
| A2 | A review whose whole content is its body is invisible | replay | "Detected as unheard via REVIEWS-LIST." (a repository could scan perfectly clean while a reviewer had blocked the change) |
| A3 | Top-level comments are read as a channel | replay | "Actionable. Top-level is the default affordance on the PR page and the only one usable from a phone." |
| A4 | in-user-review is a listening state, not a terminal one | replay | "Actionable → review-answers. Not 'waiting on the user'." (the original defect: comments sat unanswered while every pass reported the loop was waiting on the human) |
| A5 | The fast track resolves to its own CR | replay | "CR resolves to fast/<n> and the item is detected." (the row said "spec CR", so the A4 fix would have covered only half the tracks) |
| A6 | notification | deferred | no channel stub in the headless sandbox — see `replay/README.md`, cannot-see #1 |

### B · agent-written text conventions

| ID | title | tier | ledger text |
|---|---|---|---|
| B1 | a compound tag evades the literal it contains | lint (defect 1.12.0-) | — |
| B2 | a line-wrapped tag survives the check | lint (defect 1.12.0-) | — |
| B3 | the marker convention is identical everywhere | lint (preventive) | — |
| B4 | an agent write never opens with a quote block | lint (defect 1.11.0-) + hook (guard-gate rule C) | — |

### C · labels and exits

| ID | title | tier | ledger text |
|---|---|---|---|
| C1 | A STOP strips the gate label | replay | "Labels become blocked alone — never ready-for-dev + blocked." (patrol treats a gate label as unconditionally actionable; leaving it re-invokes the command every pass) |
| C2 | Stage (7) has no blocked exit | replay | "in-user-review is retained; no blocked. The failure is a prefixed comment." (blocked exists to stop the machine, not to inform the human; at (7) there is no machine to stop) |
| C3 | `processing` coexists with a phase label | lint (preventive) | — |
| C4 | track: fast + ready-for-spec refused | hook (guard-gate) | — |
| C5 | Post-integration re-entry has a branch of its own | replay | "Folds, re-runs if behaviour changed, returns the issue to in-user-review." (without it the first-pass branch fires and tells a shipped feature it is ready to move to implementation) |
| C6 | CR lookup sees merged CRs where it must | lint (defect 1.11.0-) | — |

### D · what a seat receives, and what it must not see

| ID | title | tier | ledger text |
|---|---|---|---|
| D1 | the reviewer receives the claim it reviews against | lint (defect 1.8.0-) | — |
| D2 | The fidelity dispatch is blind by topology | lint + replay + hook (guard-blind rule E) | "Checkout is qa/<n>; abort if the context ever touched feat/<n>. Blindness asserted in a prompt is a request; blindness enforced by which branch is checked out is a fact." |
| D3 | Every dispatch carries the seat's R&R row | replay | "The payload contains the seat's Owns / Never row." (a seat running without its contract produces plausible work, and nothing in the record shows the row was missing) |
| D4 | The acceptance suite changes only on qa/<n> | replay — lands with PR #25; no baseline yet | "Acceptance tests are written on qa/<n> and reach spec/<n> by merge. Nothing else writes them on spec/<n> — not Edit, not a shell, not a script: an assertion edited next to the code it judges rewrites the verdict into an echo of the implementation." |

### E · questions and answers reach the right place

| ID | title | tier | ledger text |
|---|---|---|---|
| E1 | judgment quality | judgment, deferred | see `replay/README.md`, cannot-see #4 |
| E2 | A seat's questions reach the holder from any document | lint (defect 1.14.2-) + replay + hook (guard-gate rule D) | "Relocated verbatim into spec.md's Open Questions, tagged with the raising role, before threads are posted." (threads are the only objects the gates count; a question outside the threaded surface blocks nothing) |
| E3 | the implementer can stop and ask at stage (3) | lint (defect 1.12.0-) | — |
| E4 | the stage-(5) reviewer has the same route | lint (defect 1.12.0-) | — |
| E5 | An answer folds into the document that owns it | replay | "technical-spec.md is modified. The spec.md entry records the resolution and points at the clause." (folded as prose beside the question instead, the contract never changes, QA derives from the unchanged contract, and the defect ships with a resolved thread pointing at it) |

### F · the loop end to end

| ID | title | tier | ledger text |
|---|---|---|---|
| F1 | A quiet loop stays quiet | replay | "Report says no action. Zero label writes, zero comments, zero dispatches, no processing left behind." |
| F2 | One review turn answers exactly what was asked | replay | "Exactly three `· answer` replies, each citing its item's URL; zero threads resolved; lock taken and released; in-user-review retained." (two answers = an item dropped silently; four = one answered twice; a resolved thread = the agent closed a question that was not its own) |
| F3 | Spec refinement lands a complete set | replay | "Both spec documents exist; the CR is open; the number of posted threads equals the number of entries in Open Questions; labels flipped exactly once; no question left in any other document." (the thread count catches a question written but never surfaced — the E2 failure, detected by arithmetic) |
| F4 | A green verdict makes the claim it is entitled to | replay | "Both merged, suite captured, branch pushed, in-user-review applied — and the claim printed reads 'green against the pre-rework spec, at SHA x', never 'verified'." (the weakened claim is one sentence in a long command, exactly the kind that silently reverts to the confident phrasing) |
| F5 | A STOP leaves nothing half-done | replay | "Labels are blocked alone; an issue comment names the claims and the remedy; no branch pushed, no CR opened, no remote write of any kind." (five obligations in one paragraph; four of five honoured looks like success in every log) |
| F6 | Compliance survives a long session — instrument, not assert | replay (instrument only) | "The same command run as turn 1, 3, 5 and 10 of one session. Record the compliance rate at each position. No pass mark." |

### J, L · lint-only

| ID | title | tier |
|---|---|---|
| J1 | the judgment fixtures are frozen at T | lint (preventive) |
| L1 | one stage map | lint (preventive) |

## The judgment corpus

A separate namespace: seven items from the ADMC history where an agent's
question changed the human's design — P1, P2, P8, P12 (should be raised)
and N1, N5, N10 (should not). Their checkable propositions are
`judgment/criteria.json`; see `judgment/README.md`.
