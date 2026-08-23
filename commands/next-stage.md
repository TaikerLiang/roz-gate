---
description: Advance one gated issue to its next stage — spec refinement (2), parallel impl+QA (3+4+5), or the fast track — routed by its labels; prints the workflow map first
argument-hint: "[issue-number]"
---

Advance **one** issue to its next stage (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`). Route by the issue's labels;
follow the matched path's steps exactly and do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (`forge`,
`default_branch`, `test`, `env_sync`, `lockfile`, `specs_dir`,
`acceptance_dir`). Then read `${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md`
and use its concrete CLI for every CAPITALIZED-OP below. Label names follow the
adapter's scheme (GitLab uses scoped forms). If the config block is missing,
stop and tell the user to run `/roz-gate:init`. **Personas**: every role
dispatch below (`em`, `product`, `implementer`, `qa`, `reviewer`) resolves
through the `### Roz Gate personas` block — dispatch the mapped subagent,
attaching the seat's R&R row from
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its contract. Block missing
→ plugin defaults (`roz-gate:<role>`; implementer = the project's
`implementer` agent).

## 1. Select the issue
- If an issue number was passed (`$ARGUMENTS`), target that issue. Verify it
  carries a gate label (`status: ready-for-spec` or `status: ready-for-dev`);
  if not, stop and say so.
- Otherwise ISSUE-LIST filtered by each gate label, excluding any issue that
  also carries `status: processing`.
  - None → report "no gated issues" and stop.
  - Several → list them, pick the **oldest**.

## 2. Validate the label invariants (before anything else)
- Exactly **one** `track:` label. Zero or two → stop and report.
- `track: fast` + `status: ready-for-spec` is **illegal** (fast has no spec
  stage) → stop and report.
- Never repair labels yourself — a violation stops here and is reported.

## 3. Print the workflow map
Show the whole workflow with the issue's current position and what this run
will do, THEN act:

`track: spec`:
```
(1) intake → (2) spec → (2a) Q&A → (3)(4) impl+QA → (5) review → (6) integrate → (7) main
                ▲ #<n> is here — ready-for-spec: running spec refinement now
```
`track: fast`:
```
(1) intake → (3') implement (main agent) → (5) review → merge to main
                ▲ #<n> is here — ready-for-dev: implementing now
```

## 4. Route
| Labels | Path |
|---|---|
| `track: spec` + `status: ready-for-spec` | **A — spec refinement (2)** |
| `track: spec` + `status: ready-for-dev` | **B — impl + validation (3)+(4)+(5)** |
| `track: fast` + `status: ready-for-dev` | **C — fast track** |

---

## Path A — spec refinement (2)

### A1. Lock
LABEL-ADD `status: processing`.

### A2. Branch
Create `spec/<n>` from `<default_branch>` (`git fetch` first).

### A3. Spec refinement (NO implementation code)
Base everything strictly on the issue body. Per the workflow's stage (2):
- Dispatch `em` and `product` → write `<specs_dir>/<n>/spec.md`.
- Dispatch `implementer` → write `<specs_dir>/<n>/technical-spec.md` (the
  contract: command/API spec, schema, behavioral guarantees; a documented test
  **port** for non-API features).
- **Rules enumeration requirement:** `spec.md` MUST enumerate its
  story-level rules exhaustively and number them — `R<k> · <2–4-word
  title>`, one entry per behavioural rule or guarantee; scenarios cite the
  rules they exercise. Each rule carries a **provenance annotation**:
  `(from Q<j>)` — ruled by the gate holder's answer to that question;
  `(from AC-<j>)` — carried from the issue's acceptance criteria;
  `(assumed)` — resolved to a recommendation nobody confirmed. The
  enumeration is the spec's own content in numbered form — never a second
  prose copy that can drift from it. `technical-spec.md` numbers its
  clauses the same way — `G<k>` for guarantees (citing parent rules:
  `G6 (R6, S6)`), `C<k>` for every other normative clause — so that
  tags, findings, and the §5 walk below have stable anchors to attach to;
  anchor-free contract prose cannot be cited, audited, or kept current.
- **Evidence annotations — rulings are not claims.** Two kinds of
  sentence share the spec's typography and must not share its authority.
  The test is **jurisdiction**: *can the implementer be ordered to make
  this sentence true?* Yes → it is a requirement — a ruling or a
  guarantee about the system being built, enforced by (4) and (6) like
  any other. No → it describes **pre-existing reality** (current DB
  behaviour, lock contention, a third-party library, how today's code
  behaves), and writing it down does not make it true. Every such
  empirical claim carries an evidence tag:
  - `(measured, <date>, <scope one-liner>)` — measured by the
    `implementer` (the only spec-stage seat allowed in the codebase),
    with the scope that bounds the claim (`measured 2026-08-20, 15 runs,
    dev db n≈10k`) and a link to what was run wherever one exists. The
    date says when; the scope is the falsifier.
  - `(unverified)` — asserted, load-bearing, and nobody has checked. The
    honest state of a draft; **illegal to sign** (Path B refuses to
    start while one exists).
  - `(assumed-empirical: <named risk>)` — the demotion: not measured,
    accepted as an assumption with its risk stated. Distinct from
    `(assumed)`, which marks an unconfirmed *decision*; this marks an
    unmeasured *fact*, and the holder's action differs (order a
    measurement vs confirm a choice).
  Placement: one authority tag on a rule's title line; evidence tags sit
  on the empirical premise itself, in the rationale italics, with the
  measurement citation. Authority tags say *who decided*; evidence tags
  say *how we know* — they never compete for the same clause. Any
  mechanical check of these tags matches the **opening token only** —
  `(unverified)`, `(assumed-empirical:`, `(measured` — because tags with
  free text wrap at the document's line width: requiring the closing
  paren on the same line makes the miss silent on exactly the tag whose
  purpose is to be seen, and a wrapped `(measured …` a checker cannot
  fully parse is a *present* tag, never read as absent.
- **Scenario boundary:** scenario text states observable behaviour from
  an actor's observation surface — Given/When/Then only. Content
  addressed to another seat (test guidance, review guidance, "recorded so
  QA does not chase it") is a rule, or a note under the rule it derives
  from, never a scenario: an unfalsifiable scenario pollutes the
  coverage map, the evidence cards, and the (5q) audit permanently.
- **Port observability walk:** when the `implementer` designs the test
  port (§5), it walks every `spec.md` scenario once and appends the
  result to §5 as a per-scenario table — `S<k>` ×
  {observable / observable via `<control point>` / limitation: `<why>`}.
  A gap found here is a port fix on the spot; a **limitation is a verdict
  exemption**, and the implementer never grants its own: every
  limitation row is surfaced on the spec-gate kit's attention list for
  the gate holder to countersign. This table is what test-spec.md's
  "not testable through the port" section verifies at (4) instead of
  discovering.
- **ID citation convention:** wherever any agent cites a rule, scenario, or
  question ID in a comment, thread, or report, the first mention in that
  comment is written in full — `R7 · Expired offers don't count`, linked to
  the ID's definition line — never the bare code. The reader may be on a
  phone with no lookup table in their head.
- **Open Questions requirement:** `spec.md`'s `## Open Questions` section is
  the **single collection point for every seat's open questions**, whatever
  document the seat owns — (2a)'s threads anchor here and nowhere else, so a
  question written anywhere else has no route to the gate holder. Seats never
  write the section directly (em owns `spec.md`; concurrent writes and
  self-assigned numbers would break `(from Q<j>)` provenance): each dispatch
  **returns its question batch in its report**, and the main agent appends
  them — em/product first, implementer after — assigning `Q<k>` append-only
  for the life of the issue. The owning document may carry a pointer to a
  Q-ID; it never carries the question body. Each item uses the intake batch
  shape — phone-readable, and reused verbatim as its thread body in A6:
  - Title line `**[<role>] · Q<k> · <2–3-word label>**` — role = who raised
    it (`[product]`, `[em]`, or `[implementer]`; combine if more than one);
    items that challenge the user story / acceptance criteria append
    **(story-level)** to the title line.
  - Blank line, then the question as **one sentence**.
  - The options as **(a)/(b) bullets** — mark the recommended one
    `← ✅ recommended`; an option needing detail says so inline
    ("(b) a subset → say which").
  - The why as **one italic line**.

### A4. Commit + push
Commit the two spec docs on `spec/<n>` and push. If a pre-commit hook fails on
something unrelated to the spec docs (e.g. lockfile drift), commit with
`--no-verify` (these are docs-only) and say so.

### A5. Open the CR
CR-OPEN from `spec/<n>` targeting `<default_branch>`, title
`Spec: #<n> <title>`, body: "Stage (2) spec refinement for #<n>. For review.
Refs #<n>".

### A6. Post open questions as inline review threads
**Sweep first:** check the other spec docs for question-shaped content (an
open-questions section, unresolved "TBD"/"open:" items). Found → relocate it
verbatim into `spec.md`'s `## Open Questions`, tagged with the raising role,
before posting anything — a question outside the threaded surface is invisible
to every gate that counts threads, and resolves the only way it can: silent
interpretation. Then, for EACH item in the `## Open Questions` section of
`spec.md`:
THREAD-POST-INLINE on the spec CR, anchored to that item's line in
`<specs_dir>/<n>/spec.md`, body = **the item verbatim** (title line, blank
line, question, option bullets with the marked recommendation, italic why —
A3 already shaped it).
- **Every agent question comment MUST start with `**[`** — `/roz-gate:spec-answers`
  uses that marker to tell agent comments from the user's replies. The A3
  title line satisfies this by construction.
- For **(story-level)** items, end the body with one more italic line: *"If
  your decision changes the user story, I will mirror a note to issue #<n>."*

### A6b. Post the spec-gate kit
Assemble the **spec-gate kit** per
`${CLAUDE_PLUGIN_ROOT}/references/gate-kit.md` (blind-spot header,
attention list, issue-delta, decision ledger — ledger entries exist only
if intake carried rulings) and post it as **one top-level comment** on
the spec CR. This comment is the kit's permanent home — every later
update edits it in place (COMMENT-EDIT), never posts a sibling.

### A7. Flip labels — only AFTER the CR and threads are created
LABEL-REMOVE `status: ready-for-spec` and `status: processing`;
LABEL-ADD `status: in-spec-review`.

### A8. Report
Print the CR URL and the list of open-question threads. Never write code beyond
the two spec docs. **Next:** the user answers the threads;
`/roz-gate:spec-answers` folds them in; when all are resolved, the user
applies `status: ready-for-dev`.

---

## Path B — implementation + validation (3)+(4)+(5)

The spec CR (`spec/<n>`) must already exist and be approved (its Q&A threads
resolved). If `spec/<n>` does not exist, stop and say so.

**Unverified-claim check (before anything else):**
`grep -nE '(^|[(,])[[:space:]]*unverified' <specs_dir>/<n>/*.md` — the
widened pattern also catches a tag illegally merged into another
parenthesis (`(from Q4, unverified)`) and a wrap-split compound, both of
which the bare literal `(unverified)` misses; the two-axis writing rule
(A3) is the first line of defense, this grep the second. Any hit → the
STOP exit, listing
the claims, recommendation: measure (implementer, at (2) cost) or demote to
`(assumed-empirical: <named risk>)`. This is the signing moment — B2 stamps
the approval — and it is the only gate that can reach the false-GREEN branch:
a claim false only under conditions the acceptance run never produces passes
(4), (5q) and (6), because **a faithful transcription of a falsehood
satisfies fidelity**. Zero hits in a spec that carries evidence tags is a
clean check; zero hits in a spec written before the vocabulary existed is
**not** — say which one the report means.

### B1. Lock
LABEL-ADD `status: processing`.

### B2. Stamp the approval + two sibling branches off the spec branch
The gate label just applied is the human's approval of `spec/<n>` **as it
stands**: COMMENT-EDIT the spec-gate kit to append one line —
`approved at <spec/<n> HEAD SHA>` — the anchor for the final-gate kit's
since-you-approved diff. Also note in the report whether the spec changed
after the kit's last update (the gate-produced-change signal,
gate-kit.md § Instrumentation).
`git fetch` first, then create both off `spec/<n>`:
- `feat/<n>` (implementer) and `qa/<n>` (qa). They are **independent
  siblings** — `qa/<n>` must contain NO implementation code; that is what
  enforces the black box.

### B3. Dispatch implementer AND qa IN PARALLEL
Launch both at once (they never see each other):
- **implementer** on `feat/<n>`: implement per
  `<specs_dir>/<n>/technical-spec.md` + write **unit** tests. For a non-API
  feature, also provide the documented test **port** QA tests against.
  **A contract gap you cannot resolve from the spec docs → stop and report
  to the main agent; never decide unilaterally in code** — the same
  mid-flight route QA has, and the ambiguity takes the same backward
  transition through the spec CR.
- **qa** on `qa/<n>`: write black-box acceptance tests in
  `<acceptance_dir>/<feature>/` (`<feature>` = the project's layout unit —
  config `acceptance_layout`; absent → one folder per feature) from
  `spec.md` + the contract ONLY. **`test-spec.md` required shape**: its
  scenario→test map must be **derivable from machine-readable trace
  markers in the test source** (marker syntax = config `trace_marker`;
  absent → qa picks one idiomatic to the language and declares it at the
  top of `test-spec.md`) — never hand-maintained; each scenario maps to
  ≥1 test or an explicit `uncovered` row with a reason. These run
  post-integration and will NOT pass on `qa/<n>` by design — write them against
  the contract, do not chase green here.
  **The §5 observability map is a claim to verify, never a fact to
  inherit:** walk every scenario against the port yourself, then
  reconcile with the implementer's §5 table — every mismatch, both
  directions, is a mandatory reported finding (map says observable, you
  cannot drive it → contract defect; map says not-observable, you can →
  an over-declared limitation shrinking the testable surface). Each
  `uncovered / not testable through the port` row in `test-spec.md`
  cites the §5 limitation row it corresponds to; a row with no §5
  citation is a contract defect and takes the ambiguity route — never a
  silent `uncovered` entry.

### B4. Commit + push + open both CRs (target = the spec branch)
- Commit each branch's files and push. Use `--no-verify` only for unrelated
  pre-commit drift, and say so.
- CR-OPEN for `feat/<n>` targeting `spec/<n>`, title `feat: implement #<n>`;
  CR-OPEN-DRAFT for `qa/<n>` targeting `spec/<n>`, title
  `test: #<n> black-box (QA)`. **Both target `spec/<n>`.**
- **The QA CR opens as a draft.** CR-READY only if `qa` reported its suite
  complete; a partial — or paused — deliverable stays draft. Draft = QA still
  working/paused; ready = complete. This is the machine-readable signal
  `/roz-gate:patrol` and `/roz-gate:integrate` key on.

### B5. Code review (5) on the implementation CR
- Dispatch the **reviewer** agent on the CR's diff
  (`git diff spec/<n>...feat/<n>`), **attaching
  `<specs_dir>/<n>/spec.md` and `technical-spec.md`** — the reviewer's
  mandate is "does it do what it claims", so it receives the claim; it
  never reviews code against its own inference of intent. It wraps
  `/code-review` where available.
- Post its findings as severity-graded inline threads on the implementation CR —
  THREAD-POST-INLINE, body starts
  `**[reviewer] · blocking|should-fix|nit|question**`, anchored to file:line.
  Rule/scenario IDs in a finding follow the citation convention (A3): first
  mention carries the ID's title and a link to its definition.
- **A finding that is really a contract ambiguity routes to a spec-CR
  thread through the main agent** (the (2a) machinery) — never settled
  reviewer-to-implementer on the implementation CR, where the contract
  stays unamended, the decision never reaches the ledger, and QA keeps
  testing the old text. (The fidelity brief already routes
  scenario-meaning disputes this way; the same rule applies here.)

### B5b. QA fidelity review (5q) on the QA CR
- Dispatch the **reviewer** seat a second time, in a **fresh context**
  (never a continuation of B5's), with
  `${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md` as its contract,
  on a `qa/<n>` checkout — that branch contains no implementation code,
  which is what makes this dispatch structurally implementation-blind.
- It audits the QA suite's fidelity to the spec (four questions:
  scenario fidelity, vacuous assertions, coverage honesty, over-assertion)
  and posts two-way-cited findings as inline threads on the **QA CR**
  plus one top-level summary comment. Its findings are evidence for the
  human, never a verdict.
- Runs alongside B5 — it needs only `qa/<n>`, so it costs no wall-clock.

### B6. Flip labels + report
- LABEL-REMOVE `status: ready-for-dev` and `status: processing` (the open CRs
  are now the in-flight state).
- Report the implementation CR, the QA CR, and the open threads on both.
  **Next:** `implementer` addresses the implementation CR's threads; `qa`
  addresses the QA CR's fidelity threads, and a **fresh implementation-blind
  reviewer dispatch re-checks and resolves** what it is satisfied with
  (patrol's address-review engine — the audited party never closes the
  audit's findings). All resolved on both → `/roz-gate:integrate <n>`.

---

## Path C — fast track

The main agent implements this itself (the one R&R exception). No spec branch,
no QA branch, no integration stage — the guards are unit tests, CI, the
reviewer, and the user's CR review.

### C1. Lock
LABEL-ADD `status: processing`.

### C2. Branch
Create `fast/<n>` from `<default_branch>` (`git fetch` first).

### C3. Implement — with the escalation valve armed
- Make the minimum change that satisfies the issue's acceptance criteria. A bug
  fix MUST carry a unit test reproducing it.
- **Escalation valve:** the moment this stops being trivial — a real design
  decision, user-facing behaviour beyond the issue's AC, a growing diff — STOP.
  Relabel atomically: LABEL-REMOVE `track: fast`, `status: ready-for-dev`,
  `status: processing`; LABEL-ADD `track: spec`, `status: ready-for-spec`.
  Delete `fast/<n>` if empty, and report why it escalated. The issue rejoins
  the loop at (2).

### C4. Verify
Run the affected tests plus the existing suite (config `test`). The suite must
stay green before opening the CR.

### C5. Commit + push + open the CR (target = default branch)
CR-OPEN from `fast/<n>` targeting `<default_branch>`, title
`fast: #<n> <title>`, body ending `Closes #<n>`.

### C6. Code review (5)
- Dispatch the **reviewer** agent on `git diff <default_branch>...fast/<n>`,
  **attaching the issue body** (story + acceptance criteria — the claim the
  diff is reviewed against) — same inline-thread mechanics as B5. The main
  agent wrote this code, so the reviewer is the independent check; it is NOT
  skippable — except for **doc-only** diffs.

### C7. Flip labels + report
- LABEL-REMOVE `status: ready-for-dev` and `status: processing`.
- Report the CR and any review threads. **Next:** address review threads; once
  all are resolved (review-clean), LABEL-ADD `status: in-user-review` — then
  the user reviews and merges the CR; merging closes the issue.
  `/roz-gate:integrate` does not apply.

---

Process exactly **one** issue per run.

**Failure = the STOP exit.** If any step after the lock fails — or you hit
anything this command cannot or should not decide — follow the STOP protocol
(`references/workflow.md` → The main agent): discard uncommitted local work, replace
the issue's status labels with `status: blocked` alone, and post the issue
comment. This command **creates remote artifacts as it goes**, so the comment
must inventory what already exists — branches pushed, CRs opened, partial
deliverables committed — say which step it died on, and recommend how to
continue. The escalation valve (C3) is **not** a failure — it is a designed
transition and never uses the STOP exit.
