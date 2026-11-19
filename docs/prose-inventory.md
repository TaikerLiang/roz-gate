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
*Not classified* with its reason; every hook rule A–L owns at least one row. Prose no case guards is listed under *Unguarded
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
| references/next-stage-path-b2.md | edited assertion (QA-4; the fidelity audit checks it) |
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
| C7 | references/next-stage-path-a.md | CR-OPEN from `<spec-branch>` targeting `<default_branch>` | Does the remote have the base the branch is cut from? | OBSERVATION | roz-branch | #135 | `roz-branch snapshot` heads | `UNKNOWN` → STOP | C7, F7 | — | not_ready |
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
| L22, D25, D26 | references/workflow.md | The commands resolve seats by running `bin/roz-persona` | Which agent type sits in each seat — the block's line, else the default — and is it there? | OBSERVATION | code bin/roz-persona | — | `bin/roz-persona --json` (the personas block through `find_block`; `.claude/agents/`, `~/.claude/agents/`, the plugin's `agents/`) | no usable agent → `PERSONA_UNMAPPED` / `AGENT_TYPE_UNAVAILABLE`, exit 2: the STOP exit; a name found nowhere is dispatched as printed, `checked: unverified` | L22, D25, D26, test_roz_persona | not required: already code | authoritative |
| C22 (policy) | commands/tip.md | review-clean is that record current **and** zero open threads | Is the implementation review-clean (`reviewed-sha` == head, marker present, zero open threads)? | MECHANICAL POLICY | roz-check | #134 ← row C22 (obs) | row C22 (obs) — a `roz-state` snapshot | the rule is `unknown` and the verdict never `eligible` — `may_start` false, no lock (`references/roz-check.md`) | C22, C23; `hooks/tests/test_roz_check.py`; the declared seeds (`redproof.py` § check) | `shadow_check_mismatch` (integrate's entry: C12, C16, D4, F4) | shadow |
| C16 (policy) | references/fidelity-brief.md | That comment is the record that the audit ran | May the QA CR integrate (a fidelity record on its current head, zero open fidelity threads)? | MECHANICAL POLICY | roz-check | #134 ← row C16 (obs) | row C16 (obs) — a `roz-state` snapshot | the rule is `unknown` and the verdict never `eligible` — `may_start` false, no lock (`references/roz-check.md`) | C16, C17; `hooks/tests/test_roz_check.py`; the declared seeds (`redproof.py` § check) | `shadow_check_mismatch` (C12, C16, D4, F4) | shadow |
| C24 (policy), F13 | references/patrol-scan.md | illegal state: gate label applied by | Is a gate label applied by a bot an illegal state? | MECHANICAL POLICY | roz-check | #134 ← row C24 (obs) | row C24 (obs), the block's `bot_login` | — | C24, F13 | — | identified |
| C27, F14 | references/patrol-scan.md | - **A gate label on a stage that passed.** For a `track: spec` issue | Is `ready-for-dev` on a stage that already passed an illegal state? | MECHANICAL POLICY | roz-check | #134 ← rows C6 / L4 | the label, CR-FIND of `<feat-branch>` (all-states) | — | C27, F14 | — | identified |
| C3 | references/workflow.md | label besides the `processing` lock | Does `processing` coexist with exactly one phase label? | MECHANICAL POLICY | roz-check | #134 | the issue's labels | — | C3 | — | identified |
| C10 | references/branch-names.md | **1 + max(`{seq}`)** | May a re-entry after a closed CR proceed, or is it the human's door (no `{seq}` → STOP)? | MECHANICAL POLICY | roz-check | #134 ← row C31 | `roz-branch lookup`, CR-FIND (all-states) | — | C10 | — | identified |
| C11 | references/branch-names.md | **1 + max(`{seq}`)** | Which `{seq}` does a re-entry cut, and does it collide? | MECHANICAL POLICY | roz-check | #134 ← row C31 | `roz-branch lookup` matches (`seq`), the snapshot | lookup `UNKNOWN` → STOP | C11, C31 | `shadow_branch_mismatch` (C11) | ready |
| C12 | commands/integrate.md | already merged in. | Are the feat and QA CRs merged, and is the spec branch's tip the one validated? | MECHANICAL POLICY | roz-check | #134 ← rows C6 / L4 | CR-FIND (all-states), `git merge-base --is-ancestor` | — | C12, F4 | — | not_ready |
| C20 | references/next-stage-path-b.md | ## Path B — implementation + review (3)+(5) | Has the implementation landed on the spec branch before (4) launches? | MECHANICAL POLICY | roz-check | #134 ← rows C22 / C6 | CR-FIND, `roz-branch` snapshot | — | C20 | — | identified |
| C14 | commands/init.md | - `fix_rounds` — optional: the fix-and-rerun budget on a red suite at (6) | Has the fix-and-rerun budget run out? | MECHANICAL POLICY | roz-check | #134 | `fix_rounds`, the rounds already spent (no observable count today) | — | C14 | — | not_ready |
| C17, C23 | references/patrol-scan.md | actionable: fidelity-audit | Is the audit / review that never ran the actionable step? | MECHANICAL POLICY | roz-check | #134 ← rows C16 / C22 (policy) | rows C16 / C22 (policy) | — | C17, C23 | — | identified |
| A4 | references/patrol-scan.md | Any unresolved thread whose last comment is a human answer | Is an `in-user-review` issue with an unheard human item actionable? | MECHANICAL POLICY | roz-check | #134 ← rows A1–A3 | rows A1, A2, A3 | — | A4, F1 | — | identified |
| E11 | commands/spec-answers.md | **A fold may ask once** (#206) | Is this question second-order (raised by a fold's answer), so deferred? | MECHANICAL POLICY | roz-check | #134 | the thread's marker lineage (CR comments) | — | E11 | — | identified |
| A10 | references/intake-brief.md | **[intake] · reply** | May an intake summary be written now? | MECHANICAL POLICY | hook A | — | the holder's latest comment | no holder comment → denied | A10, RuleA | not required: the hook is the source of truth | authoritative |
| C4 | references/workflow.md | **The gate label is the confirmation** | May an agent apply a gate label? | MECHANICAL POLICY | hook B | — | the Bash call | — | C4, RuleB | not required: the hook is the source of truth | authoritative |
| B4 | references/next-stage-path-a.md | MUST start with `**[ | Does an agent write open with its tag, never a quote block? | MECHANICAL POLICY | hook C | — | the comment body in the Bash call | — | B4, RuleC | not required: the hook is the source of truth | authoritative |
| E2 | references/next-stage-path-a.md | delete it from the source document | Do open questions live only in `spec.md` when a commit is made? | MECHANICAL POLICY | hook D | — | the staged spec documents | — | E2, RuleD | not required: the hook is the source of truth | authoritative |
| D2, D5, D7, D8 | references/next-stage-path-b2.md | roz-gate/fidelity-dispatch | May a call under a blind dispatch read this path or ref? | MECHANICAL POLICY | hook E | — | the marker (`seat=`, `feat=`, `read=`), the tool call | no marker → not blind | D2, D5, D7, D8, RuleE | not required: the hook is the source of truth | authoritative |
| E7 | references/next-stage-path-a.md | The options as **(a)/(b) bullets** | Does a question carry its options as bullets? | MECHANICAL POLICY | hook F | — | the comment body | — | E7, RuleF | not required: the hook is the source of truth | authoritative |
| C18 | references/workflow.md | it opens with the title `**[<command>] · blocked**` | Does a STOP comment name its resume move? | MECHANICAL POLICY | hook G | — | the comment body | — | C18, RuleG | not required: the hook is the source of truth | authoritative |
| E10 | references/next-stage-path-b.md | Guard-gate rule H denies a CR-OPEN whose diff touches `<specs_dir>/*/technical-spec.md` | Does a CR that changed the contract declare its deviations? | MECHANICAL POLICY | hook H | — | the CR-OPEN call, the diff | — | E10, RuleH | not required: the hook is the source of truth | authoritative |
| A9 | references/intake-brief.md | **[intake] · reply** | Does an intake reply answer the human who spoke? | MECHANICAL POLICY | hook I | — | the comment body, the thread | — | A9, RuleI | not required: the hook is the source of truth | authoritative |
| C25, C9 | commands/next-stage.md | `git worktree remove --force` every worktree this run created | Does the loop's worktree add run alone, and live under `roz-gate/wt/`? | MECHANICAL POLICY | hook J | — | the Bash call | — | C25, C9, RuleJ | not required: the hook is the source of truth | authoritative |
| C28 | references/workflow.md | A missing dependency in the base is a STOP, never an option | May the loop merge this ref into an issue branch? | MECHANICAL POLICY | hook K | — | the Bash call, the worktree's branch, `default_branch` | base unresolved → `main` (roz-config's rule) | C28, RuleK | not required: the hook is the source of truth | authoritative |
| D3, D29 | references/workflow.md | every dispatch attaches the seat's | Does a seat dispatch carry its R&R row and its `Plugin root:` line? | MECHANICAL POLICY | hook L | — | the Agent / Task call, workflow.md's R&R table, the personas block | — | D3, D29, RuleL | not required: the hook is the source of truth | authoritative |
| D4 | references/workflow.md | - **(4)** `qa` on `qa/{n}`, cut off `spec/{n}` **after the merge** | May this acceptance file be edited on this branch? | MECHANICAL POLICY | hook acceptance | — | the edited path, HEAD | — | D4, test_guard_acceptance | not required: the hook is the source of truth | authoritative |
| B1, B2, B6, B9 | references/next-stage-path-a.md | **`unverified` is a reserved word** in every spec document: it appears only as this tag | Does a spec document use a reserved word only as its tag? | MECHANICAL POLICY | none yet — a commit-time check on the spec documents (rule D's shape) could own it | — | the staged spec documents, `references/reserved-words.json` | — | B1, B2, B6, B9 | — | identified |
| B5 | references/intake-brief.md | <details><summary>Supplement — context and decision trail</summary> | Is the must-read on top and within its line budget? | MECHANICAL POLICY | none yet — a write-time form check (rule C's detector) could own it | — | the comment body | — | B5 | — | identified |
| B7, C26, C30 | commands/patrol.md | one row per issue the scanner listed | Is the pass report the fixed table, with each unreached row queued? | MECHANICAL POLICY | none yet — the report is the session's final text; no tool call carries it, so no hook sees it | — | — | — | B7, C26, C30, F11 | — | not_ready |
| C26 | commands/patrol.md | patrol_issues_per_pass | Which N actionable issues does this pass act on? | MECHANICAL POLICY | none yet — selection is not eligibility (#134), and #260 excludes an action resolver | — | the scan table, `patrol_issues_per_pass` | — | C26 | — | identified |
| C1, C2 | references/workflow.md | status labels with `blocked` alone | On a STOP, are the status labels `blocked` alone — and never at (7)? | MECHANICAL POLICY | none yet — a label write is one tool call; a hook could deny `blocked` beside a gate label | — | the label-write call, the issue's labels | — | C1, C2, F5 | — | identified |
| C8 | references/next-stage-path-a.md | Stage (2) spec refinement for #<n>. For review. Closes #<n>" | Does the CR body close its issue? | MECHANICAL POLICY | none yet — the CR-OPEN call (rule H's detector) could check the body | — | the CR-OPEN call | — | C8 | — | identified |
| C15 | references/workflow.md | A command's git reference to it is always `origin/<default_branch>` | Does every git site name `origin/<default_branch>`, never the bare branch? | MECHANICAL POLICY | none yet — hook K covers the merge; a diff naming the bare branch has no hook | — | the Bash call | — | C15 | — | identified |
| C19, F12 | commands/tip.md | **Read-only.** This command writes nothing: no label, no comment, no commit, | Does tip write nothing? | MECHANICAL POLICY | none yet — tip sets no marker, so no hook can tell its calls apart | — | the tool calls | — | C19, F12 | — | identified |
| D1, D6, D28 | commands/next-stage.md | attaching the seat's R&R row | Does a dispatch carry its required lines (claim, amendment list)? | MECHANICAL POLICY | none yet — the dispatch text is model-composed; a dispatch-time check could own its required lines (hook L owns the R&R row and the plugin root) | — | the dispatch text | — | D1, D6, D28 | — | identified |
| E9 | references/qa-brief.md | ## Step zero — the contract review | Is a QA contract question posted as a `[qa]` thread on the spec CR? | MECHANICAL POLICY | none yet — a write-time form check could own the routing | — | the comment call | — | E9 | — | identified |
| L3 | references/workflow.md | made by the **commit sub-agent** (`references/commit-brief.md`) | Does every commit go through the commit sub-agent? | MECHANICAL POLICY | none yet — the commit sub-agent sets no marker a hook could read | — | the `git commit` call | — | L3 | — | identified |
| L6 | commands/init.md | they run **in a linked worktree** (`git worktree add`, under `.git/roz-gate/wt/<branch>`), never in the checkout | Do `test` / `acceptance_test` run in a linked worktree? | MECHANICAL POLICY | none yet — a hook could read the cwd of the test call | — | the Bash call's cwd | — | L6, F8 | — | identified |

## Kept in prose

Block granularity: each conclusion is "stays", so one row per block, with
the reason.

| id | source | anchor | question | class | why it needs a model or a human |
|---|---|---|---|---|---|
| B8, D9–D19, E12 | references/qa-brief.md | **The port is the only road.** | How does QA write a suite that drives the port and asserts the contract — and is a red a harness defect or a contract mismatch? | SEMANTIC JUDGMENT | reading a contract and deciding what a red means is judgment; the mechanical edge (what QA may read) is hook E |
| D22–D24 | references/qa-brief.md | ## Step zero — the contract review | Is this a hole in the shared contract, or a term used against its Glossary definition — to report, never to resolve alone? | SEMANTIC JUDGMENT | whether a Given has a control point, or a clause means what the Glossary defines, is a reading of the contract |
| C5 | commands/spec-answers.md | **The fold changed no behaviour** | Did the fold change behaviour? | SEMANTIC JUDGMENT | whether an amendment changes behaviour is a reading of the spec |
| C29 | references/workflow.md | A missing dependency in the base is a STOP, never an option | Does the base lack code another issue delivers? | SEMANTIC JUDGMENT | only a reader of the spec knows what the issue needs; the forbidden remedy is hook K (row C28) |
| E3, E4 | references/next-stage-path-a.md | Dispatch `implementer` | Should the implementer / reviewer stop and ask the holder? | SEMANTIC JUDGMENT | when a question is worth the holder's time is judgment; how it reaches them is hook F |
| C32 | references/next-stage-path-b.md | `accept a bounded risk` | What does each reserved-word hit do to the contract, and which of the four actions does it get? | SEMANTIC JUDGMENT | whether a guarantee, scenario or acceptance criterion depends on a claim is a reading of the spec; the gate itself is the grep (B6, B9) |
| E15 | commands/spec-answers.md | **A demotion a guarantee needs is not folded** | Does a demotion answer leave a guarantee resting on an unmeasured premise? | SEMANTIC JUDGMENT | which clauses depend on a premise is a reading of the spec; the promote grep keeps blocking either way |
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
| A8, B3, B10, D20, E13, E14 | rules about the prose itself (one scan sub-agent; one marker convention; the reserved-word STOP's per-hit table; the blindness rule's clause structure; step zero's decision chain; the QA persona carries no procedure that contradicts the brief) — checked statically, never answered at runtime |
| J1 | the judgment tier's own instrument |
| L1, L7, L9, L10, L11, L12 | human-facing pages, not executable prose |
| L8 | the `/roz-gate:config` mod's implementation, not a question the loop answers |
| L13, L14 | this page's own lints (the inventory; § Kernel) |
| L15 | the `roz-state` contract's own lint — `references/roz-state.md` and `hooks/state_contract.py` carry one field table (#239) |
| L16 | `roz-check`'s own lint — `references/roz-check.md`, `hooks/state_check.py` and `commands/integrate.md` § 1 carry one rule table (#134) |
| L17 | the replay instrument's own lint — the forge stub's URLs name the fixture's repository, and an unserved `--json` field is UNKNOWN (#250) |
| L18 | the evaluation charter's own lint — `evals/charter.md` keeps its terms, levels and six rules, and the pages that apply it point at it (#257) |
| L19 | the documents' own lint — recorded baselines are data and rendered; the retired headline figures and phrasings stay out (#280) |
| L20 | `next-stage`'s own lint — the route table names one path file per row, every step id is a heading in exactly one file, the hand-off instruction is present (#279) |
| L21 | rules about the prose itself — the repo's runtime prose total and each command file's word count stay within their caps (#278) |
| L23 | the prohibition audit's own lint — `docs/prohibitions.json` held to the runtime prose, one quote per clause (#380) |
| D27 | rule E's own wiring lint — the dispatch's `Implementation:` line is rendered by the reader the hook enforces from (`hooks/implementation_dirs.py`, #281); the behaviour is the hook tests' |
| D21 | the dispatch steps' own lint — a step that enumerates a dispatch's contents names the seat's R&R row (#294) |
| J2 | Judgment V1's own lint — the corpus is approved and leak-free, and the scorer reproduces hand-computed numbers (#258) |
| J3 | the Workflow Value pilot's own lint — the baseline is told nothing of the loop, the gold is the retrospective record, an invalid or unreviewed pair is never compared (#259) |

## Duplicated mechanical interpretation

The same mechanical question answered in prose in several files — each a
migration target, and each a place a fix lands in one file and not the
others (#95, #140 were this shape).

| question | files that answer it in prose | rows |
|---|---|---|
| review-clean | `references/workflow.md` (the definition), `references/next-stage-path-b.md`, `references/next-stage-path-b2.md`, `references/next-stage-path-c.md`, `references/code-review-mechanics.md`, `commands/tip.md`, `commands/patrol.md`, `commands/integrate.md`, `references/patrol-scan.md` | C22 (obs), C22 (policy) |
| `reviewed-sha` against the branch head | the files above plus `references/branch-names.md` | C22 (obs) |
| a fidelity record on the QA CR | `commands/integrate.md`, `references/next-stage-path-b2.md`, `commands/patrol.md`, `commands/tip.md`, `references/fidelity-brief.md`, `references/patrol-scan.md`, `references/workflow.md` | C16 (obs), C16 (policy) |
| a CR merged, all states included | `commands/integrate.md`, `commands/next-stage.md` and its four path files, `commands/spec-answers.md`, `commands/tip.md`, `references/patrol-scan.md` | C6, C13 |
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
| migrated | the prose Lookup in `references/next-stage-path-a.md` A2 / `references/next-stage-path-c.md` C2, `commands/integrate.md` and `commands/tip.md` deleted; rows C31 / C10 / C11 move to `migrated <sha>` |

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

## Prohibitions

Every `never`, `cannot`, `do not`, `must not`, `forbidden`, `may not` and
`only … may` the runtime prose states, and who enforces it (#380). "In a
prompt, the agent decides whether to obey. With a hook, the call is blocked
every time" — this section records which of the two each prohibition is.
The data is `docs/prohibitions.json`; the block below is rendered from it
by `tools/ledger.py`, and lint L23 holds the data to the prose.

**A row is one distinct rule.** Two prohibitions share a row only when they
have the same **predicate**, the same **consequence** and the same
**scope**; when uncertain they are separate rows (#262: one prohibition
clause, one decision question, one rule). A later issue may prove two rows
one invariant and merge them; the audit does not.

**A source is one clause.** `{file, quote}`: the quote occurs exactly once
in its file and holds exactly one prohibition word, and every prohibition
word lies inside exactly one quote. A sentence with two prohibitions is two
sources — and `only … may` is counted at its `only`, so a prohibition
between the two words is a clause of its own. A line number is never stored: an edit that leaves the clause
alone leaves the row alone, and one that changes the clause makes the row
stale — which is when to look at it again.

| class | meaning | `owner` | `evidence` |
|---|---|---|---|
| `hooked` | a hook denies the act itself — not a narrower operational boundary beside it (rule E stops QA reading the implementation; it does not make an assertion follow the contract) | `hook <rule>` | the hook-test cases |
| `deterministic-candidate` | the rule's **whole predicate** is decidable from files, git and one call's input, and nothing decides it. A rule whose predicate needs something no call carries — which command is writing, say — is not one, however easy part of it is to recognise. Its issue chooses the owner, in this order: the architecture removes the invalid choice · a generator produces the value · `roz-check` or a static check verifies it · a hook denies it · it stays prose (#352, #354: push a failure down the trust stack; eliminate before denying) | `none yet` | the follow-up issue |
| `guarded-by-case` | a lint, replay or judgment case asserts this prohibition — not a neighbouring one | the prose or kernel rule that owns it | ledger ids |
| `prose-only` | nothing enforces it. The reason says why: `semantic`, `persona`, `authority` — or `unguarded — <what would guard it>`, a gap recorded as a gap | `prose` | — |
| `not-a-rule` | the word forbids an agent nothing: a fact, a condition, another seat's rule described, a line addressed to the human | — | — |

**The evidence bar is the owner's, not the class's.** Evidence that a rule
matters is not evidence that a blocking mechanism is justified, so what a
candidate's issue must show depends on the owner it ends with:

| eventual owner | what justifies it |
|---|---|
| the architecture removes the invalid choice, or a generator produces the value | an architecture justification and tests of the invariant — no prior failure is required |
| a static lint or `roz-check` verification | an accepted deterministic contract and a red-proof of the checker |
| another runtime blocking policy | strong observed failure evidence |
| a runtime deny hook | a replay red or a shipped defect (`hooks/README.md` § How to add a rule) |

Where a prohibition could be both, the stronger claim on enforcement wins:
`hooked`, then `deterministic-candidate`, then `guarded-by-case`.

**What the lint cannot see.** A prohibition spelled with none of these
words ("no force-push", "is not yours to …"); whether a class is right;
whether the evidence is enough. Those are review. Sections no case touches
at all are listed under *Unguarded executable prose*, by section — a
different unit, kept apart.

<!-- prohibitions -->
Scope: `agents/`, `commands/`, `references/`, `templates/` — 36 files, 523 prohibition words, each inside one quote of one row.

| class | rules | sources |
|---|---|---|
| `hooked` | 7 | 18 |
| `deterministic-candidate` | 15 | 34 |
| `guarded-by-case` | 72 | 159 |
| `prose-only` | 121 | 157 |
| `not-a-rule` (reasons) | 12 | 155 |

Of the `prose-only` rules, **71 are `unguarded`** — not semantic, and nothing enforces them yet.

| id | rule | stated in | class | owner | evidence / reason |
|---|---|---|---|---|---|
| P001 | Dispatched with no one to ask, a spec seat never waits for an answer — it returns its open questions with the deliverable | `agents/em.md` · `agents/product.md` | `prose-only` | prose | unguarded — a replay case in which a dispatched seat holds an open question and must return it rather than end its turn asking (E2 guards where a returned question lands, not that the seat returns it) |
| P002 | A dispatched spec seat never silently assumes an answer to an open question | `agents/em.md` · `agents/product.md` | `prose-only` | prose | semantic — whether a choice was an assumption is a reading of the deliverable against the spec |
| P003 | A seat folding an answer never posts its follow-up question to the forge itself — the main agent posts or defers it | `agents/em.md` · `agents/product.md` | `deterministic-candidate` | none yet | #391 |
| P004 | em never accepts a vague answer to a requirement | `agents/em.md` | `prose-only` | prose | persona — how the seat interrogates; what counts as vague is its judgment |
| P005 | product never accepts a happy-path-only answer | `agents/product.md` | `prose-only` | prose | persona — how the seat interrogates; what counts as happy-path-only is its judgment |
| P006 | A spec seat never offers merging, rebasing onto or cherry-picking from another branch as an option — it reports the missing dependency | `agents/em.md` · `agents/product.md` · `references/next-stage-path-a.md` | `guarded-by-case` | references/workflow.md | C29 |
| P012 | QA never resolves an ambiguity in the spec by interpretation — an ambiguity is a finding it reports | `agents/qa.md` | `guarded-by-case` | references/qa-brief.md | D24, E14 |
| P013 | QA tests against the contract, never the raw implementation | `agents/qa.md` · `references/workflow.md` · `references/qa-brief.md` | `guarded-by-case` | references/qa-brief.md | B8, D9, D10, D13 — hook E is a supporting operational boundary (no read of the implementation during the dispatch), not this rule's owner: a seat can obey E and still assert what it observed |
| P014 | The acceptance tests are a maintained suite, never write-once snapshots | `agents/qa.md` · `references/workflow.md` | `prose-only` | prose | semantic — whether a suite is maintained or a snapshot is a reading of how it was written |
| P015 | QA never flags a project-sanctioned test layout as a violation | `agents/qa.md` | `prose-only` | prose | semantic — whether a finding is about the layout is a reading of the finding |
| P016 | `test-spec.md`'s scenario→test map is derived from the trace markers in the test source, never hand-maintained | `agents/qa.md` · `references/workflow.md` · `references/qa-brief.md` | `deterministic-candidate` | none yet | #392 |
| P017 | A QA red is a harness issue fixed or a finding reported, never an edited assertion (QA-4) | `agents/qa.md` · `references/workflow.md` · `references/qa-brief.md` · `references/next-stage-path-b2.md` | `guarded-by-case` | kernel QA-4 (`references/qa-brief.md`) | B8, D9, D13 |
| P018 | QA references exact scenario names, never a paraphrase | `agents/qa.md` | `prose-only` | prose | persona — how the seat communicates |
| P019 | QA does not negotiate on violations | `agents/qa.md` | `prose-only` | prose | persona — how the seat communicates |
| P020 | The reviewer does not redesign the architecture | `agents/reviewer.md` | `prose-only` | prose | persona — the seat's role boundary; whether a comment is a redesign is its judgment |
| P021 | The reviewer does not re-test behaviour against the spec | `agents/reviewer.md` | `prose-only` | prose | persona — the seat's role boundary |
| P022 | A review comment is never a vague "consider refactoring" | `agents/reviewer.md` | `prose-only` | prose | persona — how the seat communicates |
| P023 | The reviewer never invents problems to look thorough | `agents/reviewer.md` | `prose-only` | prose | persona — how the seat communicates |
| P024 | A contract corrected while building is declared under `## Contract deviations`, never silently changed | `templates/implementer.md` | `prose-only` | prose | unguarded — a case in which the build's contract diff and its `## Contract deviations` section disagree: a corrected clause the section does not list — hook H is a supporting operational boundary (a CR whose diff touches `technical-spec.md` must carry the section), not this rule's owner: a section that says `none` passes it |
| P025 | The implementer never substitutes a local reading for a Glossary definition it cannot build to | `templates/implementer.md` | `prose-only` | prose | semantic — whether the build follows the definition is a reading of the code against the Glossary |
| P026 | The implementer never waits on an open question mid-job — it returns its open questions with the deliverable | `templates/implementer.md` | `prose-only` | prose | unguarded — a replay case in which the dispatched implementer holds an open question and must return it rather than end its turn asking (E3 guards that the route exists, not that it is taken) |
| P027 | The implementer never silently assumes an answer to an open question | `templates/implementer.md` | `prose-only` | prose | semantic — whether a choice was an assumption is a reading of the build against the spec |
| P028 | The config command never edits `.claude/roz-gate.local.json`, `CLAUDE.md` or `CLAUDE.local.md` itself — `bin/roz-config` does the write | `commands/config.md` | `prose-only` | prose | unguarded — a replay case on `/roz-gate:config` setting a key: the local file changes only through `bin/roz-config`, with no Edit or Write on it — not a deterministic candidate today: the predicate is which command is writing, not which path is written (`init` writes `CLAUDE.md` legitimately), and no tool call or local state carries a trustworthy command identity. It becomes one if the architecture introduces a command-context / capability boundary |
| P030 | A multi-value config key is passed one value per quoted argument, never split on spaces | `commands/config.md` | `prose-only` | prose | unguarded — a replay case on `/roz-gate:config` setting `inbox_label` to a label that holds a space |
| P032 | An agent never applies a gate label (`ready-for-spec`, `ready-for-dev`) — the gate is the human's | `commands/config.md` · `commands/to-issues.md` · `commands/spec-answers.md` · `commands/patrol.md` · `references/workflow.md` | `hooked` | hook B | `hooks/tests/test_guard_gate.py::RuleB_GateLabelsAreHumanOnly` |
| P033 | The config command never creates forge labels | `commands/config.md` | `prose-only` | prose | unguarded — a replay case on `/roz-gate:config` whose forge journal holds no label-create call |
| P034 | init says, where it asks for `test` and `acceptance_test`, that they run in a linked worktree, never in the checkout | `commands/init.md` | `guarded-by-case` | references/workflow.md | L6 |
| P035 | init never automates the bot credential's creation — it points the user at the one-time setup | `commands/init.md` | `prose-only` | prose | authority — creating a credential is the human's act |
| P036 | On GitLab the `processing` lock label is created plain, never scoped — it must coexist with a phase label | `commands/init.md` · `references/forge-gitlab.md` | `prose-only` | prose | unguarded — a lint on init's GitLab label list, or a replay of init on GitLab whose journal creates `processing` unscoped (C3 checks label coexistence, not how init creates the label) |
| P037 | A `type:` label is never a gate — no command applies, removes, validates or dispatches on one | `commands/init.md` | `prose-only` | prose | unguarded — a replay case in which an issue carries a `type:` label and no gate label: nothing is dispatched |
| P038 | init never copies the workflow prose into the project's `CLAUDE.md` — only the pointer and the config block | `commands/init.md` | `prose-only` | prose | unguarded — a replay case on init whose resulting `CLAUDE.md` section is the template's pointer and block and nothing from `references/workflow.md` |
| P039 | init never copies, moves or renames a user's agent file when it links a seat | `commands/init.md` | `prose-only` | prose | unguarded — a replay case on init linking a seat: the user's agent file is byte-identical and in place afterwards |
| P041 | init never links a persona that fails the seat's contract check without showing the violating lines | `commands/init.md` | `prose-only` | prose | semantic — whether a persona's text fights the seat's Never column is a reading of that text |
| P042 | init never edits an existing `CLAUDE.md` section without showing the change first | `commands/init.md` | `prose-only` | prose | unguarded — a replay case on init over a project that already has the section: the change is shown before any write to `CLAUDE.md` |
| P043 | A command's git work runs in a linked worktree, never in the user's checkout | `commands/next-stage.md` · `commands/patrol.md` · `references/commit-brief.md` · `references/workflow.md` | `guarded-by-case` | references/workflow.md | C9, F8 |
| P044 | next-stage never scans for Path B2 — it is reached by number only | `commands/next-stage.md` | `prose-only` | prose | unguarded — a replay case in which a QA-ready issue exists and next-stage runs with no number: it is not picked |
| P045 | next-stage never repairs a label-invariant violation itself — it stops and reports | `commands/next-stage.md` · `references/workflow.md` · `references/patrol-scan.md` | `prose-only` | prose | unguarded — a replay case on next-stage over an issue with two `track:` labels: the labels are unchanged and the run reports |
| P047 | The loop never merges another issue's branch into the issue branch — the remedy is to sync the base | `commands/next-stage.md` · `commands/spec-answers.md` | `hooked` | hook K | `hooks/tests/test_guard_gate.py::RuleK_LoopMergesOnlyBaseOrOwn` — rule K acts in a loop worktree — where every command's git work runs; a merge in the person's own checkout is not the loop's and is not judged |
| P048 | The fast track's escalation valve (C3) never uses the STOP exit — it is a designed transition | `commands/next-stage.md` | `prose-only` | prose | unguarded — a replay case that escalates a fast-track issue: labels end on the spec track's gate, not `status: blocked`, and no STOP comment is posted |
| P049 | to-issues relays the intake seat's question to the user verbatim — it does not answer, soften or batch it | `commands/to-issues.md` | `prose-only` | prose | unguarded — a replay case on to-issues in which the seat returns a question: the text shown to the user is the seat's, unaltered |
| P050 | uninit never retires the loop mid-flight — open loop issues or CRs stop it | `commands/uninit.md` | `prose-only` | prose | unguarded — a replay case on uninit with an open `spec/*` CR: it stops and lists it, removing nothing |
| P051 | uninit never deletes the work products — specs, the acceptance suite, issue and CR history | `commands/uninit.md` | `prose-only` | prose | unguarded — a replay case on uninit: `<specs_dir>` and `<acceptance_dir>` are intact afterwards |
| P052 | An existing branch is found by Lookup, never guessed | `commands/integrate.md` · `commands/review-answers.md` · `commands/spec-answers.md` · `commands/patrol.md` · `references/branch-names.md` · `references/workflow.md` | `guarded-by-case` | references/branch-names.md | C31 |
| P053 | integrate's worktree starts at the remote's spec-branch tip, never at a stale local ref | `commands/integrate.md` · `references/next-stage-path-b2.md` | `prose-only` | prose | unguarded — a replay seed whose local spec ref is behind the remote's (every seed today has local = remote, so only the source shows it) |
| P054 | integrate merges a CR that is open, never one already merged | `commands/integrate.md` · `references/workflow.md` | `guarded-by-case` | commands/integrate.md | C12 |
| P055 | Once both CRs are merged, integrate validates the current spec-branch tip — it never reconstructs it from stale `feat` / `qa` tips | `commands/integrate.md` · `references/workflow.md` | `guarded-by-case` | commands/integrate.md | C12 |
| P057 | On a re-verdict the final-gate kit's cards are regenerated wholesale from the new run, never patched | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay re-verdict whose kit comment afterwards carries the new run's cards and a re-stamped `cards-sha`, with none of the earlier run's text |
| P058 | A green verdict states what the run licenses — "green against the pre-rework spec, at SHA x" — never "verified" | `commands/integrate.md` · `references/workflow.md` | `guarded-by-case` | commands/integrate.md | F4, C12 |
| P059 | A classifiable RED at integration is routed to its fix, never finalized | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay case with a red integration: labels do not reach `in-user-review` and the spec branch is not pushed as green |
| P060 | An integration RED is fixed in the implementation, the harness or the contract, never in a QA assertion (QA-4 at stage 6) | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay case with an integration red that is a contract disagreement: the assertion is unchanged afterwards (D9 / D19 assert QA-4 at the QA dispatch, not at integration) |
| P061 | On a STOP `status: blocked` is worn alone, never beside a gate or phase label | `commands/integrate.md` | `guarded-by-case` | references/workflow.md | C1, F5 — C1 and F5 assert `blocked` alone on next-stage's STOP; integrate's re-verdict STOP (entered from `in-user-review`) has no case of its own |
| P062 | A red integration is never silently merged | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay case with a red integration: the spec CR is not merged and the report says red |
| P063 | The gate-kit comment is never a review item | `commands/review-answers.md` · `commands/tip.md` · `commands/spec-answers.md` · `references/patrol-scan.md` | `guarded-by-case` | commands/review-answers.md | E8 |
| P064 | A behavioural claim in a review answer cites a spec rule or a test, never a code line alone | `commands/review-answers.md` | `prose-only` | prose | semantic — whether a claim is behavioural and what it rests on is a reading of the answer |
| P065 | A marker-carrying comment never opens with a quote block | `commands/review-answers.md` | `hooked` | hook C | `hooks/tests/test_guard_gate.py::RuleC_MarkerCommentNeverOpensWithAQuote` |
| P066 | A stage-(7) answer never resolves the user's thread — the user's satisfaction closes it | `commands/review-answers.md` | `guarded-by-case` | commands/review-answers.md | F2 |
| P067 | Silence is never consent to a change at stage (7) | `commands/review-answers.md` · `references/workflow.md` | `prose-only` | prose | authority — only the user's word authorizes a change; whether a reply is that word is a reading of it |
| P068 | A reaction is consent to a readback proposing one change, never to one proposing several | `commands/review-answers.md` | `prose-only` | prose | authority — only the user's word authorizes a change; whether a readback proposes one change or several is a reading of it |
| P069 | At stage (7) an ambiguous reply resolves to asking, never to acting | `commands/review-answers.md` | `prose-only` | prose | semantic — whether a reply is ambiguous is a reading of it |
| P070 | A failing assertion that faithfully states the contract is never classified as "they authorized it" — the user rules | `commands/review-answers.md` | `prose-only` | prose | authority — ruling on a contract defect is the user's; whether an assertion faithfully states the contract is a reading |
| P071 | The back-to-intake door is taken on the user's word, never by the agent on its own | `commands/review-answers.md` | `prose-only` | prose | authority — abandoning the issue's work is the user's decision |
| P072 | tip is typed by the user; patrol never runs it | `commands/tip.md` | `guarded-by-case` | commands/tip.md | C19 |
| P073 | Asked to act on what it finds, tip names the command or the human act — it never does it itself | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 |
| P074 | A lock tip finds is part of its answer, never something it waits on or clears | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 — F12 asserts zero writes (the lock is not cleared); nothing asserts that tip does not wait |
| P075 | Review-clean is the code-review record current and zero open threads, never zero threads alone | `commands/tip.md` · `commands/patrol.md` · `references/patrol-scan.md` · `references/next-stage-path-b2.md` | `guarded-by-case` | references/workflow.md | C22 — C22 asserts it at next-stage B2.1; tip's own reading of review-clean has no case |
| P076 | tip's answer is a reading of the documents, never a new rule | `commands/tip.md` | `prose-only` | prose | semantic — whether an answer adds a rule the documents do not give is a reading of it |
| P077 | tip names the repair for an illegal or stuck state and never performs it | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 |
| P078 | tip never declares a `processing` lock stale — it reports the pair and the evidence | `commands/tip.md` | `prose-only` | prose | unguarded — a replay case on tip over `processing` beside a phase label: the answer reports the pair and does not call the lock stale |
| P079 | An agent never deletes or force-pushes a remote branch — `git push origin --delete` is the human's to run | `commands/tip.md` · `references/branch-names.md` · `references/workflow.md` · `references/next-stage-path-c.md` · `references/next-stage-path-a.md` | `deterministic-candidate` | none yet | #394 |
| P080 | tip never writes — no label, no comment, no commit, no branch, no cleared `blocked` | `commands/tip.md` | `guarded-by-case` | commands/tip.md | C19, F12 |
| P081 | tip never dispatches a seat | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 |
| P082 | The agent-marker predicate (`**[`, `✅ [`) never swallows a human's bare `✅` answer | `commands/spec-answers.md` | `guarded-by-case` | references/patrol-scan.md | A1 |
| P083 | A ruling's authority tag and an empirical premise's `(unverified)` evidence tag are never merged into one parenthesis | `commands/spec-answers.md` | `deterministic-candidate` | none yet | #396 |
| P084 | A question a depth-0 fold raises is a new `Q<k>` with its own thread, never a reply in the folded question's thread | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay case in which a depth-0 fold raises a question: a new thread exists and the folded thread gains no question reply (E11 covers depth 1) |
| P085 | On a post-integration re-entry a question the fold surfaces is one top-level `[review] · question` comment, never a new seat thread | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | C5 |
| P086 | On a post-integration re-entry a question the fold surfaces is never deferred | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay re-entry whose fold surfaces a question: no `· deferred` entry and no `[spec-answers] · deferred` comment |
| P087 | A rule born from an amendment carries `(from A<k>)` as its provenance, never `(assumed)` | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay amendment fold (E6's or E8's seed): the rule it adds is tagged `(from A<k>)` |
| P088 | A resolved Open Questions entry never restates rule, scenario or contract text — it points at IDs | `commands/spec-answers.md` | `prose-only` | prose | semantic — whether an entry restates a rule or points at it is a reading of the entry |
| P089 | The re-spawned folding seat never writes `## Open Questions` itself — em owns the section | `commands/spec-answers.md` · `references/next-stage-path-a.md` | `guarded-by-case` | references/workflow.md | E11 |
| P090 | A `· follow-up` reply on the same question is never deferred | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | E11 |
| P091 | A seat that needs more information never resolves the thread — it replies `· follow-up` and leaves it open | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay case in which the folding seat returns a follow-up: the thread carries the reply and is still unresolved |
| P092 | spec-answers never edits the issue body or acceptance criteria — it comments, and the user decides whether to amend | `commands/spec-answers.md` · `references/workflow.md` | `prose-only` | prose | unguarded — a replay case whose resolution changes the user story: the journal holds an ISSUE-COMMENT and no ISSUE-EDIT-BODY (the call alone does not decide it: intake's finalize edits the body legitimately) |
| P093 | Fold threads and the `[spec-answers] · deferred` comment are posted after the push, never before | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | E11 |
| P094 | A post-integration fold never returns the issue to implementation | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | C5 |
| P095 | A red on a post-integration re-entry is never resolved by editing an assertion to match (QA-4) | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay re-entry whose acceptance run is red: the assertion is unchanged afterwards |
| P096 | When a post-integration fold changed behaviour, the stale pair is not taken as evidence — the suite is not run for it, the cards are not regenerated, `cards-sha` is not re-stamped | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | C5 |
| P097 | patrol never re-reads the forge to confirm a row of the scanner's table | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A8, F9 |
| P098 | A row patrol cannot act on as written is reported as an illegal state, never re-derived | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay pass whose scanner table carries a verdict outside the brief's list: the row is reported `illegal:` and the forge is not re-read for it |
| P099 | patrol never re-scans between the actions of one pass | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | F9 — F9 asserts the main agent lists nothing after the table; a second scanner dispatch in an N>1 pass (C26) has no assertion of its own |
| P100 | A merged CR on an issue in an unexpected status is an illegal state patrol reports and never repairs | `commands/patrol.md` · `references/patrol-scan.md` | `prose-only` | prose | unguarded — a replay pass over a merged CR whose issue wears a status other than the close-out's: no label or close is written and the row is `illegal:` (C24 / C27 / F13 / F14 cover gate-label illegal states) |
| P101 | The implementer is never dispatched onto a fast-track branch — the main agent addresses its own CR's threads | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay address-review pass on a fast CR: no `implementer` dispatch |
| P102 | A seat never commits — every commit goes through the commit sub-agent | `commands/patrol.md` · `references/qa-brief.md` | `guarded-by-case` | references/commit-brief.md | L3 |
| P103 | patrol's code-review action never commits | `commands/patrol.md` | `prose-only` | prose | unguarded — C23's seed with an assertion that the remote's refs are unchanged by the action |
| P104 | patrol's code-review action never resolves a thread | `commands/patrol.md` | `prose-only` | prose | unguarded — C23's seed with an assertion that the journal holds no thread-resolve |
| P105 | patrol's fidelity-audit action never commits | `commands/patrol.md` | `prose-only` | prose | unguarded — C17's seed with an assertion that the remote's refs are unchanged by the action |
| P106 | patrol's fidelity-audit action never touches the implementation branch | `commands/patrol.md` | `prose-only` | prose | unguarded — C17's seed with an assertion that no call of the action names the implementation branch — hook E is a supporting operational boundary (while the marker exists a git action on the implementation ref is denied), not this rule's owner: the action also runs before the marker is written and after it is removed |
| P107 | patrol's fidelity-audit action never resolves a thread | `commands/patrol.md` | `prose-only` | prose | unguarded — C17's seed with an assertion that the journal holds no thread-resolve |
| P108 | The gate holder is read from the scanner's table, never re-listed | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A8, F9 |
| P109 | A bot identity never holds a gate | `commands/patrol.md` · `references/forge-github.md` · `references/forge-gitlab.md` · `references/workflow.md` · `references/intake-brief.md` | `prose-only` | prose | unguarded — a replay pass over a bot-authored, unassigned inbox issue: no summary is written and the report says it needs an assignee (C24 / F13 cover a bot-applied label, not a bot holder) — hook A is a supporting operational boundary: an `[intake] · summary` on a bot-authored, unassigned issue is denied (`has no holder`) |
| P110 | On an issue with no gate holder only the questions batch may be posted | `commands/patrol.md` | `prose-only` | prose | unguarded — the same replay pass: the journal holds the `[intake]` batch and no other comment on that issue — hook A is a supporting operational boundary (a summary with no holder is denied), not the whole rule |
| P111 | Intake's clarification thinking is the dispatched `product` seat's, never patrol's own | `commands/patrol.md` · `references/workflow.md` | `prose-only` | prose | unguarded — a replay intake pass: a `product` dispatch precedes every `[intake]` comment and the comment is its text |
| P112 | At finalize, comments from anyone but the gate holder are thread discussion — never folded in, never listed, never a reason to wait | `commands/patrol.md` · `references/workflow.md` · `references/intake-brief.md` | `prose-only` | prose | unguarded — a replay finalize on an issue whose latest summary is followed by a non-holder comment: the summary is finalized verbatim and nothing waits |
| P113 | A summary request from anyone but the gate holder never triggers an intake summary | `commands/patrol.md` | `hooked` | hook A | `hooks/tests/test_guard_gate.py::RuleA_IntakeSummaryTrigger` |
| P114 | The intake question batch is asked once — patrol never re-batches | `commands/patrol.md` · `references/workflow.md` | `deterministic-candidate` | none yet | #395 |
| P115 | A bot's or an agent-marker comment never counts as a human comment on an intake thread | `commands/patrol.md` · `references/workflow.md` | `guarded-by-case` | references/patrol-scan.md | A9 — hook I is a supporting boundary: a reply where no human comment follows the latest `[intake]` comment is denied |
| P116 | An intake reply never re-asks the question batch | `commands/patrol.md` · `references/workflow.md` · `references/intake-brief.md` | `guarded-by-case` | commands/patrol.md | A9 |
| P117 | An intake reply never edits the issue body or a label | `commands/patrol.md` · `references/workflow.md` · `references/intake-brief.md` | `guarded-by-case` | commands/patrol.md | A9 |
| P118 | An intake reply never @-mentions anyone | `commands/patrol.md` · `references/intake-brief.md` | `guarded-by-case` | commands/patrol.md | A9 |
| P119 | A `this pass` cell is one clause from the vocabulary, never a list and never a commit log | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | B7, F11 |
| P120 | An actionable row the pass did not reach is `queued: <action>`, never `in progress` | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | C30 |
| P121 | An in-flight `track: spec` row never needs a label from the holder | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | C30 |
| P122 | A gated row waiting on an open blocker reads `waits on #<n>` alone — never `queued: waits on …`, never `blocked:` | `commands/patrol.md` · `references/patrol-scan.md` | `guarded-by-case` | commands/patrol.md | F15 |
| P123 | A row whose branches are unknown is never acted on and never read as "no branch" | `commands/patrol.md` · `references/branch-names.md` · `references/patrol-scan.md` · `references/roz-state.md` | `guarded-by-case` | references/branch-names.md | C31, A11 |
| P124 | A queue item is never written without its link | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | B7, F11 |
| P125 | An illegal state is a table row and a queue item, never a note under Details | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | B7 |
| P126 | patrol never runs intake for the user beyond the protocol | `commands/patrol.md` | `prose-only` | prose | semantic — whether an act is beyond the protocol is a reading of it |
| P127 | On anything unexpected patrol stops and reports, never improvises | `commands/patrol.md` | `prose-only` | prose | semantic — whether an act is an improvisation is a reading of it against the command |
| P128 | The next sequence is one past the highest, never one past the count | `references/branch-names.md` · `references/next-stage-path-c.md` · `references/next-stage-path-a.md` | `guarded-by-case` | references/branch-names.md | C31 |
| P129 | An invalid `branch_template` is fixed with `/roz-gate:config`, never by a command | `references/branch-names.md` | `prose-only` | prose | unguarded — a replay case with an invalid `branch_template`: the STOP comment names the config command and the local file is unchanged |
| P131 | A name collision before a cut is a STOP naming the branch, never a silent bump of the sequence | `references/branch-names.md` · `references/next-stage-path-c.md` · `references/next-stage-path-a.md` | `prose-only` | prose | unguarded — a replay case whose expanded name already exists on the remote: STOP, and no branch with a bumped sequence is cut (C31 holds the prose; C11 covers the legitimate next sequence) |
| P132 | Two live matches of different kinds are an ambiguity a command must not resolve — it STOPs naming both | `references/branch-names.md` | `prose-only` | prose | unguarded — a replay case whose Lookup returns two branches of different kinds for one issue: STOP naming both, nothing bound |
| P133 | A head that survives only in merged-CR history is a CR's name, never a branch — nothing checks it out, reads it or cuts from it | `references/branch-names.md` | `guarded-by-case` | references/branch-names.md | A11 |
| P134 | The scanner binds branch names through `bin/roz-branch match`, never by matching the template itself | `references/branch-names.md` · `references/patrol-scan.md` | `guarded-by-case` | references/branch-names.md | L4, C31 |
| P135 | The commands never repeat the commit rules — `commit-brief.md` is their only home | `references/commit-brief.md` | `guarded-by-case` | references/commit-brief.md | L3 |
| P136 | The commit sub-agent works in the one worktree the dispatch names, never another | `references/commit-brief.md` | `prose-only` | prose | unguarded — a replay case with two loop worktrees present: the commit lands in the named one only |
| P137 | The commit sub-agent never stages a path outside the dispatch's file list | `references/commit-brief.md` | `prose-only` | prose | unguarded — a replay case whose worktree holds a stray untracked file: the commit carries the listed files only |
| P138 | The commit sub-agent never rewords the commit message | `references/commit-brief.md` | `prose-only` | prose | unguarded — a replay case comparing the dispatched message with the commit's |
| P139 | The commit sub-agent never retries a failed commit more than once | `references/commit-brief.md` | `prose-only` | prose | unguarded — a replay case with a pre-commit hook that always fails: at most two commit attempts |
| P140 | The commit sub-agent never widens the file list to make a hook pass | `references/commit-brief.md` | `prose-only` | prose | unguarded — the same replay case: the staged set never grows beyond the dispatched list |
| P141 | The commit sub-agent never `--no-verify`s a failure that names a file in its list | `references/commit-brief.md` | `prose-only` | prose | unguarded — a replay case whose hook fails on a listed file: no `--no-verify` commit follows |
| P142 | A `gh` call never passes `--repo` — the repository is the current directory's remote | `references/forge-github.md` | `deterministic-candidate` | none yet | — |
| P143 | The bot token is passed per invocation, never exported into the session environment | `references/forge-github.md` · `references/forge-gitlab.md` · `references/identity-github-app.md` | `deterministic-candidate` | none yet | — |
| P144 | In bot mode an issue is never created without an assignee — a bot-authored issue is never born holder-less | `references/forge-github.md` · `references/forge-gitlab.md` | `deterministic-candidate` | none yet | — |
| P145 | The bot's git identity is given per command, never written into the repository's git config | `references/forge-github.md` · `references/forge-gitlab.md` | `deterministic-candidate` | none yet | — |
| P146 | A failed blockers read is a failed read, never "no blockers" | `references/forge-github.md` · `references/forge-gitlab.md` · `references/workflow.md` · `references/roz-state.md` | `guarded-by-case` | references/patrol-scan.md | F15 |
| P147 | The loop never writes an issue relationship — blockers are read-only | `references/forge-github.md` · `references/forge-gitlab.md` · `references/workflow.md` · `references/patrol-scan.md` | `guarded-by-case` | references/patrol-scan.md | F15 |
| P148 | In bot mode the `{user}` slot is the first `bot_login`, never a forge call | `references/forge-github.md` · `references/forge-gitlab.md` | `prose-only` | prose | unguarded — a replay case in bot mode that cuts a branch: no WHOAMI call in the journal |
| P149 | A command never merges a CR on the forge — CR-MERGE is the human's act at (7) | `references/forge-github.md` · `references/forge-gitlab.md` | `deterministic-candidate` | none yet | — |
| P150 | The fidelity audit gives cited evidence, never a verdict | `references/workflow.md` · `references/fidelity-brief.md` · `references/next-stage-path-b2.md` | `prose-only` | prose | semantic — whether a finding is evidence or a verdict is a reading of it |
| P151 | A dispatched seat never searches for plugin files — the dispatch names the plugin root | `references/workflow.md` | `guarded-by-case` | references/workflow.md | D28 — hook L (D29) is a supporting boundary: a seat dispatch without the `Plugin root:` line is denied; it does not stop a seat that has the line from searching |
| P152 | A persona is swappable; the seat's contract never is | `references/workflow.md` | `guarded-by-case` | references/workflow.md | D25 |
| P153 | A failed seat resolve, or a spawn the runtime refuses, is the STOP exit — never another agent | `references/workflow.md` | `guarded-by-case` | references/workflow.md | D26, L22 |
| P154 | A seat's question is moved into `spec.md`'s Open Questions, never copied | `references/workflow.md` · `references/next-stage-path-a.md` | `guarded-by-case` | references/workflow.md | E2 — hook D is a supporting boundary: a commit while `technical-spec.md` still carries an open-questions heading is refused; a question left elsewhere is not seen |
| P155 | An as-built change to what a rule means takes the backward transition, never a silent edit | `references/workflow.md` | `prose-only` | prose | semantic — whether an as-built correction changes what a rule means is a reading of the diff against the spec |
| P156 | QA tests through the port, never through the persistence layer or an implementation import beyond the port's declared types | `references/workflow.md` · `references/qa-brief.md` | `guarded-by-case` | references/qa-brief.md | B8 — hook E is a supporting boundary (no read of the implementation during the dispatch) |
| P157 | QA or the implementer hitting a contract ambiguity mid-flight never interprets it — it stops and reports | `references/workflow.md` | `prose-only` | prose | semantic — whether a choice was an interpretation of an ambiguous clause is a reading |
| P158 | QA or the implementer hitting a contract ambiguity never decides it unilaterally in code | `references/workflow.md` · `references/next-stage-path-b.md` | `prose-only` | prose | semantic — whether code settles an ambiguity is a reading of it against the contract |
| P159 | A review finding that is really a contract ambiguity is never settled on the implementation CR | `references/workflow.md` · `references/next-stage-path-b.md` | `prose-only` | prose | semantic — whether a finding is a contract ambiguity is a reading of it |
| P160 | The loop's `git worktree add` runs alone, from inside the repository — never as `git -C <dir>` | `references/workflow.md` | `deterministic-candidate` | none yet | — — hook J is a supporting boundary: it denies the add when anything is chained to it, not the `-C` spelling on its own |
| P161 | A gate label a bot identity applied is an illegal state — reported, never acted on, never repaired | `references/workflow.md` · `references/patrol-scan.md` | `guarded-by-case` | references/patrol-scan.md | C24, F13 |
| P162 | A dependency missing from the base is a STOP, never an option a command offers or takes | `references/workflow.md` | `guarded-by-case` | references/workflow.md | C29 |
| P163 | Code the spec asks this issue to build, or scope beyond the issue, is a scope question on the spec CR, never the missing-dependency STOP | `references/workflow.md` · `references/next-stage-path-a.md` | `guarded-by-case` | references/workflow.md | C29 |
| P164 | A Given with no control point is a contract defect QA reports, never works around | `references/workflow.md` · `references/qa-brief.md` | `guarded-by-case` | references/qa-brief.md | D22 |
| P165 | "The port is the API" never becomes "the port is always HTTP" | `references/workflow.md` | `guarded-by-case` | references/workflow.md | B8 |
| P166 | A port that under-exposes a promised observation point is a defect QA reports — never worked around, never silently downgraded to `uncovered` | `references/workflow.md` · `references/qa-brief.md` | `prose-only` | prose | unguarded — D22's sibling on an observation point: a scenario whose promised observation the port does not expose is a finding, and `test-spec.md` does not mark it `uncovered` without one |
| P167 | A shared fact has one home — seats read it there and never re-decide it | `references/workflow.md` | `prose-only` | prose | semantic — whether a seat re-decided a fact its home already states is a reading of its deliverable |
| P168 | QA never reads the implementation during its dispatch | `references/workflow.md` · `references/qa-brief.md` · `references/next-stage-path-b2.md` | `hooked` | hook E | `hooks/tests/test_guard_blind.py::RuleE_QaDispatchSeat` |
| P169 | The scanner never re-derives the values the main agent handed it (the inbox filter, `default_branch`) | `references/patrol-scan.md` | `prose-only` | prose | unguarded — a replay pass asserting the scanner makes no `roz-config` call and no read of the local file |
| P170 | A track-less issue outside the inbox filter is never commented on, never locked, never listed as waiting — only counted | `references/patrol-scan.md` | `guarded-by-case` | references/patrol-scan.md | F11 — F11 asserts the filtered-out issue has no row; that it is neither commented on nor locked is asserted there only as the absence of a queue item |
| P171 | A gate label on a stage that already passed is an illegal state — reported, never repaired, never routed | `references/patrol-scan.md` | `guarded-by-case` | references/patrol-scan.md | C27, F14 |
| P172 | A blocker is the forge's own relationship, never a `Blocked by` line in a body or a spec | `references/patrol-scan.md` | `guarded-by-case` | references/patrol-scan.md | F15 |
| P173 | Nothing is re-invoked on an issue wearing `status: blocked` — it waits on the user | `references/patrol-scan.md` | `prose-only` | prose | unguarded — a replay pass over a `status: blocked` issue: its row is `blocked:` with `needs you: yes`, and no dispatch or write names it |
| P174 | Intake captures intent — never binding terms (scenarios, schemas, guarantees) | `references/intake-brief.md` | `prose-only` | prose | semantic — whether a sentence of the story binds a term is a reading of it |
| P175 | Live intake returns the single most important question, never a list | `references/intake-brief.md` | `prose-only` | prose | unguarded — a replay case on to-issues (live mode): each seat return carries one question |
| P176 | A question's options are one bullet each, never prose | `references/intake-brief.md` · `references/next-stage-path-a.md` | `hooked` | hook F | `hooks/tests/test_guard_gate.py::RuleF_QuestionOptionsAreBullets` |
| P177 | Acceptance criteria are observable and testable, never implementation tasks | `references/intake-brief.md` | `prose-only` | prose | semantic — whether a criterion is an observable outcome or a task is a reading of it |
| P178 | The intake seat never resolves a disagreement between commenters — it carries both sides and names the summary's choice as a recommendation | `references/intake-brief.md` | `prose-only` | prose | authority — settling a disagreement is the gate holder's; whether a summary settled one is a reading of it |
| P179 | In an intake reply an answer from anyone but the gate holder is recorded as input, never as settled | `references/intake-brief.md` | `prose-only` | prose | authority — only the gate holder's label decides; whether a reply presents an answer as settled is a reading of it |
| P180 | One issue is one story — never split into parent/child, tasks, layers or implementation slices at intake | `references/intake-brief.md` | `prose-only` | prose | semantic — whether a set of stories is a split by layer or task is a reading of them |
| P181 | Intake captures what and why, never how | `references/intake-brief.md` | `prose-only` | prose | semantic — whether a sentence of the story states how is a reading of it |
| P182 | The intake seat drives toward the smallest story — shrink, don't grow | `references/intake-brief.md` | `prose-only` | prose | persona — how the seat scopes; what counts as growing is its judgment |
| P183 | The intake seat does not gold-plate the clarification — good enough to gate is the bar | `references/intake-brief.md` | `prose-only` | prose | persona — how the seat interrogates; what counts as gold-plating is its judgment |
| P184 | An intake batch never holds more than five questions | `references/intake-brief.md` | `deterministic-candidate` | none yet | — |
| P185 | The proposed track is never treated as decided — the human confirms or overrides it | `references/intake-brief.md` | `prose-only` | prose | authority — the track is the human's to confirm |
| P186 | The gate kit is never posted into a review thread — it is a top-level comment on the spec CR | `references/gate-kit.md` | `deterministic-candidate` | none yet | — |
| P187 | The gate kit quotes, never paraphrases | `references/gate-kit.md` | `prose-only` | prose | semantic — whether a line is a verbatim excerpt of its source or a paraphrase needs the source read against it |
| P188 | The gate kit sorts its items, never filters them | `references/gate-kit.md` | `prose-only` | prose | unguarded — a replay case whose kit is compared with the spec: every rule and scenario id appears in it |
| P189 | The kit's sort is on computed properties only, never the assembler's confidence | `references/gate-kit.md` | `prose-only` | prose | semantic — what an ordering was based on is not visible in the output |
| P190 | The word "mechanical" never appears in the gate kit | `references/gate-kit.md` | `deterministic-candidate` | none yet | — |
| P191 | A verdict exemption (an observability limitation) is never granted by the implementer — it stands once the holder has seen it in the kit | `references/gate-kit.md` · `references/next-stage-path-a.md` | `prose-only` | prose | authority — exempting a scenario from the verdict is the holder's |
| P192 | An evidence card's observation slot holds what the run emitted, never the expectation restated | `references/gate-kit.md` | `prose-only` | prose | semantic — whether a card's observation is the run's output or the expectation reworded needs the captured output read against it |
| P193 | "The spec you approved is byte-identical" never appears alone when non-spec paths moved | `references/gate-kit.md` | `prose-only` | prose | unguarded — a replay re-verdict in which only non-spec paths moved since approval: the kit's since-you-approved line names the commits beside the claim |
| P194 | The §5 observability map is a claim QA verifies against the port, never a fact it inherits | `references/qa-brief.md` | `guarded-by-case` | references/qa-brief.md | D22 |
| P195 | QA never writes a unit test — its level is the port | `references/qa-brief.md` | `guarded-by-case` | references/qa-brief.md | B8 |
| P196 | The QA seat never posts to the forge — its findings are returned and the main agent posts them | `references/qa-brief.md` | `guarded-by-case` | references/workflow.md | E9 |
| P197 | The QA seat never touches the implementation branch or the spec branch | `references/qa-brief.md` | `prose-only` | prose | unguarded — a QA-frame replay assertion that the remote's implementation and spec refs are unchanged by the dispatch — hook E is a supporting boundary: during the dispatch a git action on the implementation ref is denied; the spec branch is not covered |
| P198 | The fidelity reviewer never reads the implementation | `references/fidelity-brief.md` | `hooked` | hook E | `hooks/tests/test_guard_blind.py::RuleE_FidelityDispatchIsBlind` |
| P199 | A fidelity dispatch never continues a context that has seen the implementation | `references/fidelity-brief.md` · `references/next-stage-path-b2.md` | `prose-only` | prose | unguarded — a replay assertion that the fidelity dispatch is a fresh agent, not a continuation of the code reviewer's |
| P200 | The blind fidelity reviewer never opens the implementation CR's threads | `references/fidelity-brief.md` · `references/next-stage-path-b2.md` | `guarded-by-case` | references/fidelity-brief.md | D6 |
| P201 | Mapping defects are an itemized list, never folded into the fidelity count | `references/fidelity-brief.md` | `prose-only` | prose | unguarded — a replay fidelity audit seeded with a mapping defect: the summary lists it apart from the count |
| P202 | A fidelity finding is a new thread, never posted into an existing unresolved thread | `references/fidelity-brief.md` | `prose-only` | prose | unguarded — C17's seed with an open thread on the QA CR: the audit's findings are new threads and the open one gains no reply |
| P203 | A scenario that is not assertable as written is a spec finding reported to the main agent, not routed to QA | `references/fidelity-brief.md` | `prose-only` | prose | semantic — whether a finding is a test defect or a spec defect is a reading of it |
| P204 | A scenario-meaning dispute is a spec ambiguity — never settled reviewer-to-QA on the QA CR | `references/fidelity-brief.md` | `prose-only` | prose | semantic — whether a finding is a dispute about a scenario's meaning is a reading of it |
| P205 | At the reserved-word STOP each row is decided on its own, never one action for all | `references/next-stage-path-b.md` | `guarded-by-case` | references/next-stage-path-b.md | B10 |
| P206 | A rule or contract line born from a deferred item carries `(assumed)`, never `(from Q<k>)` | `references/next-stage-path-b.md` | `guarded-by-case` | references/next-stage-path-b.md | E11 |
| P207 | The code reviewer reviews against the claim it is handed, never against its own inference of intent | `references/next-stage-path-b.md` | `guarded-by-case` | references/next-stage-path-b.md | D1 |
| P208 | A branch is cut only from a base the remote has — never from anything else | `references/next-stage-path-c.md` · `references/next-stage-path-a.md` | `guarded-by-case` | references/branch-names.md | C7 |
| P209 | The spec's rule enumeration is the content itself in numbered form, never a second prose copy | `references/next-stage-path-a.md` | `prose-only` | prose | semantic — whether a passage restates the numbered rules is a reading of the document |
| P210 | A reserved word loose in a sentence is reworded, never waved through as a false positive | `references/next-stage-path-a.md` · `references/reserved-words.md` | `guarded-by-case` | references/reserved-words.md | B6, B10 |
| P211 | Accepting a risk is never evidence for an empirical premise | `references/next-stage-path-a.md` | `prose-only` | prose | semantic — whether a tag claims evidence the spec does not have is a reading of the premise and its tag |
| P212 | The supplement fold changes placement, never the shapes the hooks and checkers parse (headings, IDs, tags, the §5 table) | `references/next-stage-path-a.md` | `prose-only` | prose | unguarded — a replay spec refinement whose documents are parsed afterwards: every heading, id, tag and the §5 table are in their exact shapes |
| P213 | A Glossary definition a seat finds insufficient or contradicted goes through that seat's channel, never settled locally | `references/next-stage-path-a.md` | `guarded-by-case` | references/next-stage-path-a.md | D24 — D24's replay half asserts it for QA; for the implementer only the lint anchor holds the sentence |
| P214 | Review guidance or a note for QA is a rule or a note under its rule, never a scenario | `references/next-stage-path-a.md` | `prose-only` | prose | semantic — whether a scenario is falsifiable behaviour or guidance is a reading of it |
| P216 | In a comment, thread or report the first mention of an ID is written in full with its link, never the bare code | `references/next-stage-path-a.md` | `prose-only` | prose | unguarded — a replay assertion over posted comments: the first occurrence of each `R<k>` / `S<k>` / `C<k>` carries its title and a link |
| P217 | A gate-kit update edits the kit's one comment in place, never posts a sibling | `references/next-stage-path-a.md` | `prose-only` | prose | unguarded — a replay re-verdict or spec-answers run: the spec CR carries exactly one kit comment afterwards |
| P218 | Path A writes the two spec documents and never code | `references/next-stage-path-a.md` | `prose-only` | prose | unguarded — F3's seed with an assertion that the spec branch's diff against its base touches only `<specs_dir>/<n>/` |
| P219 | With a contract question still unsettled, QA is not dispatched — the question routes to the spec CR first | `references/next-stage-path-b2.md` | `guarded-by-case` | references/next-stage-path-b2.md | D6 |
| P220 | QA never opens the implementation CR — the as-built changes reach it as the dispatch's copy | `references/next-stage-path-b2.md` | `prose-only` | prose | unguarded — a QA-frame replay assertion that no tool call under the dispatch names the implementation CR (D6 asserts it for the fidelity dispatch) |
| P221 | The blind dispatch's worktrees are removed after the marker is gone, never while it is on | `references/next-stage-path-b2.md` | `deterministic-candidate` | none yet | — |
| P222 | The audited party never closes the audit's findings — the reviewer re-checks and resolves them | `references/next-stage-path-b2.md` | `prose-only` | prose | unguarded — a replay address-review on a QA CR with fidelity threads: each thread is resolved under a `reviewer` dispatch, not a `qa` one |
| P223 | An unknown fact neither satisfies nor refutes a precondition — a consumer never reads it as `0`, `false` or empty | `references/roz-state.md` | `prose-only` | prose | unguarded — a lint over the commands' preconditions needs a parseable precondition form; `hooks/tests/` hold it for `roz-check` only — `roz-check` implements the invariant in code for the operations it knows (`unknown` → `may_start: false`) |
| P224 | A STOP message or a later audit reads why a rule came out as it did from the check result, never reconstructs it | `references/roz-check.md` | `prose-only` | prose | unguarded — a replay STOP after a failed check: the comment's reason matches the result's `failed` codes |
| P225 | A caller of `roz-check` reads `verdict`, `may_start`, `failed` and `unknown` — codes, never the prose | `references/roz-check.md` | `prose-only` | prose | unguarded — no command consumes `roz-check` yet (shadow mode); the guard is a lint on the consuming step once one does |
| P226 | Creating the bot's credentials is the human's task — a command never automates a step of it | `references/identity-github-app.md` | `prose-only` | prose | authority — credentials are the human's to create; no case observes a command attempting it |
| P227 | The bot credential is never written into git config or any repository file | `references/identity-github-app.md` | `prose-only` | prose | unguarded — a replay case in bot mode: no file in the work tree and no git config value holds the token after the run |

**Not a rule** — a prohibition word that forbids an agent nothing. One row per reason; every fragment is listed, none is matched by pattern.

| id | reason | fragments |
|---|---|---|
| P007 | states a fact or the persona's stance; forbids no act | `agents/qa.md` “You do not care how elegant the code is” · `agents/reviewer.md` “The author cannot see their own blind spots” · `commands/config.md` “this prompt never runs” · `commands/config.md` “seats are never configured” · `commands/init.md` “routine plugin upgrades never demand a re-init” · `commands/uninit.md` “don't block retirement” · `commands/uninit.md` “a plugin command cannot uninstall its own plugin” · `commands/integrate.md` “the user's checkout was never touched” · `commands/review-answers.md` “report what never landed” · `commands/tip.md` “the close-out never ran” · `commands/tip.md` “it was never gated” · `commands/spec-answers.md` “was never read” · `commands/spec-answers.md` “they do not hold the issue” · `commands/spec-answers.md` “the user's checkout was never touched” · `commands/patrol.md` “It never changes the model this command itself runs on” · `commands/patrol.md` “the review that never ran” · `commands/patrol.md` “(or never re-checked)” · `commands/patrol.md` “the audit that never ran” · `references/branch-names.md` “never asks about the CR” · `references/branch-names.md` “the adapter ops do not change” · `references/workflow.md` “the workflow's vocabulary never changes” · `references/workflow.md` “the review that never ran, or re-runs” · `references/workflow.md` “Your three options do not change” · `references/workflow.md` “do not wait for you to type them” · `references/patrol-scan.md` “the review never ran, or” · `references/patrol-scan.md` “never re-checked the head” · `references/patrol-scan.md` “the audit never ran. Implementation CR” · `references/intake-brief.md` “the summary was never requested” · `references/gate-kit.md` “in the holder's name they never made” · `references/gate-kit.md` “never threaded; its recommendation” · `references/fidelity-brief.md` “in a branch never entered” · `references/next-stage-path-b.md` “it never sees the user's checkout” · `references/next-stage-path-b2.md` “Path B never ran” · `references/next-stage-path-b2.md` “when B2.7 never did” |
| P008 | a condition — what to do when something cannot be done — not a prohibition | `agents/reviewer.md` “If you cannot explain why a line is correct” · `templates/implementer.md` “a definition you cannot build to is a question” · `commands/next-stage.md` “anything this command cannot or should not decide” · `commands/integrate.md` “A local ref that cannot fast-forward” · `commands/review-answers.md` “Anything you cannot read as a clear yes” · `commands/spec-answers.md` “On anything this command cannot or should not decide” · `commands/patrol.md` “A row you cannot act on as written” · `commands/patrol.md` “A row the pass cannot act on as written” · `references/commit-brief.md` “a hook you cannot read” · `references/commit-brief.md` “a failure you cannot classify” · `references/workflow.md` “it hit something it cannot or should not decide” · `references/qa-brief.md` “you cannot drive it” · `references/fidelity-brief.md` “cannot be ordered to produce” · `references/next-stage-path-b.md` “A contract gap you cannot resolve” · `references/next-stage-path-b2.md` “a ref that cannot fast-forward” |
| P009 | example text inside the implementer template's commented-out stack block, which the project replaces with its own | `templates/implementer.md` “Raw SQL only when the ORM cannot express it cleanly” |
| P010 | addressed to the human who fills in the template, not to an agent | `templates/claude-workflow.md` “the seat names never change” · `templates/idea.md` “Don't add labels” |
| P011 | describes another seat's or command's rule to the reader (the rule is stated to its owner elsewhere); forbids the reader nothing | `templates/implementer.md` “QA never touches the persistence layer” · `commands/tip.md` “patrol never re-invokes anything on `blocked`” · `commands/spec-answers.md` “qa never writes spec text” · `references/branch-names.md` “A reader that may not run git” · `references/next-stage-path-b.md` “QA never persists entities or touches the persistence layer, so a Given” |
| P029 | says where a value lives or what state a file is in (a local key is per person and not committed); forbids no act | `commands/config.md` “per person, per clone, never committed” · `commands/init.md` “(`.claude/roz-gate.local.json`, never committed). Say so” · `commands/init.md` “(`.claude/roz-gate.local.json`, never committed; the write” · `commands/next-stage.md` “are per person, per clone, never in the block” · `commands/integrate.md` “are per person, per clone, never in the block” · `commands/review-answers.md` “are per person, per clone, never in the block” · `commands/spec-answers.md` “are per person, per clone, never in the block” · `commands/patrol.md` “are per person, per clone, never in the block” · `references/workflow.md` “`.claude/roz-gate.local.json`, never committed; default: the remote's HEAD” · `references/reserved-words.md` “A candidate is never listed” |
| P031 | describes a value the tool refuses (`bin/roz-config` validates it); the prose forbids the agent nothing | `commands/config.md` “never a directory or a `.gitignore`” |
| P040 | the word is part of a name — the R&R table's `Never` column, the kit's `cannot-be-covered-black-box` bucket | `commands/init.md` “R&R row (Owns / Never)” · `commands/init.md` “Text that fights the Never column” · `commands/integrate.md` “cannot-be-covered-black-box” · `references/branch-names.md` “the forbidden implementation ref” · `references/workflow.md` “\| Role \| Owns \| Never \|” · `references/workflow.md` “its R&R row above (Owns / Never)” · `references/workflow.md` “fights its seat's Never column” · `references/gate-kit.md` “cannot-be-covered-black-box” · `references/fidelity-brief.md` “**Cannot fail given the port**” · `references/next-stage-path-b2.md` “"you never read the implementation" stays in the dispatch text” · `references/roz-state.md` “### Never a fact” · `references/roz-check.md` “§ Never a fact” · `references/roz-check.md` “## What it never decides” |
| P046 | defines a term by what it is not; forbids no act | `commands/next-stage.md` “(never code this issue would build)” · `commands/integrate.md` “never reached its assertion” · `commands/tip.md` “(never `spec` + `ready-for-dev`” · `commands/spec-answers.md` “(never code this spec asks for)” · `references/patrol-scan.md` “`track: fast` never with a spec-stage status” · `references/qa-brief.md` “never reached its assertion” · `references/roz-state.md` “this forge or this version cannot answer” |
| P056 | states a fact given as the reason for a neighbouring rule; forbids no act | `commands/integrate.md` “a feature-scoped run cannot see (a sync” · `commands/integrate.md` “this command never moves the local ref” · `commands/integrate.md` “exactly the code a feature-scoped run cannot see” · `commands/review-answers.md` “a reaction cannot select which” · `commands/tip.md` “This command cannot tell a live lock from a stale one” · `commands/spec-answers.md` “the item itself never changes” · `commands/spec-answers.md` “the two axes never share a tag” · `commands/patrol.md` “never queues behind machine work” · `commands/patrol.md` “must not starve the rest of the loop” · `commands/patrol.md` “so a quiet inbox is never a mystery” · `commands/patrol.md` “so it never *newly* enters anything” · `references/branch-names.md` “they never coexist for one issue” · `references/branch-names.md` “cannot compute its name” · `references/branch-names.md` “it cannot tell a spec branch from a qa branch” · `references/workflow.md` “(Bash never sets it)” · `references/workflow.md` “the loop never moves the local ref” · `references/workflow.md` “never the main agent's, for the same reason” · `references/workflow.md` “a foreign agent it cannot reach” · `references/workflow.md` “the human cannot see that cost” · `references/workflow.md` “three reasons that do not depend on timing” · `references/patrol-scan.md` “an `UNKNOWN` snapshot cannot reach you” · `references/patrol-scan.md` “so the main agent never re-lists for assignees” · `references/gate-kit.md` “never a replacement for opening them” · `references/gate-kit.md` “cannot reveal drift from the *ask*” · `references/qa-brief.md` “their comments quote the code you must not see” · `references/fidelity-brief.md` “their comments quote the code you must not see” · `references/next-stage-path-b.md` “the acceptance run never produces” · `references/next-stage-path-b.md` “the decision never reaches the ledger” · `references/next-stage-path-c.md` “cannot block it” · `references/next-stage-path-a.md` “cannot block it” · `references/next-stage-path-a.md` “cannot be cited, audited, or kept current” · `references/next-stage-path-a.md` “must not share its authority” · `references/next-stage-path-a.md` “they never compete for the same clause” · `references/next-stage-path-a.md` “a checker cannot fully parse” · `references/next-stage-path-a.md` “a reader who does not never scrolls past it” · `references/next-stage-path-b2.md` “its threads quote the code QA must not see” · `references/next-stage-path-b2.md` “the code the reviewer must not see” |
| P130 | describes what a `bin/` tool or a hook does or refuses — code, tested in `hooks/tests/`; the prose forbids the agent nothing | `references/branch-names.md` “Expand never computes the sequence itself” · `references/branch-names.md` “never a precondition of a live head” · `references/branch-names.md` “never from wherever the forge CLI resolves by default” · `references/branch-names.md` “it never creates, deletes, checks out or moves a branch” · `references/branch-names.md` “it never chooses the live attempt or the next sequence” · `references/branch-names.md` “a failed history read never makes it `unknown`” · `references/branch-names.md` “never the session's cwd” · `references/workflow.md` “never overwriting” · `references/workflow.md` “never written back (#122)” · `references/next-stage-path-a.md` “is a *present* tag, never read as absent” · `references/roz-state.md` “It never answers "what should Roz Gate do next?"” · `references/roz-state.md` “is never an "additive field"” · `references/roz-state.md` “A thread count is never absent under an observed CR” · `references/roz-state.md` “`dependencies.blocked_by` is never absent at all” · `references/roz-state.md` “it is never evidence that a snapshot became semantically invalid” · `references/roz-state.md` “never the whole block” · `references/roz-state.md` “never does today” · `references/roz-state.md` “A defect in the tool, never an observation” · `references/roz-state.md` “never reported as `unsupported`” · `references/roz-state.md` “never the CLI's” · `references/roz-state.md` “never absent; a live head is unaffected” · `references/roz-state.md` “never through `roz-config`” · `references/roz-state.md` “never expands a template or matches a head itself” · `references/roz-state.md` “are never compared here” · `references/roz-check.md` “It never runs the operation” · `references/roz-check.md` “never a second failure or a second unknown” · `references/roz-check.md` “the operation must not start” · `references/roz-check.md` “it never checks a spec CR at entry” · `references/roz-check.md` “counted, never ignored” |
| P215 | example text — a sample rule, comment or sentence shown to illustrate a shape; forbids no act | `references/next-stage-path-a.md` “Expired offers don't count” |
<!-- /prohibitions -->

## Unguarded executable prose

Sections of at least 80 words that no lint literal lies inside and no replay
`check.py` cites in a `source:` line (computed when this page was written;
re-run by hand). Persona sections are expected here — they are semantic by
nature. The rest wait for a case or a reason.
Sentences that forbid something are classified one by one under *Prohibitions*.

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
