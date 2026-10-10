# The Roz Gate workflow

The authoritative workflow doc, shipped with the plugin — commands read it via
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`, so a plugin upgrade updates
every project at once. The project's CLAUDE.md carries only a pointer to this
file plus its `### Roz Gate config` block; angle-bracket values below
(`<specs_dir>`, `<acceptance_dir>`) resolve from that config block.


An idea becomes a shipped feature through a labelled, role-driven loop. The
**main agent** is the user's proxy and the stakeholder accountable for every
output; it orchestrates the loop and dispatches the specialist agents (plugin:
em, product, qa, reviewer; project: implementer). Each stage is gated by a
`status:` label or a change request (PR/MR — "CR") the user reviews — the human
stays in the loop at every transition.

## Roles (R&R)

| Role | Owns | Never |
|------|------|-------|
| **main agent** | proxy + accountable for all output; intake: dispatches `product` under the intake brief, relays its questions verbatim, publishes the confirmed story; orchestration, git/forge mechanics, integration; **hosts the (7) review conversation** — answering by quotation, dispatching for judgment; decides the next step; implements `track: fast` changes itself | act as a specialist on any clarification or `track: spec` work (it dispatches) |
| **product** | actors, scenarios (Given/When/Then: happy/edge/failure), consistency, user-facing gaps | architecture, code, impl tests |
| **em** | problem statement, success metrics, architecture / domain boundaries, business rules, out-of-scope; resolves conflicts; owns `spec.md` | code, deep implementation |
| **implementer** | `technical-spec.md` (the contract); implementation code + **unit** tests; the QA test **port** for non-API features | spec scenarios, black-box tests, reviewing its own code |
| **qa** | black-box acceptance tests from `spec.md`'s scenarios + the contract **only — never the implementation**; `test-spec.md`; the integration verdict — reports **only to the main agent** | reading the implementation, unit tests, architecture |
| **reviewer** | independent review of the **implementation code** (correctness / security / performance / maintainability); **fidelity audit of the QA suite** (assertions vs scenarios — cited evidence, never a verdict); severity-graded inline comments | architecture (em's), re-testing behaviour (qa's), writing code; **reading the implementation when auditing QA's tests** (separate blind dispatch) |

**Seats and personas.** The role names above are fixed **seats** — the
workflow's vocabulary never changes. Who sits in a seat is per-project
configuration: the `### Roz Gate personas` block in CLAUDE.md maps each seat
to the subagent actually dispatched — the plugin default (`roz-gate:<role>`)
or an agent the user already owns (e.g. `implementer: backend`). Commands
always dispatch through this mapping, and every dispatch attaches the seat's
**contract**: its R&R row above (Owns / Never) plus the stage's instructions.
**Persona is swappable; the contract never is.** A persona whose own text
fights its seat's Never column is a misconfiguration — init flags it when
linking. Personas block missing (pre-1.2 project) → plugin defaults
(`roz-gate:<role>`; implementer = the project's `implementer` agent).

## The loop

The first two stages differ by binding force: (1) drafts the **MOU** — intent
and boundary, no implementation terms — and (2) signs the **contract**
(`technical-spec.md`), whose enforcement is blind QA (4) plus the integration
verdict (6). `track: fast` deals close on the MOU alone.

**(1) Intake** — `/roz-gate:to-issues` (or the inbox, (1b)). The `product`
agent, dispatched under the **intake brief** (one self-contained question at a
time, each with a recommendation), clarifies a use case into **one issue = one
user story**; the main agent only relays the questions and publishes the
confirmed result — clarification thinking never lives in the orchestrator's
context. Intake applies the `track:` label you confirmed; you apply the gate
(`status:`) label — the human guards the gate.

**(1a) Track** — every issue in the loop carries **exactly one `track:` label**,
proposed at intake and confirmed (or overridden) by you:
- **`track: spec`** — needs design: user-facing scenarios, domain/data
  modelling, real decisions to resolve. Gate it with `status: ready-for-spec`.
- **`track: fast`** — vendor / config / chore / doc update / test fix. No spec
  stage; gate it with `status: ready-for-dev` directly and it follows **the
  fast track** instead of (2)–(6).

**(1b) The inbox — async intake.** An open issue with **no `track:` label** is
the **inbox**: a raw idea captured away from the keyboard (e.g. the forge's
mobile app), not yet in the loop — every command except intake triage ignores
it. You may narrow your inbox (`inbox_label`, `inbox_assignee` — lists, yours
per clone, set with `/roz-gate:config`): a track-less issue outside the filter
is a plain issue patrol only counts. Three beats — ask once, summarize on demand, the label confirms:
1. Patrol posts **one** batched questions comment (prefixed `**[intake]**`,
   numbered, each option with a marked recommendation) — then leaves the
   thread to the humans: free-form discussion, anyone may weigh in, from any
   device. Patrol never re-batches.
2. When the **gate holder** — the issue's assignee (unassigned → the author,
   if human; a bot identity never holds a gate) —
   ends a comment with the line **`summary`** (corrections and the request
   can share one comment; a first-line `summary` works too), the `product`
   agent (same intake brief, async mode) condenses the body + **all**
   comments into one
   `**[intake] · summary**`: story + AC + proposed `track:` on top, an
   attributed decision trail folded below; unanswered questions resolve to their recommendations,
   listed as explicit **assumptions**; disagreements are shown as
   **contested points** with both sides — one reply flips them. Corrections?
   Reply them — end with `summary` to re-read a revised summary first, or
   label directly: finalize folds your corrections either way.
3. **The gate label is the confirmation** — no approve keyword. The gate
   holder applies `status: ready-for-spec` (⇒ `track: spec`) or
   `status: ready-for-dev` (⇒ `track: fast`); patrol then rewrites the body
   to the story template and applies that track — the label choice itself
   confirms the track. The label reads: **"build the story from everything
   I said"** — at finalize only the holder's words drive the body; bystander
   comments never fold in un-endorsed. Confident holders may label without
   ever asking for a summary; patrol summarizes before finalizing either
   way. Everything before the label is input; **the label is the decision**
   — and it is still only ever the holder's to apply.

**(2) Spec refinement** — gated by `status: ready-for-spec`. `em`+`product`
write `<specs_dir>/{n}/spec.md`; `implementer` writes `technical-spec.md`
(the contract: command/API spec, schema, behavioral guarantees). Opens the
**spec CR** (`spec/{n}`) for your review; the spec CR **stays open** as the
feature umbrella for the whole feature.

**(2a) Open-question Q&A loop** — open questions are posted as inline review
threads on the spec CR, each tagged with the role that raised it. `spec.md`'s
`## Open Questions` is the **single collection point for every seat's
questions**, whatever document the seat owns — a question written anywhere
else has no route to you, so a seat's question is *moved* there, never
copied (since 1.15.0 guard-gate rule D refuses the commit while
`technical-spec.md` still carries an open-questions section). You answer inline; the fold command re-spawns the
owning role agent and folds the decision into **the document the raising seat
owns** (`spec.md`; `technical-spec.md` for `[implementer]` questions — the
contract QA tests against must learn the answer, or the pipe is one-way), and
resolves the thread. A resolution that changes the user story → a comment on
the issue (it never auto-edits the issue body/AC). Gate: all threads resolved.

**When the spec stage shows the issue missed something — three routes, by how
much changed.** (i) The story and its AC still hold, the spec must simply
cover more → **amend in place**: open a thread on the spec CR yourself ("the
spec misses X"); `spec-answers` treats a human-opened thread as an amendment
request — folds it into the owning document, records it as a resolved
`A<k>` item, replies, resolves. (ii) The **story itself changed** →
**re-spec**: close the spec CR yourself, amend the issue, re-apply
`ready-for-spec`; nothing halted abnormally, so no `blocked` is involved —
but the old `spec/{n}` is yours to delete (`git push origin --delete
spec/{n}`; `next-stage` stops and tells you so, because **an agent never
deletes or force-pushes a remote branch**), and the previous spec stays
readable in the closed CR. Under a `branch_template` that carries `{seq}`
there is nothing to delete: the next pass cuts the next sequence and the
old branch stays (`references/branch-names.md`). (iii) The issue is **a different story** → strip
its `track:`/`status:` labels and it returns to the inbox, exactly as from
(7) below.

**(3) Implementation + (4) Validation — launch together**, gated by
`status: ready-for-dev`. Independent siblings, both branched off `spec/{n}`,
both CRs targeting the spec CR:
- **(3)** `implementer` on `feat/{n}` → implementation code + **unit** tests.
- **(4)** `qa` on `qa/{n}` → `test-spec.md` + black-box tests in
  `<acceptance_dir>/<feature>/`. The qa branch carries **no implementation
  code** — that structurally enforces the black box: QA tests the **contract**
  (or a provided port), never the raw implementation. Tests are a **living
  suite** — maintained and evolving, never write-once per-issue snapshots.
  Suite layout is the project's call, like its test runner: optional config
  `acceptance_layout` declares it (absent → feature-organized, the
  default). `test-spec.md`'s scenario→test map is derived from
  machine-readable trace markers in the test source (config
  `trace_marker`), never hand-maintained. The QA CR opens as a
  **draft** and is marked ready only when the suite is complete —
  ready-not-draft is the completeness signal integration waits for.
- **(5q)** `reviewer`, in a separate implementation-blind dispatch on
  `qa/{n}` (the branch topology enforces the blindness, and since 1.16.0
  guard-blind rule E enforces it at the tool layer while the dispatch's
  marker exists — no read of `src/` outside the suite, no touch of
  `feat/{n}`), audits the QA
  suite's fidelity to the spec — the suite the verdict is computed from
  is otherwise the loop's only unaudited artifact. Findings are two-way
  cited threads on the QA CR; both CRs must be thread-clean before (6).

If **QA or the implementer** hits a contract ambiguity mid-flight, it stops
and reports to the main agent — it never interprets, and it never decides
unilaterally in code. The main agent distills the question and its
recommendation into an inline thread on the still-open spec CR; the affected
work pauses and the issue re-enters `status: in-spec-review` (the backward
transition). The decision folds in through (2a)'s machinery; the label clears
and the paused side resumes. A (5) review finding that is really a contract
ambiguity takes the same route through the main agent — never settled on the
implementation CR, where the contract stays unamended and QA keeps testing
the old text.

**(5) Code review** — on the implementation CR. `reviewer` posts
severity-graded inline comments (`blocking` / `should-fix` / `nit` /
`question`); `implementer` addresses them; loop until **all review threads
resolved**.

**(6) Integration = the verdict.** Once the implementation CR is review-clean
and the QA CR is ready, the main agent merges **both** into `spec/{n}` and runs
QA's black-box tests against the implementation **for the first time**.
Pass/fail is the verdict on whether the implementation matches the spec — this
is where genuine bugs surface. Once both CRs are merged, a later run
**validates the current `spec/{n}` tip and merges nothing** — the spec branch
is the integration source of truth from that moment, never reconstructed from
stale `feat/{n}` / `qa/{n}` tips; it moves legitimately without either branch
changing (a rebase onto a new base, a sync with concurrently merged work),
and each move wants a fresh verdict. Patrol routes that re-verdict like the
first one.

**The base branch.** `default_branch` — yours, per clone (`/roz-gate:config
default_branch <branch>`, `.claude/roz-gate.local.json`, never committed;
default: the remote's HEAD) — is the loop's base: `spec/{n}`
and `fast/{n}` are cut from it, their CRs target it, the fast reviewer diffs
against it, and (6) merges it in before (7) — `feat/{n}` and `qa/{n}` are
siblings off `spec/{n}` and target it, as (3)/(4) say. It is whatever the team ships
from — the trunk, or on a sprint cadence the current release branch
(`release/20261006`), changed at handover with `/roz-gate:config`. The
commands always read the current value: an issue cut from the previous base
is the human's to move (retarget its CR, rebase); nothing in the loop pins or
detects it. A command's git reference to it is always `origin/<default_branch>`
— the loop never moves the local ref, and in a dedicated clone nobody does; the
bare name is a CR target only. A base the remote does not have stops the cut
(`blocked`).

**The branch names.** `spec/{n}`, `feat/{n}`, `qa/{n}`, `fast/{n}` are the
**default** names — the block's `branch_template` renders them for a repo
with its own convention (`{type}/{user}/{n}/{seq}` → `spec/pwliangc/5/1`,
`fix/pwliangc/5/1`, `test/pwliangc/5/1`): `{type}` is `spec` / `test` / the
issue's `type:` label, `{user}` your `branch_user` (or your forge login),
`{seq}` the attempt. Every command binds its names once from the template
and finds an existing branch on the remote by pattern — it never guesses
another person's `{user}`; the hooks read the same template
(`references/branch-names.md`). Like the base, a template change is yours
to carry for an issue already cut.

**(7) Review** — after a green (6), the main agent brings the default branch
into `spec/{n}` (resolving conflicts on the feature branch so the spec CR's
diff stays clean), then sets `status: in-user-review` and **hosts your review
on the spec CR**. Reviewing produces comments, and comments are heard: the main
agent answers what the artifacts already say — quoted, with links — dispatches
a seat when the answer needs specialist judgment, and reads any change back to
you in one line before making it. **Nothing is built without your word**;
silence is never consent. Your three options do not change: **merge it, change
it, or send it back to intake** — starting over is a normal outcome here, not a
failure. The issue leaves (7) when you merge. (`/roz-gate:review-answers`.)

**The hand-back rule.** Whenever `status: in-user-review` is applied or
re-applied, the SHA at the head of `spec/{n}` has a **captured, green, full**
acceptance run and a full unit run **at that exact SHA**, and the gate kit's
evidence cards were regenerated wholesale from that run's output — a full run
and wholesale regeneration are a matched pair, since cards assembled from a
partial run assert observed values nobody observed. What such a run licenses is
one sentence and never more: *"green against the pre-rework spec, at SHA
`<x>`"*. The acceptance suite derives from the spec as approved, so it can only
fail on behaviour the spec described. Rework that *adds* behaviour no scenario
describes ships green and unverified — nothing in the loop can verify it,
because verification needs a spec and by construction there is not one. That is
what the other door is for, and why it stays visible.

## The fast track (`track: fast`)

Skips (2), (2a), (4) and (6). Picked up from `status: ready-for-dev`:
- The **main agent implements directly** on `fast/{n}` off the default branch;
  one CR targeting the default branch. This is the one R&R exception.
- The guards replacing QA: a bug fix must carry a unit test reproducing it, the
  existing suite must stay green, **(5) still applies** (skippable for doc-only
  diffs), and you review and merge the CR yourself. Once review-clean the main
  agent sets `status: in-user-review`; merging closes the issue — the forge
  on its own rule, or patrol's close-out on the next pass.
- **(7) works the same here, on `fast/{n}`** — with the boundary inverted, as
  it is throughout this track: the main agent wrote the code, so it answers you
  directly, dispatches no seat, and skips the readback ceremony. A (7) change
  to the code re-dispatches `reviewer` on the new commits — on this track that
  is the whole guard.
- **Escalation valve:** the moment the change stops being trivial (a real
  design decision, user-facing behaviour, a growing diff) — stop and relabel
  atomically: `track: fast` → `track: spec`, gate back to
  `status: ready-for-spec`; the issue rejoins the loop at (2).

## Label state machine

- An open issue with **no `track:` label** is the **inbox** ((1b)) — pre-loop,
  not a violation: invisible to every command except patrol's async intake
  (and, with an inbox filter configured, to patrol too unless it matches).
  A **gate label on a track-less issue** is the one legal transient of intake:
  the gate holder's confirmation, which the next patrol pass finalizes into a
  body rewrite + the confirmed `track:` (`ready-for-spec` ⇒ `spec`,
  `ready-for-dev` ⇒ `fast`).
- An issue also **returns to the inbox from (2a) or (7)**: when your review concludes
  the issue itself was wrong, you strip its `track:` and `status:` labels and it
  is a raw idea again, discussion and decision ledger intact on the same issue.
  Redoing the work is cheap; re-answering what you already ruled is not, so the
  ledger carries forward as prior answers to confirm.
- Every open issue in the loop has **exactly one `track:` label** (applied at
  intake; only the escalation valve changes it) and **at most one `status:`
  label besides the `processing` lock** — the lock is a mutex, not a phase:
  while a command runs, `processing` coexists with the phase label it locks (a
  stale pair tells you exactly which stage a killed run died in).
- Gate states (waiting for a command): `spec`+`ready-for-spec`,
  `spec`+`ready-for-dev`, `fast`+`ready-for-dev`. Transient states:
  `processing` (locked by a running command), `in-spec-review` (spec CR
  awaiting you — or re-entered on a QA ambiguity mid-flight or a spec-semantics
  change at (7); the backward transition), `in-user-review` (work that passed
  the verdict, awaiting your review — where the (7) conversation lives),
  `blocked` (an automated step stopped on something it won't decide and left an
  issue comment with evidence + recommendation; you decide, the label clears,
  the step re-runs). No `status:` label = in flight (the open CRs are the
  state) or done.
- `fast`+`ready-for-spec` is **illegal**. Commands validate these invariants
  before acting and stop to report a violation; they never repair labels.
- On GitLab, `track::`/`status::` are scoped labels (the platform enforces the
  one-per-scope invariants); the `processing` lock is a plain label so it can
  coexist with a phase label.

## The main agent

**The workspace.** You may be working in the checkout — on the default branch
itself — while a scheduled patrol fires and auto-invokes `next-stage`,
`integrate`, `spec-answers` or `review-answers`. So a command's **entire
working surface is a linked worktree**, never your checkout: it creates
`$(git rev-parse --git-common-dir)/roz-gate/wt/<branch>` with `git worktree
add` at its branch step, and every checkout, merge, commit, test run and
seat dispatch happens inside it (`cd` there or `git -C`). The commit itself
is made by the **commit sub-agent** (`references/commit-brief.md`) dispatched
into that worktree — the target repo's pre-commit output lands in its
context, never the main agent's, for the same reason patrol's scan is a
sub-agent; the main agent pushes from the `sha` it returns. It never runs
`git checkout`, `switch`, `reset`, `stash` or `merge` in your checkout, not
even transiently; `git fetch` is the one git call it may make there, because
a fetch touches no working tree. Nothing of the agent's work is visible in
your checkout until it lands on the remote. The worktree lives for one
command: **both exits** remove it (`git worktree remove --force <path>` then
`git worktree prune`) — Done because the branch is already on the remote,
STOP because the worktree *is* the uncommitted local work. A branch already
checked out in another worktree makes `git worktree add` refuse: that
refusal is the mutex between two commands running at once, and it is a STOP
that removes nothing — the worktree is the other run's — never a reason to
work in the checkout. A command removes only the worktrees it created. Patrol itself touches no git at all —
its scan is forge calls. The one piece of command state outside a worktree
is rule E's fidelity-dispatch marker, which lives in the *common* git dir
the checkout and its worktrees share (`hooks/README.md`). **An agent never
deletes or force-pushes a remote branch**: every remote write a command
makes is additive — a new branch, a commit on its own branch, a label, a
comment. Removing a branch is the human's act, like a gate label.

The bridge between you and the team, both directions, and the owner of state
management under one rule: **you move gate labels — a gate label is an
authorization; agents and commands move transient labels — a transient label is
a status report. Neither ever moves the other's.**

| Transition | Owner |
|---|---|
| `track:` label at intake | `/roz-gate:to-issues` (interactive) or the (1b) proposal comment (async) proposes — **you** confirm either way |
| raw idea → inbox issue (no labels) | **you** (e.g. the forge's mobile app) |
| inbox → in the loop (body rewrite + `track:` label) | patrol's async intake, only after the **gate holder** (issue assignee; unassigned → author, if human — a bot never holds a gate) applies the gate label — the label is the confirmation |
| apply a gate label (`ready-for-spec`, `ready-for-dev`) | **you**, only ever you |
| gate → `processing` → next state | the running command |
| (2) complete → `in-spec-review` | the spec stage |
| `in-spec-review` → `ready-for-dev` (all threads resolved) | **you** |
| in flight → `in-spec-review` (backward; QA ambiguity) | main agent |
| `in-user-review` → `in-spec-review` (backward; a (7) comment changes what a rule means) | main agent |
| → `in-user-review` (both tracks; and back from (2a) after a (7) amendment) | main agent |
| (7) → the inbox (`track:` + `status:` stripped — start over) | **you** |
| escalation valve: `track: fast` → `track: spec` + gate reset | main agent, atomically |
| abnormal stop → `blocked` (+ issue comment) | the stopping command |
| `blocked` cleared after you decide | main agent, at your direction |
| labels retire at close | the closing merge — (7), or your fast-CR merge; patrol's **close-out** finishes it (labels off, issue closed) where the forge does not do it on merge |

**Invocation policy.** Workflow commands are executed by the main agent and —
except `/roz-gate:to-issues`, which you always initiate (the inbox's async
intake is likewise initiated by you, by filing the raw issue) — do not wait
for you to type them. A patrol pass (`/roz-gate:patrol`, run manually, on a loop, or on
a schedule) sends one **read-only scanner sub-agent** to classify every open
issue into a table (`references/patrol-scan.md` — the single home of the
classification rules; the forge reads stay in the scanner's context, not the
main agent's) and invokes the right command per that table; it acts on one in-loop issue per pass (closest
to done) and then triages the **whole inbox** (intake is comment-only, so
every batch of questions lands in a single pass), treats `processing` as a
lock, never applies a gate label, and stops to report anything unexpected.

**Command lifecycle & the STOP protocol.** Every state-mutating command takes
the `processing` lock on entry and leaves through exactly one of two exits.
**Done:** work complete, lock removed. **STOP:** it hit something it cannot or
should not decide: (1) remove the command's worktree(s) — the uncommitted local
work lives nowhere else; (2) replace the issue's
status labels with `blocked` alone; (3) post an issue comment — what happened,
where it died, what already exists remotely, a recommended next step — as the
**must-read, at most 12 rendered lines before the first `<details>`** (a
phone's ~60 characters per line; a long line counts for several), with the
evidence (logs, command output, diffs) folded below it in one
`<details><summary>Evidence</summary>` block; the human on a phone reads the
decision first and opens the evidence only to check it. No third
exit. A stale `processing` therefore means exactly one thing — a killed run —
and the phase label next to it says where.

**(7) is the one stage with no `blocked` exit**, and for a reason that does not
generalize: `blocked` means *an automated step stopped and needs you*, which is
where the issue already is. Setting it would also delete `in-user-review` — the
only label saying this work passed the verdict — and keeping both would be an
illegal double status. So at (7) a failure is a `**[review] · question**`
saying what could not be done: the prefix makes it non-actionable until you
reply, which is exactly what `blocked` would have bought.

## Principles

- **QA tests a contract, not raw implementation.** HTTP API → the API doc;
  otherwise the implementer provides a documented **test port** as part of the
  contract. The test port is the front door for features with no natural
  external interface (scheduled jobs, bot commands, internal services): a
  small, stable, documented driver the acceptance tests call instead of
  importing internals — control points to drive the behaviour (e.g.
  `advance_clock(minutes)`, `run_expiry_sweep()`) and observation points to
  read its externally observable outcomes (e.g. `get_offer_state(id)`). It is
  **specified in `technical-spec.md` at stage (2)** — that is what lets QA
  write its suite in parallel with the build — and implemented by the
  implementer at stage (3) with the same obligations as a public API: stable,
  documented, behaviour-only. A port that exposes internal state or models
  "for convenience" re-couples QA to the implementation and is a contract
  defect — QA should report it, not use it. **A port that under-exposes a
  promised observation point is the same defect in the other direction** —
  QA reports it, never works around it or silently downgrades the scenario
  to uncovered. (In hexagonal-architecture terms: a driving port whose actor
  is the acceptance suite.)
- **The verdict lives at integration, by design.** (3) and (4) run in parallel
  and never see each other; that independence is what makes the verdict honest.
- **Tooling:** `/roz-gate:to-issues` (1, 1a — dispatches `product` under the
  intake brief); `/roz-gate:next-stage` (2, 3+4+5, or
  fast — routed by labels, printing the workflow map first);
  `/roz-gate:spec-answers` (2a); `/roz-gate:integrate` (6);
  `/roz-gate:review-answers` (7 — one turn of your review conversation);
  `/roz-gate:patrol` — one polling pass that auto-invokes the commands above
  and triages the inbox ((1b)). The merge at the end of (7) is yours.
