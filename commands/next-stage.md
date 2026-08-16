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
  prose copy that can drift from it.
- **ID citation convention:** wherever any agent cites a rule, scenario, or
  question ID in a comment, thread, or report, the first mention in that
  comment is written in full — `R7 · Expired offers don't count`, linked to
  the ID's definition line — never the bare code. The reader may be on a
  phone with no lookup table in their head.
- **Open Questions requirement:** each item in `spec.md`'s `## Open Questions`
  section uses the intake batch shape — phone-readable, and reused verbatim as
  its thread body in A6:
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
For EACH item in the `## Open Questions` section of `spec.md`:
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
  **Next:** `implementer` addresses the implementation CR's threads and
  `qa` addresses the QA CR's fidelity threads until all resolved, then
  `/roz-gate:integrate <n>`.

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
