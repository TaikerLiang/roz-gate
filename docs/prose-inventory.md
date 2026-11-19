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
| `deterministic-candidate` | files, git and one call's input could decide it, and nothing does. Its issue chooses the owner, red first, in this order: the architecture removes the invalid choice · a generator produces the value · `roz-check` verifies it · a hook denies it · it stays prose (#352, #354: push a failure down the trust stack; eliminate before denying) | `none yet` | the follow-up issue |
| `guarded-by-case` | a lint, replay or judgment case asserts this prohibition — not a neighbouring one | the prose or kernel rule that owns it | ledger ids |
| `prose-only` | nothing enforces it. The reason says why: `semantic`, `persona`, `authority` — or `unguarded — <what would guard it>`, a gap recorded as a gap | `prose` | — |
| `not-a-rule` | the word forbids an agent nothing: a fact, a condition, another seat's rule described, a line addressed to the human | — | — |

Where a prohibition could be both, the stronger claim on enforcement wins:
`hooked`, then `deterministic-candidate`, then `guarded-by-case`.

**What the lint cannot see.** A prohibition spelled with none of these
words ("no force-push", "is not yours to …"); whether a class is right;
whether the evidence is enough. Those are review. Sections no case touches
at all are listed under *Unguarded executable prose*, by section — a
different unit, kept apart.

<!-- prohibitions -->
Scope: `agents/`, `commands/`, `templates/` — 17 files, 208 prohibition words, each inside one quote of one row.

| class | rules | sources |
|---|---|---|
| `hooked` | 4 | 9 |
| `deterministic-candidate` | 6 | 8 |
| `guarded-by-case` | 42 | 62 |
| `prose-only` | 65 | 70 |
| `not-a-rule` (reasons) | 10 | 59 |

Of the `prose-only` rules, **40 are `unguarded`** — not semantic, and nothing enforces them yet.

| id | rule | stated in | class | owner | evidence / reason |
|---|---|---|---|---|---|
| P001 | Dispatched with no one to ask, a spec seat never waits for an answer — it returns its open questions with the deliverable | `agents/em.md` · `agents/product.md` | `prose-only` | prose | unguarded — a replay case in which a dispatched seat holds an open question and must return it rather than end its turn asking (E2 guards where a returned question lands, not that the seat returns it) |
| P002 | A dispatched spec seat never silently assumes an answer to an open question | `agents/em.md` · `agents/product.md` | `prose-only` | prose | semantic — whether a choice was an assumption is a reading of the deliverable against the spec |
| P003 | A seat folding an answer never posts its follow-up question to the forge itself — the main agent posts or defers it | `agents/em.md` · `agents/product.md` | `deterministic-candidate` | none yet | #391 |
| P004 | em never accepts a vague answer to a requirement | `agents/em.md` | `prose-only` | prose | persona — how the seat interrogates; what counts as vague is its judgment |
| P005 | product never accepts a happy-path-only answer | `agents/product.md` | `prose-only` | prose | persona — how the seat interrogates; what counts as happy-path-only is its judgment |
| P006 | A spec seat never offers merging, rebasing onto or cherry-picking from another branch as an option — it reports the missing dependency | `agents/em.md` · `agents/product.md` | `guarded-by-case` | references/workflow.md | C29 |
| P012 | QA never resolves an ambiguity in the spec by interpretation — an ambiguity is a finding it reports | `agents/qa.md` | `guarded-by-case` | references/qa-brief.md | D24, E14 |
| P013 | QA tests against the contract, never the raw implementation | `agents/qa.md` | `guarded-by-case` | references/qa-brief.md | B8, D9, D10, D13 — hook E is a supporting operational boundary (no read of the implementation during the dispatch), not this rule's owner: a seat can obey E and still assert what it observed |
| P014 | The acceptance tests are a maintained suite, never write-once snapshots | `agents/qa.md` | `prose-only` | prose | semantic — whether a suite is maintained or a snapshot is a reading of how it was written |
| P015 | QA never flags a project-sanctioned test layout as a violation | `agents/qa.md` | `prose-only` | prose | semantic — whether a finding is about the layout is a reading of the finding |
| P016 | `test-spec.md`'s scenario→test map is derived from the trace markers in the test source, never hand-maintained | `agents/qa.md` | `deterministic-candidate` | none yet | #392 |
| P017 | A QA red is a harness issue fixed or a finding reported, never an edited assertion (QA-4) | `agents/qa.md` | `guarded-by-case` | kernel QA-4 (`references/qa-brief.md`) | B8, D9, D13 |
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
| P028 | The config command never edits `.claude/roz-gate.local.json`, `CLAUDE.md` or `CLAUDE.local.md` itself — `bin/roz-config` does the write | `commands/config.md` | `deterministic-candidate` | none yet | — |
| P030 | A multi-value config key is passed one value per quoted argument, never split on spaces | `commands/config.md` | `prose-only` | prose | unguarded — a replay case on `/roz-gate:config` setting `inbox_label` to a label that holds a space |
| P032 | An agent never applies a gate label (`ready-for-spec`, `ready-for-dev`) — the gate is the human's | `commands/config.md` · `commands/to-issues.md` · `commands/spec-answers.md` · `commands/patrol.md` | `hooked` | hook B | `hooks/tests/test_guard_gate.py::RuleB_GateLabelsAreHumanOnly` |
| P033 | The config command never creates forge labels | `commands/config.md` | `prose-only` | prose | unguarded — a replay case on `/roz-gate:config` whose forge journal holds no label-create call |
| P034 | init says, where it asks for `test` and `acceptance_test`, that they run in a linked worktree, never in the checkout | `commands/init.md` | `guarded-by-case` | references/workflow.md | L6 |
| P035 | init never automates the bot credential's creation — it points the user at the one-time setup | `commands/init.md` | `prose-only` | prose | authority — creating a credential is the human's act |
| P036 | On GitLab the `processing` lock label is created plain, never scoped — it must coexist with a phase label | `commands/init.md` | `prose-only` | prose | unguarded — a lint on init's GitLab label list, or a replay of init on GitLab whose journal creates `processing` unscoped (C3 checks label coexistence, not how init creates the label) |
| P037 | A `type:` label is never a gate — no command applies, removes, validates or dispatches on one | `commands/init.md` | `prose-only` | prose | unguarded — a replay case in which an issue carries a `type:` label and no gate label: nothing is dispatched |
| P038 | init never copies the workflow prose into the project's `CLAUDE.md` — only the pointer and the config block | `commands/init.md` | `prose-only` | prose | unguarded — a replay case on init whose resulting `CLAUDE.md` section is the template's pointer and block and nothing from `references/workflow.md` |
| P039 | init never copies, moves or renames a user's agent file when it links a seat | `commands/init.md` | `prose-only` | prose | unguarded — a replay case on init linking a seat: the user's agent file is byte-identical and in place afterwards |
| P041 | init never links a persona that fails the seat's contract check without showing the violating lines | `commands/init.md` | `prose-only` | prose | semantic — whether a persona's text fights the seat's Never column is a reading of that text |
| P042 | init never edits an existing `CLAUDE.md` section without showing the change first | `commands/init.md` | `prose-only` | prose | unguarded — a replay case on init over a project that already has the section: the change is shown before any write to `CLAUDE.md` |
| P043 | A command's git work runs in a linked worktree, never in the user's checkout | `commands/next-stage.md` · `commands/patrol.md` | `guarded-by-case` | references/workflow.md | C9, F8 |
| P044 | next-stage never scans for Path B2 — it is reached by number only | `commands/next-stage.md` | `prose-only` | prose | unguarded — a replay case in which a QA-ready issue exists and next-stage runs with no number: it is not picked |
| P045 | next-stage never repairs a label-invariant violation itself — it stops and reports | `commands/next-stage.md` | `prose-only` | prose | unguarded — a replay case on next-stage over an issue with two `track:` labels: the labels are unchanged and the run reports |
| P047 | The loop never merges another issue's branch into the issue branch — the remedy is to sync the base | `commands/next-stage.md` · `commands/spec-answers.md` | `hooked` | hook K | `hooks/tests/test_guard_gate.py::RuleK_LoopMergesOnlyBaseOrOwn` — rule K acts in a loop worktree — where every command's git work runs; a merge in the person's own checkout is not the loop's and is not judged |
| P048 | The fast track's escalation valve (C3) never uses the STOP exit — it is a designed transition | `commands/next-stage.md` | `prose-only` | prose | unguarded — a replay case that escalates a fast-track issue: labels end on the spec track's gate, not `status: blocked`, and no STOP comment is posted |
| P049 | to-issues relays the intake seat's question to the user verbatim — it does not answer, soften or batch it | `commands/to-issues.md` | `prose-only` | prose | unguarded — a replay case on to-issues in which the seat returns a question: the text shown to the user is the seat's, unaltered |
| P050 | uninit never retires the loop mid-flight — open loop issues or CRs stop it | `commands/uninit.md` | `prose-only` | prose | unguarded — a replay case on uninit with an open `spec/*` CR: it stops and lists it, removing nothing |
| P051 | uninit never deletes the work products — specs, the acceptance suite, issue and CR history | `commands/uninit.md` | `prose-only` | prose | unguarded — a replay case on uninit: `<specs_dir>` and `<acceptance_dir>` are intact afterwards |
| P052 | An existing branch is found by Lookup, never guessed | `commands/integrate.md` · `commands/review-answers.md` · `commands/spec-answers.md` · `commands/patrol.md` | `guarded-by-case` | references/branch-names.md | C31 |
| P053 | integrate's worktree starts at the remote's spec-branch tip, never at a stale local ref | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay seed whose local spec ref is behind the remote's (every seed today has local = remote, so only the source shows it) |
| P054 | integrate merges a CR that is open, never one already merged | `commands/integrate.md` | `guarded-by-case` | commands/integrate.md | C12 |
| P055 | Once both CRs are merged, integrate validates the current spec-branch tip — it never reconstructs it from stale `feat` / `qa` tips | `commands/integrate.md` | `guarded-by-case` | commands/integrate.md | C12 |
| P057 | On a re-verdict the final-gate kit's cards are regenerated wholesale from the new run, never patched | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay re-verdict whose kit comment afterwards carries the new run's cards and a re-stamped `cards-sha`, with none of the earlier run's text |
| P058 | A green verdict states what the run licenses — "green against the pre-rework spec, at SHA x" — never "verified" | `commands/integrate.md` | `guarded-by-case` | commands/integrate.md | F4, C12 |
| P059 | A classifiable RED at integration is routed to its fix, never finalized | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay case with a red integration: labels do not reach `in-user-review` and the spec branch is not pushed as green |
| P060 | An integration RED is fixed in the implementation, the harness or the contract, never in a QA assertion (QA-4 at stage 6) | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay case with an integration red that is a contract disagreement: the assertion is unchanged afterwards (D9 / D19 assert QA-4 at the QA dispatch, not at integration) |
| P061 | On a STOP `status: blocked` is worn alone, never beside a gate or phase label | `commands/integrate.md` | `guarded-by-case` | references/workflow.md | C1, F5 — C1 and F5 assert `blocked` alone on next-stage's STOP; integrate's re-verdict STOP (entered from `in-user-review`) has no case of its own |
| P062 | A red integration is never silently merged | `commands/integrate.md` | `prose-only` | prose | unguarded — a replay case with a red integration: the spec CR is not merged and the report says red |
| P063 | The gate-kit comment is never a review item | `commands/review-answers.md` · `commands/tip.md` · `commands/spec-answers.md` | `guarded-by-case` | commands/review-answers.md | E8 |
| P064 | A behavioural claim in a review answer cites a spec rule or a test, never a code line alone | `commands/review-answers.md` | `prose-only` | prose | semantic — whether a claim is behavioural and what it rests on is a reading of the answer |
| P065 | A marker-carrying comment never opens with a quote block | `commands/review-answers.md` | `hooked` | hook C | `hooks/tests/test_guard_gate.py::RuleC_MarkerCommentNeverOpensWithAQuote` |
| P066 | A stage-(7) answer never resolves the user's thread — the user's satisfaction closes it | `commands/review-answers.md` | `guarded-by-case` | commands/review-answers.md | F2 |
| P067 | Silence is never consent to a change at stage (7) | `commands/review-answers.md` | `prose-only` | prose | authority — only the user's word authorizes a change; whether a reply is that word is a reading of it |
| P068 | A reaction is consent to a readback proposing one change, never to one proposing several | `commands/review-answers.md` | `prose-only` | prose | authority — only the user's word authorizes a change; whether a readback proposes one change or several is a reading of it |
| P069 | At stage (7) an ambiguous reply resolves to asking, never to acting | `commands/review-answers.md` | `prose-only` | prose | semantic — whether a reply is ambiguous is a reading of it |
| P070 | A failing assertion that faithfully states the contract is never classified as "they authorized it" — the user rules | `commands/review-answers.md` | `prose-only` | prose | authority — ruling on a contract defect is the user's; whether an assertion faithfully states the contract is a reading |
| P071 | The back-to-intake door is taken on the user's word, never by the agent on its own | `commands/review-answers.md` | `prose-only` | prose | authority — abandoning the issue's work is the user's decision |
| P072 | tip is typed by the user; patrol never runs it | `commands/tip.md` | `guarded-by-case` | commands/tip.md | C19 |
| P073 | Asked to act on what it finds, tip names the command or the human act — it never does it itself | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 |
| P074 | A lock tip finds is part of its answer, never something it waits on or clears | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 — F12 asserts zero writes (the lock is not cleared); nothing asserts that tip does not wait |
| P075 | Review-clean is the code-review record current and zero open threads, never zero threads alone | `commands/tip.md` · `commands/patrol.md` | `guarded-by-case` | references/workflow.md | C22 — C22 asserts it at next-stage B2.1; tip's own reading of review-clean has no case |
| P076 | tip's answer is a reading of the documents, never a new rule | `commands/tip.md` | `prose-only` | prose | semantic — whether an answer adds a rule the documents do not give is a reading of it |
| P077 | tip names the repair for an illegal or stuck state and never performs it | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 |
| P078 | tip never declares a `processing` lock stale — it reports the pair and the evidence | `commands/tip.md` | `prose-only` | prose | unguarded — a replay case on tip over `processing` beside a phase label: the answer reports the pair and does not call the lock stale |
| P079 | An agent never deletes a remote branch — `git push origin --delete` is the human's to run | `commands/tip.md` | `deterministic-candidate` | none yet | — |
| P080 | tip never writes — no label, no comment, no commit, no branch, no cleared `blocked` | `commands/tip.md` | `guarded-by-case` | commands/tip.md | C19, F12 |
| P081 | tip never dispatches a seat | `commands/tip.md` | `guarded-by-case` | commands/tip.md | F12 |
| P082 | The agent-marker predicate (`**[`, `✅ [`) never swallows a human's bare `✅` answer | `commands/spec-answers.md` | `guarded-by-case` | references/patrol-scan.md | A1 |
| P083 | A ruling's authority tag and an empirical premise's `(unverified)` evidence tag are never merged into one parenthesis | `commands/spec-answers.md` | `deterministic-candidate` | none yet | — |
| P084 | A question a depth-0 fold raises is a new `Q<k>` with its own thread, never a reply in the folded question's thread | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay case in which a depth-0 fold raises a question: a new thread exists and the folded thread gains no question reply (E11 covers depth 1) |
| P085 | On a post-integration re-entry a question the fold surfaces is one top-level `[review] · question` comment, never a new seat thread | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | C5 |
| P086 | On a post-integration re-entry a question the fold surfaces is never deferred | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay re-entry whose fold surfaces a question: no `· deferred` entry and no `[spec-answers] · deferred` comment |
| P087 | A rule born from an amendment carries `(from A<k>)` as its provenance, never `(assumed)` | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay amendment fold (E6's or E8's seed): the rule it adds is tagged `(from A<k>)` |
| P088 | A resolved Open Questions entry never restates rule, scenario or contract text — it points at IDs | `commands/spec-answers.md` | `prose-only` | prose | semantic — whether an entry restates a rule or points at it is a reading of the entry |
| P089 | The re-spawned folding seat never writes `## Open Questions` itself — em owns the section | `commands/spec-answers.md` | `guarded-by-case` | references/workflow.md | E11 |
| P090 | A `· follow-up` reply on the same question is never deferred | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | E11 |
| P091 | A seat that needs more information never resolves the thread — it replies `· follow-up` and leaves it open | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay case in which the folding seat returns a follow-up: the thread carries the reply and is still unresolved |
| P092 | spec-answers never edits the issue body or acceptance criteria — it comments, and the user decides whether to amend | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay case whose resolution changes the user story: the journal holds an ISSUE-COMMENT and no ISSUE-EDIT-BODY (the call alone does not decide it: intake's finalize edits the body legitimately) |
| P093 | Fold threads and the `[spec-answers] · deferred` comment are posted after the push, never before | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | E11 |
| P094 | A post-integration fold never returns the issue to implementation | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | C5 |
| P095 | A red on a post-integration re-entry is never resolved by editing an assertion to match (QA-4) | `commands/spec-answers.md` | `prose-only` | prose | unguarded — a replay re-entry whose acceptance run is red: the assertion is unchanged afterwards |
| P096 | When a post-integration fold changed behaviour, the stale pair is not taken as evidence — the suite is not run for it, the cards are not regenerated, `cards-sha` is not re-stamped | `commands/spec-answers.md` | `guarded-by-case` | commands/spec-answers.md | C5 |
| P097 | patrol never re-reads the forge to confirm a row of the scanner's table | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A8, F9 |
| P098 | A row patrol cannot act on as written is reported as an illegal state, never re-derived | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay pass whose scanner table carries a verdict outside the brief's list: the row is reported `illegal:` and the forge is not re-read for it |
| P099 | patrol never re-scans between the actions of one pass | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | F9 — F9 asserts the main agent lists nothing after the table; a second scanner dispatch in an N>1 pass (C26) has no assertion of its own |
| P100 | A merged CR on an issue in an unexpected status is an illegal state patrol reports and never repairs | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay pass over a merged CR whose issue wears a status other than the close-out's: no label or close is written and the row is `illegal:` (C24 / C27 / F13 / F14 cover gate-label illegal states) |
| P101 | The implementer is never dispatched onto a fast-track branch — the main agent addresses its own CR's threads | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay address-review pass on a fast CR: no `implementer` dispatch |
| P102 | A seat never commits — every commit goes through the commit sub-agent | `commands/patrol.md` | `guarded-by-case` | references/commit-brief.md | L3 |
| P103 | patrol's code-review action never commits | `commands/patrol.md` | `prose-only` | prose | unguarded — C23's seed with an assertion that the remote's refs are unchanged by the action |
| P104 | patrol's code-review action never resolves a thread | `commands/patrol.md` | `prose-only` | prose | unguarded — C23's seed with an assertion that the journal holds no thread-resolve |
| P105 | patrol's fidelity-audit action never commits | `commands/patrol.md` | `prose-only` | prose | unguarded — C17's seed with an assertion that the remote's refs are unchanged by the action |
| P106 | patrol's fidelity-audit action never touches the implementation branch | `commands/patrol.md` | `prose-only` | prose | unguarded — C17's seed with an assertion that no call of the action names the implementation branch — hook E is a supporting operational boundary (while the marker exists a git action on the implementation ref is denied), not this rule's owner: the action also runs before the marker is written and after it is removed |
| P107 | patrol's fidelity-audit action never resolves a thread | `commands/patrol.md` | `prose-only` | prose | unguarded — C17's seed with an assertion that the journal holds no thread-resolve |
| P108 | The gate holder is read from the scanner's table, never re-listed | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A8, F9 |
| P109 | A bot identity never holds a gate | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay pass over a bot-authored, unassigned inbox issue: no summary is written and the report says it needs an assignee (C24 / F13 cover a bot-applied label, not a bot holder) — hook A is a supporting operational boundary: an `[intake] · summary` on a bot-authored, unassigned issue is denied (`has no holder`) |
| P110 | On an issue with no gate holder only the questions batch may be posted | `commands/patrol.md` | `prose-only` | prose | unguarded — the same replay pass: the journal holds the `[intake]` batch and no other comment on that issue — hook A is a supporting operational boundary (a summary with no holder is denied), not the whole rule |
| P111 | Intake's clarification thinking is the dispatched `product` seat's, never patrol's own | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay intake pass: a `product` dispatch precedes every `[intake]` comment and the comment is its text |
| P112 | At finalize, comments from anyone but the gate holder are thread discussion — never folded in, never listed, never a reason to wait | `commands/patrol.md` | `prose-only` | prose | unguarded — a replay finalize on an issue whose latest summary is followed by a non-holder comment: the summary is finalized verbatim and nothing waits |
| P113 | A summary request from anyone but the gate holder never triggers an intake summary | `commands/patrol.md` | `hooked` | hook A | `hooks/tests/test_guard_gate.py::RuleA_IntakeSummaryTrigger` |
| P114 | The intake question batch is asked once — patrol never re-batches | `commands/patrol.md` | `deterministic-candidate` | none yet | — |
| P115 | A bot's or an agent-marker comment never counts as a human comment on an intake thread | `commands/patrol.md` | `guarded-by-case` | references/patrol-scan.md | A9 — hook I is a supporting boundary: a reply where no human comment follows the latest `[intake]` comment is denied |
| P116 | An intake reply never re-asks the question batch | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A9 |
| P117 | An intake reply never edits the issue body or a label | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A9 |
| P118 | An intake reply never @-mentions anyone | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | A9 |
| P119 | A `this pass` cell is one clause from the vocabulary, never a list and never a commit log | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | B7, F11 |
| P120 | An actionable row the pass did not reach is `queued: <action>`, never `in progress` | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | C30 |
| P121 | An in-flight `track: spec` row never needs a label from the holder | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | C30 |
| P122 | A gated row waiting on an open blocker reads `waits on #<n>` alone — never `queued: waits on …`, never `blocked:` | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | F15 |
| P123 | A row whose branches are unknown is never acted on and never read as "no branch" | `commands/patrol.md` | `guarded-by-case` | references/branch-names.md | C31, A11 |
| P124 | A queue item is never written without its link | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | B7, F11 |
| P125 | An illegal state is a table row and a queue item, never a note under Details | `commands/patrol.md` | `guarded-by-case` | commands/patrol.md | B7 |
| P126 | patrol never runs intake for the user beyond the protocol | `commands/patrol.md` | `prose-only` | prose | semantic — whether an act is beyond the protocol is a reading of it |
| P127 | On anything unexpected patrol stops and reports, never improvises | `commands/patrol.md` | `prose-only` | prose | semantic — whether an act is an improvisation is a reading of it against the command |

**Not a rule** — a prohibition word that forbids an agent nothing. One row per reason; every fragment is listed, none is matched by pattern.

| id | reason | fragments |
|---|---|---|
| P007 | states a fact or the persona's stance; forbids no act | `agents/qa.md` “You do not care how elegant the code is” · `agents/reviewer.md` “The author cannot see their own blind spots” · `commands/config.md` “this prompt never runs” · `commands/config.md` “seats are never configured” · `commands/init.md` “routine plugin upgrades never demand a re-init” · `commands/uninit.md` “don't block retirement” · `commands/uninit.md` “a plugin command cannot uninstall its own plugin” · `commands/integrate.md` “the user's checkout was never touched” · `commands/review-answers.md` “report what never landed” · `commands/tip.md` “the close-out never ran” · `commands/tip.md` “it was never gated” · `commands/spec-answers.md` “was never read” · `commands/spec-answers.md` “they do not hold the issue” · `commands/spec-answers.md` “the user's checkout was never touched” · `commands/patrol.md` “It never changes the model this command itself runs on” · `commands/patrol.md` “the review that never ran” · `commands/patrol.md` “(or never re-checked)” · `commands/patrol.md` “the audit that never ran” |
| P008 | a condition — what to do when something cannot be done — not a prohibition | `agents/reviewer.md` “If you cannot explain why a line is correct” · `templates/implementer.md` “a definition you cannot build to is a question” · `commands/next-stage.md` “anything this command cannot or should not decide” · `commands/integrate.md` “A local ref that cannot fast-forward” · `commands/review-answers.md` “Anything you cannot read as a clear yes” · `commands/spec-answers.md` “On anything this command cannot or should not decide” · `commands/patrol.md` “A row you cannot act on as written” · `commands/patrol.md` “A row the pass cannot act on as written” |
| P009 | example text inside the implementer template's commented-out stack block, which the project replaces with its own | `templates/implementer.md` “Raw SQL only when the ORM cannot express it cleanly” |
| P010 | addressed to the human who fills in the template, not to an agent | `templates/claude-workflow.md` “the seat names never change” · `templates/idea.md` “Don't add labels” |
| P011 | describes another seat's or command's rule to the reader (the rule is stated to its owner elsewhere); forbids the reader nothing | `templates/implementer.md` “QA never touches the persistence layer” · `commands/tip.md` “patrol never re-invokes anything on `blocked`” · `commands/spec-answers.md` “qa never writes spec text” |
| P029 | says where a value lives or what state a file is in (a local key is per person and not committed); forbids no act | `commands/config.md` “per person, per clone, never committed” · `commands/init.md` “(`.claude/roz-gate.local.json`, never committed). Say so” · `commands/init.md` “(`.claude/roz-gate.local.json`, never committed; the write” · `commands/next-stage.md` “are per person, per clone, never in the block” · `commands/integrate.md` “are per person, per clone, never in the block” · `commands/review-answers.md` “are per person, per clone, never in the block” · `commands/spec-answers.md` “are per person, per clone, never in the block” · `commands/patrol.md` “are per person, per clone, never in the block” |
| P031 | describes a value the tool refuses (`bin/roz-config` validates it); the prose forbids the agent nothing | `commands/config.md` “never a directory or a `.gitignore`” |
| P040 | the word is part of a name — the R&R table's `Never` column, the kit's `cannot-be-covered-black-box` bucket | `commands/init.md` “R&R row (Owns / Never)” · `commands/init.md` “Text that fights the Never column” · `commands/integrate.md` “cannot-be-covered-black-box” |
| P046 | defines a term by what it is not; forbids no act | `commands/next-stage.md` “(never code this issue would build)” · `commands/integrate.md` “never reached its assertion” · `commands/tip.md` “(never `spec` + `ready-for-dev`” · `commands/spec-answers.md` “(never code this spec asks for)” |
| P056 | states a fact given as the reason for a neighbouring rule; forbids no act | `commands/integrate.md` “a feature-scoped run cannot see (a sync” · `commands/integrate.md` “this command never moves the local ref” · `commands/integrate.md` “exactly the code a feature-scoped run cannot see” · `commands/review-answers.md` “a reaction cannot select which” · `commands/tip.md` “This command cannot tell a live lock from a stale one” · `commands/spec-answers.md` “the item itself never changes” · `commands/spec-answers.md` “the two axes never share a tag” · `commands/patrol.md` “never queues behind machine work” · `commands/patrol.md` “must not starve the rest of the loop” · `commands/patrol.md` “so a quiet inbox is never a mystery” · `commands/patrol.md` “so it never *newly* enters anything” |
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
