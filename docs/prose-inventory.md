# Executable-prose inventory

Maintainer-facing (#260); no agent reads this page. It answers one question
for every rule the loop's prose carries: **why does this still need a model
— or a human — and if it doesn't, what replaces it?** The layers are
#239's (`references/roz-state.md` is the observation boundary); this page
adds no state model and no action resolver. `evals/lint/cases/l13.py` keeps
it honest.

## The rules of this page

**Scope.** A rule is listed iff a ledger case (`evals/LEDGER.md`) or a hook
rule (`hooks/README.md`) guards it. Every ledger ID appears at least once
in the tables below — a mechanical row, a kept row, the end-to-end table or
*Not classified* with its reason; every hook rule A–K owns at least one row. Prose no case guards is listed under *Unguarded
executable prose* — unclassified, not unimportant.

**Classes.** `OBSERVATION` — a fact read from the forge or git; owner a
collector (`roz-branch`, `roz-state`). `MECHANICAL POLICY` — a decision
computable from observations; owner `roz-check`, a hook, or existing code.
`SEMANTIC JUDGMENT` — needs a reader of meaning; stays in prose.
`AUTHORITY` — the human's call; stays the human's. A rule that mixes two
classes is two rows (`C22 (obs)` / `C22 (policy)`): `roz-state` reports
the inputs, `roz-check` interprets them — never a derived boolean in the
observation layer (#239 ruling 2).

**Owner** is one of `roz-branch` (#135) · `roz-state` (#133) · `roz-check`
(#134) · `hook <rule>` · `code <path>` · `none yet — <why>`. The
mechanical-policy rows owned by `roz-check` are #134's backlog; the
observation rows owned by `roz-state` are #133's.

**Readiness.** A mechanical row is **ready** only when every field below is
filled; a `—` in any of them makes it `not_ready`, and that empty field is
the blocker.

| field | content |
|---|---|
| `inputs` | named forge ops / git commands / tools — not a description |
| `on_unknown` | required for `OBSERVATION`: what happens when the read fails |
| `oracle` | named cases — lint, replay, hook test |
| `shadow` | a named signal, or `not required: <why>` |

**Status** — one of six, in this order:

| status | meaning |
|---|---|
| `identified` | classified; readiness not yet assessed |
| `not_ready` | a required field is `—`; that field is the blocker |
| `ready` | every required field is filled |
| `shadow` | a deterministic replacement runs beside the prose and is compared |
| `authoritative` | the deterministic path is the source of truth |
| `migrated <sha>` | the redundant prose is deleted; the row stays, with the commit |

Normal path: `identified → ready → shadow → authoritative → migrated`;
`not_ready` is the explicit blocked state. A hook rule is `authoritative`
from the day it lands — its prose stays as guidance so the model is not
denied, not as the rule. `SEMANTIC JUDGMENT` / `AUTHORITY` rows have no
status.

**Anchor.** Each row quotes one literal from its `source`; the lint fails
when the literal is gone and the row is not `migrated`. When prose is
rewritten, update the anchor in the same commit.

## Semantic invariants and operational constraints

Inside one kept or mechanical rule, two contracts can hide in one paragraph
(#261):

- a **semantic invariant** — what the agent must understand or preserve
  ("test the contract, not the implementation"); it needs a reader, so it
  stays prose;
- an **operational constraint** — what the agent may or may not do while
  doing it (which paths, refs, threads); it is the part a hook can enforce.

Where a load-bearing rule carries both, write them apart as run-in
paragraphs, in this order: **Invariant.** — the semantic requirement;
**Allowed.** — what is permitted where a reader could doubt it;
**Forbidden.** — the boundary; **Exception.** — only when a real one
exists. Then, if a hook enforces the boundary, one sentence naming it. Not
every rule needs every clause, and one sentence that is already one
contract needs none. A split restructures; it never adds, removes or
broadens an allowed or forbidden action — a change of meaning is its own
issue.

Applied so far: `references/qa-brief.md` § Inputs (the blindness rule;
lint D20 pins the structure, never the wording; replay D10–D19 under
`--variant A0` vs A measure the split alone).

### One executable rule answers one decision question

A second axis (#262): **decision density**, not word count. A rule
written as one sentence can still ask for several decisions — and a model
can get one right and another wrong, which a replay then cannot attribute.
The review test:

> **A rule holds two decisions when one clause can be obeyed while another
> is violated, and the two violations are different failures.**

Not a second decision: actions that succeed or fail together (classify a
red, then act on its class), or a list of boundaries under one
**Forbidden.** — an `and` is not a defect by itself. Where the decisions
run in order, write them as a numbered list, one decision per item, with a
bold lead; the words stay, the outcomes stay (the split criterion above).
Lint may pin the structure once it is settled; it is never behavioural
proof — replay is.

Applied so far: `references/qa-brief.md` step zero — the questioned →
drivable → undrivable → wait chain, the paragraph whose first half Haiku
obeyed and whose second it violated in #199 (lint E13; replay D18/D19,
D10/D11 under `--variant A1` vs `A2`).

## Kernel

A **kernel rule** is a semantic invariant that several executable files
need, defined in exactly one of them (#263). The **owner** defines it: the
predicate, the consequence and the scope, under a bold ID label (`**QA-4**`)
that appears once. Every other file is a **consumer** and applies it: its
local trigger, what this procedure does next, and the pointer `(QA-4`. A
consumer never restates the predicate, the rationale or the exceptions in
its own words. The ID is provenance for maintainers, not an import, so a
consumer's text stays executable without looking the ID up.

**Entry.** A rule enters the kernel only when all of these hold:

- its semantics are stable;
- its semantic half is already separated from any operational constraint
  (the operational half belongs to a hook or code, never here);
- it answers one decision question, or it is a clearly bounded invariant;
- behavioural evidence exists (named replay cases);
- it has at least two real consumers.

**Change rule.** A change to a kernel rule's definition names, in its PR
body, every case in its row. Re-running them is the maintainer's spend call.
A consumer-only edit keeps its pointer.

L14 checks the tables below: the owner carries its label once and its
definition anchor, every consumer carries its pointer and its anchor, no
consumer-side file carries a retired definition, and every case is a ledger
ID.

| id | owner | definition anchor | cases |
|---|---|---|---|
| QA-4 | references/qa-brief.md | a red is never resolved by editing an assertion to match observed behaviour | B8, D4, D9, D13, D19, E12, L14 |

### QA-4 consumers

| consumer | anchor |
|---|---|
| agents/qa.md | never an edited assertion (QA-4, the QA brief) |
| references/workflow.md | (QA-4: never an edited assertion) |
| references/workflow.md | never an assertion edit (QA-4, `references/qa-brief.md` § Run the suite) |
| references/workflow.md | observed (QA-4, audited at (5q)) |
| commands/next-stage.md | edited assertion (QA-4; the fidelity audit checks it) |
| commands/integrate.md | **Apply QA-4 to an integration RED** |
| commands/spec-answers.md | never an assertion edited to match (QA-4) |

### QA-4 retired wording

Definitions and rationale the consumers used to carry. None of them may
come back in `agents/`, `commands/`, `references/` or `templates/`.

| retired literal |
|---|
| is integrate's rule |
| binds you first |
| rewrites the verdict into an echo of the implementation |
| An integration RED is never resolved by editing a QA assertion |
| the expected value comes from the requirement, never from a run of the code |
| exactly two dispositions: a **harness issue** QA fixes |

## Mechanical rules

| id | source | anchor | question | class | owner | dependency | inputs | on_unknown | oracle | shadow | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L4 | references/patrol-scan.md | bin/roz-branch match | Which branch is each issue's spec / feat / qa / fast branch — in the scanner? | OBSERVATION | roz-branch | #135 | `roz-branch snapshot` (one `git ls-remote --heads`, and the merged CRs' head names — #272), `match` | an unreadable remote → the pass STOPs before dispatch; one branch `UNKNOWN` (no live head, the merged history unread) → `waiting on: branches unknown` | C31, F9, L4, A11, test_branch_names | not required: the scanner never ran git; it switched outright (#135 ruling 3) | authoritative |
| C31, C10 | references/branch-names.md | ## The resolver | Which branch is each issue's spec / feat / qa / fast branch — in the commands? | OBSERVATION | roz-branch | #135 | `roz-branch lookup` (one `git ls-remote --heads`) | `UNKNOWN` → STOP, cut nothing | C31, C10, C11, C12, C20, test_branch_names | `shadow_branch_mismatch` (C10, C11, C12, C20, F9) | shadow |
| A5 | references/patrol-scan.md | `<feat-branch>` / `<qa-branch>` / `<fast-branch>` below from its JSON | Which CR belongs to a fast issue? | OBSERVATION | roz-branch | #135 | `roz-branch match` → `<fast-branch>`, then CR-FIND | `UNKNOWN` → the pass STOPs | A5, C31 | not required: bound by the scanner's switch (row L4) | authoritative |
| C7 | commands/next-stage.md | CR-OPEN from `<spec-branch>` targeting `<default_branch>` | Does the remote have the base the branch is cut from? | OBSERVATION | roz-branch | #135 | `roz-branch snapshot` heads | `UNKNOWN` → STOP | C7, F7 | — | not_ready |
| A1 | references/patrol-scan.md | Any unresolved thread whose last comment is a human answer | Is a thread's last comment a human's, or an agent marker (`✅ [`)? | OBSERVATION | roz-state | #133 | THREADS-LIST | — | A1 | — | not_ready |
| A2 | references/patrol-scan.md | REVIEWS-LIST | Does a CR carry an unheard review whose whole content is its body? | OBSERVATION | roz-state | #133 | REVIEWS-LIST | — | A2 | — | not_ready |
| A3 | references/patrol-scan.md | CR-COMMENTS-LIST | Is there an unheard top-level CR comment? | OBSERVATION | roz-state | #133 | CR-COMMENTS-LIST | — | A3, E8 | — | not_ready |
| A7, A11 | commands/patrol.md | ISSUE-COMMENT one line: `**[patrol] · shipped** | Is the issue's CR merged (a close-out candidate)? | OBSERVATION | roz-state | #133 | CR-FIND (all-states), ISSUE-LIST-CLOSED | — | A7 | — | not_ready |
| C6, C13 | references/patrol-scan.md | all-states form | Is a CR open, merged, or closed unmerged — merged CRs included? | OBSERVATION | roz-state | #133 | CR-FIND (all-states) | the fact is `unknown` with a reason — never `0`, `[]` or absent (`references/roz-state.md` § The unknown invariant); what a consumer then does is #134's | C6, C13; `hooks/tests/test_roz_state.py`; the seed sweep (`redproof.py` § state) | `shadow_state_mismatch` | shadow |
| C22 (obs) | references/workflow.md | **Review-clean** means exactly three things, defined here and read everywhere else | What are the implementation CR's code-review marker, its `reviewed-sha`, the branch head, and its open-thread count? | OBSERVATION | roz-state | #133 | CR-COMMENTS-LIST, THREADS-LIST, `roz-branch` snapshot `sha` | the fact is `unknown` with a reason — never `0`, `[]` or absent (`references/roz-state.md` § The unknown invariant); what a consumer then does is #134's | C22, C23; `hooks/tests/test_roz_state.py`; the seed sweep (`redproof.py` § state) | `shadow_state_mismatch` | shadow |
| C16 (obs) | references/fidelity-brief.md | That comment is the record that the audit ran | Is a `**[reviewer] · fidelity**` record on the QA CR, and what head did it audit? | OBSERVATION | roz-state | #133 | CR-COMMENTS-LIST, THREADS-LIST, `roz-branch` snapshot `sha` | the fact is `unknown` with a reason — never `0`, `[]` or absent (`references/roz-state.md` § The unknown invariant); what a consumer then does is #134's | C16, C17; `hooks/tests/test_roz_state.py`; the seed sweep (`redproof.py` § state) | `shadow_state_mismatch` | shadow |
| C24 (obs) | references/patrol-scan.md | illegal state: gate label applied by | Who applied each gate label the issue wears (its latest `labeled` event)? | OBSERVATION | roz-state | #133 | ISSUE-LABEL-EVENTS | — | C24, F13 | — | not_ready |
| F15 | references/forge-github.md | is a **failed read**, never "no blockers" | Is an issue blocked by an open forge-native blocker? | OBSERVATION | roz-state | #133 (collector first used by #205) | ISSUE-BLOCKERS | a failed read → the fact is `unknown` (`forge_query_failed`); today's prose answer is `waiting on: blockers unknown` | F15; `hooks/tests/test_roz_state.py`; the seed sweep (`redproof.py` § state) | `shadow_state_mismatch` | shadow |
| L2 | templates/claude-workflow.md | - specs_dir: | What are the block's keys and the clone's local keys? | OBSERVATION | code bin/roz-config | — | `bin/roz-config --json` | absent key → its documented default | L2, test_roz_config | not required: already code | authoritative |
| L5 | commands/uninit.md | **CLAUDE.md** — or **CLAUDE.local.md**, whichever carries it | Where does the config block live? | OBSERVATION | code hooks/config_block.py | — | `find_block` (CLAUDE.md, then CLAUDE.local.md; toplevel, then main checkout) | none found → the command stops: run `/roz-gate:init` | L5 | not required: already code | authoritative |
| C22 (policy) | commands/tip.md | review-clean is that record current **and** zero open threads | Is the implementation review-clean (`reviewed-sha` == head, marker present, zero open threads)? | MECHANICAL POLICY | roz-check | #134 ← row C22 (obs) | row C22 (obs) — a `roz-state` snapshot | the rule is `unknown` and the verdict never `eligible` — `may_start` false, no lock (`references/roz-check.md`) | C22, C23; `hooks/tests/test_roz_check.py`; the declared seeds (`redproof.py` § check) | `shadow_check_mismatch` (integrate's entry: C12, C16, D4, F4) | shadow |
| C16 (policy) | references/fidelity-brief.md | That comment is the record that the audit ran | May the QA CR integrate (a fidelity record on its current head, zero open fidelity threads)? | MECHANICAL POLICY | roz-check | #134 ← row C16 (obs) | row C16 (obs) — a `roz-state` snapshot | the rule is `unknown` and the verdict never `eligible` — `may_start` false, no lock (`references/roz-check.md`) | C16, C17; `hooks/tests/test_roz_check.py`; the declared seeds (`redproof.py` § check) | `shadow_check_mismatch` (C12, C16, D4, F4) | shadow |
| C24 (policy), F13 | references/patrol-scan.md | illegal state: gate label applied by | Is a gate label applied by a bot an illegal state? | MECHANICAL POLICY | roz-check | #134 ← row C24 (obs) | row C24 (obs), the block's `bot_login` | — | C24, F13 | — | identified |
| C27, F14 | references/patrol-scan.md | - **A gate label on a stage that passed.** For a `track: spec` issue | Is `ready-for-dev` on a stage that already passed an illegal state? | MECHANICAL POLICY | roz-check | #134 ← rows C6 / L4 | the label, CR-FIND of `<feat-branch>` (all-states) | — | C27, F14 | — | identified |
| C3 | references/workflow.md | label besides the `processing` lock | Does `processing` coexist with exactly one phase label? | MECHANICAL POLICY | roz-check | #134 | the issue's labels | — | C3 | — | identified |
| C10 | references/branch-names.md | **1 + max(`{seq}`)** | May a re-entry after a closed CR proceed, or is it the human's door (no `{seq}` → STOP)? | MECHANICAL POLICY | roz-check | #134 ← row C31 | `roz-branch lookup`, CR-FIND (all-states) | — | C10 | — | identified |
| C11 | references/branch-names.md | **1 + max(`{seq}`)** | Which `{seq}` does a re-entry cut, and does it collide? | MECHANICAL POLICY | roz-check | #134 ← row C31 | `roz-branch lookup` matches (`seq`), the snapshot | lookup `UNKNOWN` → STOP | C11, C31 | `shadow_branch_mismatch` (C11) | ready |
| C12 | commands/integrate.md | already merged in. | Are the feat and QA CRs merged, and is the spec branch's tip the one validated? | MECHANICAL POLICY | roz-check | #134 ← rows C6 / L4 | CR-FIND (all-states), `git merge-base --is-ancestor` | — | C12, F4 | — | not_ready |
| C20 | commands/next-stage.md | ## Path B — implementation + review (3)+(5) | Has the implementation landed on the spec branch before (4) launches? | MECHANICAL POLICY | roz-check | #134 ← rows C22 / C6 | CR-FIND, `roz-branch` snapshot | — | C20 | — | identified |
| C14 | commands/init.md | - `fix_rounds` — optional: the fix-and-rerun budget on a red suite at (6) | Has the fix-and-rerun budget run out? | MECHANICAL POLICY | roz-check | #134 | `fix_rounds`, the rounds already spent (no observable count today) | — | C14 | — | not_ready |
| C17, C23 | references/patrol-scan.md | actionable: fidelity-audit | Is the audit / review that never ran the actionable step? | MECHANICAL POLICY | roz-check | #134 ← rows C16 / C22 (policy) | rows C16 / C22 (policy) | — | C17, C23 | — | identified |
| A4 | references/patrol-scan.md | Any unresolved thread whose last comment is a human answer | Is an `in-user-review` issue with an unheard human item actionable? | MECHANICAL POLICY | roz-check | #134 ← rows A1–A3 | rows A1, A2, A3 | — | A4, F1 | — | identified |
| E11 | commands/spec-answers.md | **A fold may ask once** (#206) | Is this question second-order (raised by a fold's answer), so deferred? | MECHANICAL POLICY | roz-check | #134 | the thread's marker lineage (CR comments) | — | E11 | — | identified |
| A10 | references/intake-brief.md | **[intake] · reply** | May an intake summary be written now? | MECHANICAL POLICY | hook A | — | the holder's latest comment | no holder comment → denied | A10, RuleA | not required: the hook is the source of truth | authoritative |
| C4 | references/workflow.md | **The gate label is the confirmation** | May an agent apply a gate label? | MECHANICAL POLICY | hook B | — | the Bash call | — | C4, RuleB | not required: the hook is the source of truth | authoritative |
| B4 | commands/next-stage.md | MUST start with `**[ | Does an agent write open with its tag, never a quote block? | MECHANICAL POLICY | hook C | — | the comment body in the Bash call | — | B4, RuleC | not required: the hook is the source of truth | authoritative |
| E2 | commands/next-stage.md | delete it from the source document | Do open questions live only in `spec.md` when a commit is made? | MECHANICAL POLICY | hook D | — | the staged spec documents | — | E2, RuleD | not required: the hook is the source of truth | authoritative |
| D2, D5, D7, D8 | commands/next-stage.md | roz-gate/fidelity-dispatch | May a call under a blind dispatch read this path or ref? | MECHANICAL POLICY | hook E | — | the marker (`seat=`, `feat=`, `read=`), the tool call | no marker → not blind | D2, D5, D7, D8, RuleE | not required: the hook is the source of truth | authoritative |
| E7 | commands/next-stage.md | The options as **(a)/(b) bullets** | Does a question carry its options as bullets? | MECHANICAL POLICY | hook F | — | the comment body | — | E7, RuleF | not required: the hook is the source of truth | authoritative |
| C18 | references/workflow.md | it opens with the title `**[<command>] · blocked**` | Does a STOP comment name its resume move? | MECHANICAL POLICY | hook G | — | the comment body | — | C18, RuleG | not required: the hook is the source of truth | authoritative |
| E10 | commands/next-stage.md | Guard-gate rule H denies a CR-OPEN whose diff touches `<specs_dir>/*/technical-spec.md` | Does a CR that changed the contract declare its deviations? | MECHANICAL POLICY | hook H | — | the CR-OPEN call, the diff | — | E10, RuleH | not required: the hook is the source of truth | authoritative |
| A9 | references/intake-brief.md | **[intake] · reply** | Does an intake reply answer the human who spoke? | MECHANICAL POLICY | hook I | — | the comment body, the thread | — | A9, RuleI | not required: the hook is the source of truth | authoritative |
| C25, C9 | commands/next-stage.md | `git worktree remove --force` every worktree this run created | Does the loop's worktree add run alone, and live under `roz-gate/wt/`? | MECHANICAL POLICY | hook J | — | the Bash call | — | C25, C9, RuleJ | not required: the hook is the source of truth | authoritative |
| C28 | references/workflow.md | A missing dependency in the base is a STOP, never an option | May the loop merge this ref into an issue branch? | MECHANICAL POLICY | hook K | — | the Bash call, the worktree's branch, `default_branch` | base unresolved → `main` (roz-config's rule) | C28, RuleK | not required: the hook is the source of truth | authoritative |
| D4 | references/workflow.md | - **(4)** `qa` on `qa/{n}`, cut off `spec/{n}` **after the merge** | May this acceptance file be edited on this branch? | MECHANICAL POLICY | hook acceptance | — | the edited path, HEAD | — | D4, test_guard_acceptance | not required: the hook is the source of truth | authoritative |
| B1, B2, B6, B9 | commands/next-stage.md | **`unverified` is a reserved word** in every spec document: it appears only as this tag | Does a spec document use a reserved word only as its tag? | MECHANICAL POLICY | none yet — a commit-time check on the spec documents (rule D's shape) could own it | — | the staged spec documents, `references/reserved-words.json` | — | B1, B2, B6, B9 | — | identified |
| B5 | references/intake-brief.md | <details><summary>Supplement — context and decision trail</summary> | Is the must-read on top and within its line budget? | MECHANICAL POLICY | none yet — a write-time form check (rule C's detector) could own it | — | the comment body | — | B5 | — | identified |
| B7, C26, C30 | commands/patrol.md | one row per issue the scanner listed | Is the pass report the fixed table, with each unreached row queued? | MECHANICAL POLICY | none yet — the report is the session's final text; no tool call carries it, so no hook sees it | — | — | — | B7, C26, C30, F11 | — | not_ready |
| C26 | commands/patrol.md | patrol_issues_per_pass | Which N actionable issues does this pass act on? | MECHANICAL POLICY | none yet — selection is not eligibility (#134), and #260 excludes an action resolver | — | the scan table, `patrol_issues_per_pass` | — | C26 | — | identified |
| C1, C2 | references/workflow.md | status labels with `blocked` alone | On a STOP, are the status labels `blocked` alone — and never at (7)? | MECHANICAL POLICY | none yet — a label write is one tool call; a hook could deny `blocked` beside a gate label | — | the label-write call, the issue's labels | — | C1, C2, F5 | — | identified |
| C8 | commands/next-stage.md | Stage (2) spec refinement for #<n>. For review. Closes #<n>" | Does the CR body close its issue? | MECHANICAL POLICY | none yet — the CR-OPEN call (rule H's detector) could check the body | — | the CR-OPEN call | — | C8 | — | identified |
| C15 | references/workflow.md | A command's git reference to it is always `origin/<default_branch>` | Does every git site name `origin/<default_branch>`, never the bare branch? | MECHANICAL POLICY | none yet — hook K covers the merge; a diff naming the bare branch has no hook | — | the Bash call | — | C15 | — | identified |
| C19, F12 | commands/tip.md | **Read-only.** This command writes nothing: no label, no comment, no commit, | Does tip write nothing? | MECHANICAL POLICY | none yet — tip sets no marker, so no hook can tell its calls apart | — | the tool calls | — | C19, F12 | — | identified |
| D1, D3, D6 | commands/next-stage.md | attaching the seat's R&R row | Does a dispatch carry its required lines (R&R row, claim, amendment list)? | MECHANICAL POLICY | none yet — the dispatch text is model-composed; a dispatch-time check could own its required lines | — | the dispatch text | — | D1, D3, D6 | — | identified |
| E9 | references/qa-brief.md | ## Step zero — the contract review | Is a QA contract question posted as a `[qa]` thread on the spec CR? | MECHANICAL POLICY | none yet — a write-time form check could own the routing | — | the comment call | — | E9 | — | identified |
| L3 | references/workflow.md | made by the **commit sub-agent** (`references/commit-brief.md`) | Does every commit go through the commit sub-agent? | MECHANICAL POLICY | none yet — the commit sub-agent sets no marker a hook could read | — | the `git commit` call | — | L3 | — | identified |
| L6 | commands/init.md | they run **in a linked worktree** (`git worktree add`, under `.git/roz-gate/wt/<branch>`), never in the checkout | Do `test` / `acceptance_test` run in a linked worktree? | MECHANICAL POLICY | none yet — a hook could read the cwd of the test call | — | the Bash call's cwd | — | L6, F8 | — | identified |

## Kept in prose

Block granularity: each conclusion is "stays", so one row per block, with
the reason.

| id | source | anchor | question | class | why it needs a model or a human |
|---|---|---|---|---|---|
| B8, D9–D19, E12 | references/qa-brief.md | **The port is the only road.** | How does QA write a suite that drives the port and asserts the contract — and is a red a harness defect or a contract mismatch? | SEMANTIC JUDGMENT | reading a contract and deciding what a red means is judgment; the mechanical edge (what QA may read) is hook E |
| C5 | commands/spec-answers.md | **The fold changed no behaviour** | Did the fold change behaviour? | SEMANTIC JUDGMENT | whether an amendment changes behaviour is a reading of the spec |
| C29 | references/workflow.md | A missing dependency in the base is a STOP, never an option | Does the base lack code this issue needs? | SEMANTIC JUDGMENT | only a reader of the spec knows what the issue needs; the forbidden remedy is hook K (row C28) |
| E3, E4 | commands/next-stage.md | Dispatch `implementer` | Should the implementer / reviewer stop and ask the holder? | SEMANTIC JUDGMENT | when a question is worth the holder's time is judgment; how it reaches them is hook F |
| E5, E6, E8 | commands/spec-answers.md | folded into <document> | Which document owns this answer or amendment, and how does it read once folded? | SEMANTIC JUDGMENT | folding prose into the document that owns it is writing |
| F2 | commands/review-answers.md | **[review] · answer** | What does the human's review comment ask, and what answers it? | SEMANTIC JUDGMENT | answering a human is the model's job |
| — | references/workflow.md | **The gate label is the confirmation** | Ship it, change it, or send it back? | AUTHORITY | the gate holder's call; the loop's part is to never apply a gate label (hook B) |

## End-to-end cases

An F case proves a whole pass; its rules are the rows it exercises. F15 is
a single rule and has its own row above.

| case | the rows it exercises |
|---|---|
| F1 | A4, A1–A3 |
| F2 | kept: F2 |
| F3 | E2, E7 |
| F4 | C12 |
| F5 | C1, C2, C18 |
| F6 | all — an instrument, no pass mark |
| F7 | C7, C31 |
| F8 | L6, C25 |
| F9 | L4, C26 |
| F10 | C31, L4 |
| F11 | B7 |
| F12 | C19 |
| F13 | C24 |
| F14 | C27 |

## Not classified

| id | why it is not classified |
|---|---|
| A6, E1 | deferred cases — no prose rule to classify |
| A8, B3, D20, E13, E14 | rules about the prose itself (one scan sub-agent; one marker convention; the blindness rule's clause structure; step zero's decision chain; the QA persona carries no procedure that contradicts the brief) — checked statically, never answered at runtime |
| J1 | the judgment tier's own instrument |
| L1, L7, L9, L10, L11, L12 | human-facing pages, not executable prose |
| L8 | the `/roz-gate:config` mod's implementation, not a question the loop answers |
| L13, L14 | this page's own lints (the inventory; § Kernel) |
| L15 | the `roz-state` contract's own lint — `references/roz-state.md` and `hooks/state_contract.py` carry one field table (#239) |
| L16 | `roz-check`'s own lint — `references/roz-check.md`, `hooks/state_check.py` and `commands/integrate.md` § 1 carry one rule table (#134) |
| L17 | the replay instrument's own lint — the forge stub's URLs name the fixture's repository, and an unserved `--json` field is UNKNOWN (#250) |
| L18 | the evaluation charter's own lint — `evals/charter.md` keeps its terms, levels and six rules, and the pages that apply it point at it (#257) |
| L19 | the documents' own lint — recorded baselines are data and rendered; the retired headline figures and phrasings stay out (#280) |
| D21 | the dispatch steps' own lint — a step that enumerates a dispatch's contents names the seat's R&R row (#294) |
| J2 | Judgment V1's own lint — the corpus is approved and leak-free, and the scorer reproduces hand-computed numbers (#258) |
| J3 | the Workflow Value pilot's own lint — the baseline is told nothing of the loop, the gold is the retrospective record, an invalid or unreviewed pair is never compared (#259) |

## Duplicated mechanical interpretation

The same mechanical question answered in prose in several files — each a
migration target, and each a place a fix lands in one file and not the
others (#95, #140 were this shape).

| question | files that answer it in prose | rows |
|---|---|---|
| review-clean | `references/workflow.md` (the definition), `commands/next-stage.md`, `commands/tip.md`, `commands/patrol.md`, `commands/integrate.md`, `references/patrol-scan.md` | C22 (obs), C22 (policy) |
| `reviewed-sha` against the branch head | the six above plus `references/branch-names.md` | C22 (obs) |
| a fidelity record on the QA CR | `commands/integrate.md`, `commands/next-stage.md`, `commands/patrol.md`, `commands/tip.md`, `references/fidelity-brief.md`, `references/patrol-scan.md`, `references/workflow.md` | C16 (obs), C16 (policy) |
| a CR merged, all states included | `commands/integrate.md`, `commands/next-stage.md`, `commands/spec-answers.md`, `commands/tip.md`, `references/patrol-scan.md` | C6, C13 |
| branch identity | every command before #135; now `bin/roz-branch` beside the prose Lookup | L4, C31 |

## Traces

### 1 · Branch Lookup — #135

| status | evidence |
|---|---|
| identified | #135 — five renderings of one template (prose, `bin/roz-config`, three hooks) |
| ready | #135 rulings 1–8 and amendments: inputs `git ls-remote --heads`, `UNKNOWN` → STOP, oracle `test_branch_names` + C31, shadow `shadow_branch_mismatch` |
| **shadow** (commands) | PR #254 (c7a5832): `bin/roz-branch` runs beside the commands' prose Lookup; the signal reads each run's own binding |
| **authoritative** (scanner) | PR #254: the scanner binds through `roz-branch match`; it never ran git, so it switched outright |
| authoritative (commands) | when `evals/CONTRIBUTING.md` § 7's exit holds — the seven-cell matrix observed, zero unexplained mismatches, N stable runs |
| migrated | the prose Lookup in `commands/next-stage.md` A2 / C2, `commands/integrate.md` and `commands/tip.md` deleted; rows C31 / C10 / C11 move to `migrated <sha>` |

### 2 · review-clean — the observation / policy split

| step | owner | what it is | status |
|---|---|---|---|
| observe | `roz-state` (#133) | the code-review marker's presence, its `reviewed-sha`, the CR's head, the open-thread count | **`shadow`** — `bin/roz-state` reports each as `observed` / `absent` / `unknown`; `shadow_state_mismatch` compares it with the forge stub's truth |
| interpret | `roz-check` (#134) | `reviewed-sha == head` ∧ marker present ∧ threads == 0 → clean — three rules of `bin/roz-check integrate` | **`shadow`** for integrate's entry (`shadow_check_mismatch`: the verdict against the lock). The other four restatements — next-stage, tip, patrol, the scanner — are not yet behind a check |
| shadow | `replaylib` | a `review_clean_mismatch` signal in C22 / C23, as `shadow_branch` is in C11 | — |
| delete | — | the five restatements above collapse to one call; `workflow.md` keeps the definition for humans | — |

The observation half is in shadow since #133: a failed THREADS-LIST or
CR-COMMENTS-LIST read is an `unknown` fact, never zero threads or a missing
record. The policy half is in shadow since #134 for one consumer —
integrate's entry: an `unknown` fact makes the rule `unknown` and the
verdict never `eligible` (no lock), and `shadow_check` is the signal. The
other restatements of review-clean are still prose only.

## Unguarded executable prose

Sections of at least 80 words that no lint literal lies inside and no replay
`check.py` cites in a `source:` line (computed when this page was written;
re-run by hand). Persona sections are expected here — they are semantic by
nature. The rest wait for a case or a reason.

| source § section | note |
|---|---|
| `agents/em.md` § Who You Are, § Skills, § What You Respect | persona |
| `agents/product.md` § Who You Are, § Skills | persona |
| `agents/qa.md` § Who You Are, § Skills | persona |
| `agents/reviewer.md` § Who You Are, § How You Think, § How You Communicate | persona |
| `commands/review-answers.md` § 5. Read it back, then wait | the read-back before any change at (7) — no case pins it |
| `commands/review-answers.md` § 7. The other door — back to intake | sending an issue back to intake — no case |
| `commands/to-issues.md` § 2. The relay loop | no case covers `to-issues` |
| `references/fidelity-brief.md` § Vacuous-assertion checklist | semantic; judgment fixtures could cover it |
| `references/forge-gitlab.md` § Identity, § Change requests | adapter prose; the GitHub twin is better covered |
| `references/gate-kit.md` § Binding rules (violating any of these deletes the kit's reason to exist) | no case |
| `references/identity-github-app.md` § GitHub — a GitHub App, § GitLab — a project access token | setup guidance, not a runtime rule |
| `references/intake-brief.md` § Multi-party rules (async), § The finalize dispatch (async), § Rules while clarifying, § Track proposal (the decision-content test) | intake is mostly semantic; A9 / A10 guard its two mechanical edges |
