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
| A7 | A merged CR closes the issue out | replay | "Issue closed; every `track:`/`status:` label gone; exactly one shipped comment naming the CR; exactly one close; nothing written to the CR — and an issue the forge already closed on merge loses its labels and gets its comment, with no second close." (an OPEN CR at in-user-review is F1/A4/A5's fixture — zero label writes there) (GitLab and any CR against a release branch leave the issue open wearing `in-user-review` after the merge — the loop's last step never happened — issue #41) |
| A8 | The scan is one read-only sub-agent and the rules exist once | lint (defect 1.24.0-) | — |
| A6 | notification | deferred | no channel stub in the headless sandbox — see `replay/README.md`, cannot-see #1 |

### B · agent-written text conventions

| ID | title | tier | ledger text |
|---|---|---|---|
| B1 | a compound tag evades the literal it contains | lint (defect 1.12.0-) | — |
| B2 | a line-wrapped tag survives the check | lint (defect 1.12.0-) | — |
| B3 | the marker convention is identical everywhere | lint (preventive) | — |
| B4 | an agent write never opens with a quote block | lint (defect 1.11.0-) + hook (guard-gate rule C) | — |
| B5 | the must-read stays on top and within budget | lint (defect 1.19.0-) | — |

### C · labels and exits

| ID | title | tier | ledger text |
|---|---|---|---|
| C1 | A STOP strips the gate label | replay | "Labels become blocked alone — never ready-for-dev + blocked." (patrol treats a gate label as unconditionally actionable; leaving it re-invokes the command every pass) |
| C2 | Stage (7) has no blocked exit | replay | "in-user-review is retained; no blocked. The failure is a prefixed comment." (blocked exists to stop the machine, not to inform the human; at (7) there is no machine to stop) |
| C3 | `processing` coexists with a phase label | lint (preventive) | — |
| C4 | track: fast + ready-for-spec refused | hook (guard-gate) | — |
| C5 | Post-integration re-entry has a branch of its own | replay | "Folds, re-runs if behaviour changed, returns the issue to in-user-review." (without it the first-pass branch fires and tells a shipped feature it is ready to move to implementation) |
| C6 | CR lookup sees merged CRs where it must | lint (defect 1.11.0-) | — |
| C8 | A merged CR closes the issue out — the prose side | lint (defect 1.19.0-) | — |
| C9 | A command's git work lives in a worktree it removes on every exit | lint (defect 1.19.0-) + hook (rule E worktree forms) | — |
| C10 | Re-entering the spec stage after a closed CR is the human's door | lint + replay | "Labels are blocked alone; the comment carries `git push origin --delete spec/<n>` and cites the closed CR; no CR created; the remote's refs unchanged — never force-pushed, never deleted by the agent." (a second `ready-for-spec` on a branch that still exists used to fail the cut with a git error, and the only automatic fixes — force-push, delete — would give agents a destructive remote write — issue #62) |
| C7 | A branch is cut only from a base the remote has | lint + replay | "Labels are blocked alone; the STOP comment names the missing base; no branch pushed, no CR opened." (a mistyped or retired `default_branch` used to cut an empty branch from nothing and open a CR against it — issue #38) |

### D · what a seat receives, and what it must not see

| ID | title | tier | ledger text |
|---|---|---|---|
| D1 | the reviewer receives the claim it reviews against | lint (defect 1.8.0-) | — |
| D2 | The fidelity dispatch is blind by topology | lint + replay + hook (guard-blind rule E) | "Checkout is qa/<n>; abort if the context ever touched feat/<n>. Blindness asserted in a prompt is a request; blindness enforced by which branch is checked out is a fact." |
| D3 | Every dispatch carries the seat's R&R row | replay | "The payload contains the seat's Owns / Never row." (a seat running without its contract produces plausible work, and nothing in the record shows the row was missing) |
| D4 | The acceptance suite changes only on qa/<n> | replay (no baseline yet) | "Acceptance tests are written on qa/<n> and reach spec/<n> by merge. Nothing else writes them on spec/<n> — not Edit, not a shell, not a script: an assertion edited next to the code it judges rewrites the verdict into an echo of the implementation." |

### E · questions and answers reach the right place

| ID | title | tier | ledger text |
|---|---|---|---|
| E1 | judgment quality | judgment, deferred | see `replay/README.md`, cannot-see #4 |
| E2 | A seat's questions reach the holder from any document | lint (defect 1.14.2-) + replay + hook (guard-gate rule D) | "Relocated verbatim into spec.md's Open Questions, tagged with the raising role, before threads are posted." (threads are the only objects the gates count; a question outside the threaded surface blocks nothing) |
| E3 | the implementer can stop and ask at stage (3) | lint (defect 1.12.0-) | — |
| E4 | the stage-(5) reviewer has the same route | lint (defect 1.12.0-) | — |
| E6 | A thread the human opens is an amendment, folded like an answer | replay | "`spec.md` on the remote carries the amendment; a `✅ [<role>] amended` reply; the thread resolved." (a human-opened thread has one comment and no `[role]` tag, so the answered-thread rule skipped it while patrol classified it actionable — every pass reported "no new answers" — issue #62) |
| E5 | An answer folds into the document that owns it | replay | "technical-spec.md is modified. The spec.md entry records the resolution and points at the clause." (folded as prose beside the question instead, the contract never changes, QA derives from the unchanged contract, and the defect ships with a resolved thread pointing at it) |

### F · the loop end to end

| ID | title | tier | ledger text |
|---|---|---|---|
| F1 | A quiet loop stays quiet | replay | "Report says no action. Zero label writes, zero comments, one dispatch — the scanner — and no other, no processing left behind." (amended for #59: the scan is a read-only sub-agent) |
| F2 | One review turn answers exactly what was asked | replay | "Exactly three `· answer` replies, each citing its item's URL; zero threads resolved; lock taken and released; in-user-review retained." (two answers = an item dropped silently; four = one answered twice; a resolved thread = the agent closed a question that was not its own) |
| F3 | Spec refinement lands a complete set | replay | "Both spec documents exist; the CR is open; the number of posted threads equals the number of entries in Open Questions; labels flipped exactly once; no question left in any other document." (the thread count catches a question written but never surfaced — the E2 failure, detected by arithmetic) |
| F4 | A green verdict makes the claim it is entitled to | replay | "Both merged, suite captured, branch pushed, in-user-review applied — and the claim printed reads 'green against the pre-rework spec, at SHA x', never 'verified'." (the weakened claim is one sentence in a long command, exactly the kind that silently reverts to the confident phrasing) |
| F5 | A STOP leaves nothing half-done | replay | "Labels are blocked alone; an issue comment names the claims and the remedy; no branch pushed, no CR opened, no remote write of any kind." (five obligations in one paragraph; four of five honoured looks like success in every log) |
| F8 | A command leaves the user's checkout as it found it | replay | "HEAD is still main, the uncommitted edit and the untracked file are intact, no linked worktree is left behind, and spec/<n> reached the remote." (every earlier seed ran in a clean clone, where a checkout in the user's tree is invisible — issue #37) |
| F9 | A pass acts from the scanner's table | replay | "The scanner's table has a row per issue with the right verdict; the pass acts on the top actionable row, locks no other loop issue, posts every intake batch; the scanner writes nothing; the main agent lists nothing after the table." (the scan used to live in the main agent's context — #59) |
| F7 | A branch is cut from the configured base, not the trunk | replay | "`spec/<n>` descends from `origin/<default_branch>` and the CR targets it — with `default_branch` naming a release branch while `main` and an older release branch also exist." (the only base ever exercised was `main`; a loop that always cut from the trunk measured 100% — issue #38) |
| F6 | Compliance survives a long session — instrument, not assert | replay (instrument only) | "The same command run as turn 1, 3, 5, 8 and 12 of one session. Record the compliance rate at each position. No pass mark." (amended — see below) |

**Amendment — F6.** The original text measured turns 1, 3, 5 and 10. The
driver (`replay/cases/F6/drive.py`, `MEASURED`) runs a 12-turn session and
measures 1, 3, 5, 8 and 12 — past the published median first omission
around step four — and both eval READMEs report that curve. The ledger
text follows the experiment; the driver's citation was updated to match.

### J, L · lint-only

| ID | title | tier |
|---|---|---|
| J1 | the judgment fixtures are frozen at T | lint (preventive) |
| L1 | one stage map | lint (preventive) |
| L2 | the local keys `roz-config` accepts are the ones the commands read and README documents | lint (defect 1.18.0) |

## The judgment corpus

A separate namespace: seven items from the ADMC history where an agent's
question changed the human's design — P1, P2, P8, P12 (should be raised)
and N1, N5, N10 (should not). Their checkable propositions are
`judgment/criteria.json`; see `judgment/README.md`.
