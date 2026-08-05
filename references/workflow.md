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
| **main agent** | proxy + accountable for all output; intake: dispatches `product` under the intake brief, relays its questions verbatim, publishes the confirmed story; orchestration, git/forge mechanics, integration; decides the next step; implements `track: fast` changes itself | act as a specialist on any clarification or `track: spec` work (it dispatches) |
| **product** | actors, scenarios (Given/When/Then: happy/edge/failure), consistency, user-facing gaps | architecture, code, impl tests |
| **em** | problem statement, success metrics, architecture / domain boundaries, business rules, out-of-scope; resolves conflicts; owns `spec.md` | code, deep implementation |
| **implementer** | `technical-spec.md` (the contract); implementation code + **unit** tests; the QA test **port** for non-API features | spec scenarios, black-box tests, reviewing its own code |
| **qa** | black-box acceptance tests from `spec.md`'s scenarios + the contract **only — never the implementation**; `test-spec.md`; the integration verdict — reports **only to the main agent** | reading the implementation, unit tests, architecture |
| **reviewer** | independent review of the **implementation code** (correctness / security / performance / maintainability); severity-graded inline comments | architecture (em's), re-testing behaviour (qa's), writing code |

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
it. Patrol triages it entirely through issue comments, mirroring (2a): the
`product` agent (under the same intake brief, **async mode**) drafts **all open
clarifying questions as one batched comment** — numbered, each with a
recommendation, prefixed `**[intake]**` — because a comment round trip costs a
day, not seconds; answers arrive as replies (`all recs`, `1a 2b`, or free
text) from any device. The thread is open to anyone, but the **gate holder** —
the issue's assignee (unassigned → the author) — is the sole authority: their
answers settle questions, conflicting feedback comes back as a **digest** for
them to decide, and once clear the **proposal comment** (rewritten story + AC
+ proposed `track:`) files only on **their** `approve`. The gate label is
still theirs. Same invariants as `/roz-gate:to-issues`; async medium, batched
questions.

**(2) Spec refinement** — gated by `status: ready-for-spec`. `em`+`product`
write `<specs_dir>/{n}/spec.md`; `implementer` writes `technical-spec.md`
(the contract: command/API spec, schema, behavioral guarantees). Opens the
**spec CR** (`spec/{n}`) for your review; the spec CR **stays open** as the
feature umbrella for the whole feature.

**(2a) Open-question Q&A loop** — open questions are posted as inline review
threads on the spec CR, each tagged with the role that raised it. You answer
inline; the fold command re-spawns that role agent, folds the decision into
`spec.md`, and resolves the thread. A resolution that changes the user story →
a comment on the issue (it never auto-edits the issue body/AC). Gate: all
threads resolved.

**(3) Implementation + (4) Validation — launch together**, gated by
`status: ready-for-dev`. Independent siblings, both branched off `spec/{n}`,
both CRs targeting the spec CR:
- **(3)** `implementer` on `feat/{n}` → implementation code + **unit** tests.
- **(4)** `qa` on `qa/{n}` → `test-spec.md` + black-box tests in
  `<acceptance_dir>/<feature>/`. The qa branch carries **no implementation
  code** — that structurally enforces the black box: QA tests the **contract**
  (or a provided port), never the raw implementation. Tests are a living,
  feature-organized suite — never per-issue folders/tags. The QA CR opens as a
  **draft** and is marked ready only when the suite is complete —
  ready-not-draft is the completeness signal integration waits for.

If QA hits a contract ambiguity mid-flight, it stops and reports to the main
agent — it never interprets. The main agent distills the question and its
recommendation into an inline thread on the still-open spec CR; the affected QA
work pauses and the issue re-enters `status: in-spec-review` (the one backward
transition). The decision folds in through (2a)'s machinery; the label clears
and QA resumes.

**(5) Code review** — on the implementation CR. `reviewer` posts
severity-graded inline comments (`blocking` / `should-fix` / `nit` /
`question`); `implementer` addresses them; loop until **all review threads
resolved**.

**(6) Integration = the verdict.** Once the implementation CR is review-clean
and the QA CR is ready, the main agent merges **both** into `spec/{n}` and runs
QA's black-box tests against the implementation **for the first time**.
Pass/fail is the verdict on whether the implementation matches the spec — this
is where genuine bugs surface.

**(7) Merge** — after a green (6), the main agent brings the default branch
into `spec/{n}` (resolving conflicts on the feature branch so the spec CR's
diff stays clean), then sets `status: in-user-review`: nothing is left but your
review. You review the spec CR, it merges, and the issue is closed.

## The fast track (`track: fast`)

Skips (2), (2a), (4) and (6). Picked up from `status: ready-for-dev`:
- The **main agent implements directly** on `fast/{n}` off the default branch;
  one CR targeting the default branch. This is the one R&R exception.
- The guards replacing QA: a bug fix must carry a unit test reproducing it, the
  existing suite must stay green, **(5) still applies** (skippable for doc-only
  diffs), and you review and merge the CR yourself. Once review-clean the main
  agent sets `status: in-user-review`; merging closes the issue.
- **Escalation valve:** the moment the change stops being trivial (a real
  design decision, user-facing behaviour, a growing diff) — stop and relabel
  atomically: `track: fast` → `track: spec`, gate back to
  `status: ready-for-spec`; the issue rejoins the loop at (2).

## Label state machine

- An open issue with **no `track:` label** is the **inbox** ((1b)) — pre-loop,
  not a violation: invisible to every command except patrol's async intake.
- Every open issue in the loop has **exactly one `track:` label** (applied at
  intake; only the escalation valve changes it) and **at most one `status:`
  label besides the `processing` lock** — the lock is a mutex, not a phase:
  while a command runs, `processing` coexists with the phase label it locks (a
  stale pair tells you exactly which stage a killed run died in).
- Gate states (waiting for a command): `spec`+`ready-for-spec`,
  `spec`+`ready-for-dev`, `fast`+`ready-for-dev`. Transient states:
  `processing` (locked by a running command), `in-spec-review` (spec CR
  awaiting you — or re-entered mid-flight on a QA ambiguity; the one backward
  transition), `in-user-review` (finished work awaiting your final review),
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

The bridge between you and the team, both directions, and the owner of state
management under one rule: **you move gate labels — a gate label is an
authorization; agents and commands move transient labels — a transient label is
a status report. Neither ever moves the other's.**

| Transition | Owner |
|---|---|
| `track:` label at intake | `/roz-gate:to-issues` (interactive) or the (1b) proposal comment (async) proposes — **you** confirm either way |
| raw idea → inbox issue (no labels) | **you** (e.g. the forge's mobile app) |
| inbox → in the loop (body rewrite + `track:` label) | patrol's async intake, only after the **gate holder's** (issue assignee's; unassigned → author's) `approve` comment |
| apply a gate label (`ready-for-spec`, `ready-for-dev`) | **you**, only ever you |
| gate → `processing` → next state | the running command |
| (2) complete → `in-spec-review` | the spec stage |
| `in-spec-review` → `ready-for-dev` (all threads resolved) | **you** |
| in flight → `in-spec-review` (backward; QA ambiguity) | main agent |
| → `in-user-review` (both tracks) | main agent |
| escalation valve: `track: fast` → `track: spec` + gate reset | main agent, atomically |
| abnormal stop → `blocked` (+ issue comment) | the stopping command |
| `blocked` cleared after you decide | main agent, at your direction |
| labels retire at close | the closing merge — (7), or your fast-CR merge |

**Invocation policy.** Workflow commands are executed by the main agent and —
except `/roz-gate:to-issues`, which you always initiate (the inbox's async
intake is likewise initiated by you, by filing the raw issue) — do not wait
for you to type them. A patrol pass (`/roz-gate:patrol`, run manually, on a loop, or on
a schedule) reads each open issue's worn state and invokes the right command
per its classification table; it acts on one in-loop issue per pass (closest
to done) and then triages the **whole inbox** (intake is comment-only, so
every batch of questions lands in a single pass), treats `processing` as a
lock, never applies a gate label, and stops to report anything unexpected.

**Command lifecycle & the STOP protocol.** Every state-mutating command takes
the `processing` lock on entry and leaves through exactly one of two exits.
**Done:** work complete, lock removed. **STOP:** it hit something it cannot or
should not decide: (1) discard uncommitted local work; (2) replace the issue's
status labels with `blocked` alone; (3) post an issue comment — what happened,
the evidence, what already exists remotely, a recommended next step. No third
exit. A stale `processing` therefore means exactly one thing — a killed run —
and the phase label next to it says where.

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
  defect — QA should report it, not use it. (In hexagonal-architecture terms:
  a driving port whose actor is the acceptance suite.)
- **The verdict lives at integration, by design.** (3) and (4) run in parallel
  and never see each other; that independence is what makes the verdict honest.
- **Tooling:** `/roz-gate:to-issues` (1, 1a — dispatches `product` under the
  intake brief); `/roz-gate:next-stage` (2, 3+4+5, or
  fast — routed by labels, printing the workflow map first);
  `/roz-gate:spec-answers` (2a); `/roz-gate:integrate` (6);
  `/roz-gate:patrol` — one polling pass that auto-invokes the commands above
  and triages the inbox ((1b)); (7) is a plain forge merge by you.
