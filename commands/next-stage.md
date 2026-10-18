---
description: Advance one issue to its next stage — spec refinement (2), implementation + review (3+5), validation once the implementation has landed (4+5q), or the fast track — routed by its labels and CR state; prints the workflow map first
argument-hint: "[issue-number]"
---

Advance **one** issue to its next stage (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`). Route by the issue's labels —
and, for the one path that starts from an in-flight issue (B2), by its CRs;
follow the matched path's steps exactly and do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (or CLAUDE.local.md) (`forge`,
`test`, `env_sync`, `lockfile`, `specs_dir`, `acceptance_dir`,
`branch_template`). **Local keys** — `default_branch`, `inbox_label`,
`inbox_assignee`, `helper_model`, `branch_user` are per person,
per clone, never in the block: run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-config --json`
and use its values (`.claude/roz-gate.local.json`, defaults resolved — the
remote's HEAD branch, empty lists, empty strings).
`default_branch` is the loop's **base**: `<spec-branch>` and `<fast-branch>` are cut from
it and their CRs target it; `<feat-branch>` and `<qa-branch>` stay siblings off
`<spec-branch>`. **Bind the branch names** — `<spec-branch>`, `<feat-branch>`,
`<qa-branch>`, `<fast-branch>` — per
`${CLAUDE_PLUGIN_ROOT}/references/branch-names.md`: the block's
`branch_template` (absent → `{kind}/{n}`), an existing branch found by
**Lookup**, a new one rendered by **Expand**; an invalid template is a STOP
before any cut. Nothing below spells a branch name. Then read `${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md`
and use its concrete CLI for every CAPITALIZED-OP below. Label names follow the
adapter's scheme (GitLab uses scoped forms). If the config block is missing,
stop and tell the user to run `/roz-gate:init`. **Personas**: every role
dispatch below (`em`, `product`, `implementer`, `qa`, `reviewer`) resolves
through the `### Roz Gate personas` block — dispatch the mapped subagent,
attaching the seat's R&R row from
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its contract. Block missing
→ plugin defaults (`roz-gate:<role>`; implementer = the project's
`implementer` agent).

**Workspace.** Every git step below runs in a linked worktree, never in the
user's checkout (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → The main
agent → The workspace): `git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> …`
at the branch step, `cd` there (or `git -C`) for everything after, and
`git worktree remove --force` + `git worktree prune` on **both** exits.
`git worktree add` refusing because the branch is checked out elsewhere →
another command holds it → STOP.

## 1. Select the issue
- If an issue number was passed (`$ARGUMENTS`), target that issue. Verify it
  carries a gate label (`status: ready-for-spec` or `status: ready-for-dev`)
  — or is **in flight on `track: spec` with no `status:`**, the entry of
  Path B2 (its CRs decide, §4); anything else → stop and say so.
- Otherwise ISSUE-LIST filtered by each gate label, excluding any issue that
  also carries `status: processing`.
  - None → report "no gated issues" and stop. (Path B2 is reached by
    number only — patrol's `next-stage (qa)` row passes it; this command
    never scans for it.)
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
(1) intake → (2) spec → (2a) Q&A → (3) impl → (5) review → (4) QA → (5q) → (6) integrate → (7) main
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
| `track: spec` + `status: ready-for-dev` | **B — implementation + review (3)+(5)** |
| `track: spec`, no `status:`, the implementation CR **review-clean or merged**, no QA CR (CR-FIND, all-states form) | **B2 — validation (4)+(5q)** — the one route read from CR state; the scanner computes it (`actionable: next-stage (qa)`), a human may run it |
| `track: fast` + `status: ready-for-dev` | **C — fast track** |

---

## Path A — spec refinement (2)

### A1. Lock
LABEL-ADD `status: processing`.

### A2. Branch
**The branch may already exist** — a previous attempt at this stage. Before
the cut, **Lookup** the spec kind of #<n> (`git ls-remote --heads origin`
matched against the template — `references/branch-names.md`). A match →
CR-FIND (all-states form) its CR: **open** → illegal state, **STOP** (someone
is still reviewing it; the gate label is wrong, not the branch); **closed
unmerged, or no CR** → this is a **re-spec**, and the route is the
template's. It carries **`{seq}`** → `<spec-branch>` is the **next sequence**
(Expand); the previous attempt stays on the remote, readable in its closed
CR — cite it in the report — and the cut below proceeds. It carries **no
`{seq}`** → the stale branch is the
human's to remove: **STOP**, and the `blocked` comment and the report carry
the remedy verbatim — `git push origin --delete <spec-branch>` (and `<feat-branch>` / `<qa-branch>` if present) — *the human
runs this; the agent never does*: an agent never deletes or force-pushes a
remote branch, and the previous attempt stays readable in its closed CR
(cite it). The resume line reads: run the delete, then re-apply the gate label; the next pass cuts fresh (the cut
uses `-B`, so the previous attempt's local ref cannot block it).

Create `<spec-branch>` from `<default_branch>` **in a worktree** —
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> -B <spec-branch> origin/<default_branch>` (`-B`, not `-b`: after a re-spec the previous attempt's **local** `<spec-branch>` ref may survive its removed worktree, and `-B` resets it onto the base; a local ref is not a remote branch — the invariant is untouched; a `-B` refused because the branch is checked out elsewhere is the mutex, a STOP)
— and work there from here on (`git fetch --prune` first — a stale tracking ref would pass the check for a base the forge deleted; then verify `origin/<default_branch>` exists — `git rev-parse --verify -q origin/<default_branch>` — and if it does not, **STOP**: the base the config names is not on the remote; never cut from anything else).

### A3. Spec refinement (NO implementation code)
Base everything strictly on the issue body. Per the workflow's stage (2):
- Dispatch `em` and `product` → write `<specs_dir>/<n>/spec.md`.
- Dispatch `implementer` → write `<specs_dir>/<n>/technical-spec.md` (the
  contract: command/API spec, schema, behavioral guarantees; a documented test
  **port** for non-API features). **The test-port line** (#125):
  `technical-spec.md` carries exactly one line `**Test port** — <path>[,
  <path>…]` — the repo-relative files or directories the port lives in;
  the acceptance suite drives it, and it is the one thing under `src/`
  the blind reviewer may read — or `**Test port** — none` when the contract
  is an API doc. Path B refuses to start without the line, and B5b
  copies its paths into the dispatch marker; a port that lives in an
  existing unit-test file is declared there all the same (ADMC #11).
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
    start while one exists). **`unverified` is a reserved word** in every
    spec document: it appears only as this tag. Prose says *not yet
    measured* or *asserted* — the checks match the whole word anywhere,
    so the word loose in a sentence stops the gate exactly as the tag
    does, and the remedy is to reword it, never to wave it through as a
    false positive (#123). The registry of reserved words is
    `${CLAUDE_PLUGIN_ROOT}/references/reserved-words.md`.
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
  fully parse is a *present* tag, never read as absent. For `unverified`
  the match is the whole word, anywhere: the word is reserved, so no
  prose position needs telling apart.
- **Must-read / supplement requirement:** each spec document is two
  parts. The **must-read** is on top and stands alone — for `spec.md`:
  `## Rules`, `## Scenarios`, `## Open Questions`, with **at most 3 lines
  per rule** (title line + rationale italics); for `technical-spec.md`:
  the numbered clauses (`G<k>`/`C<k>`) and the §5 port table. Everything
  else — background, current-state surveys, glossary, design notes,
  alternatives considered, worked examples — is the **supplement**: a
  trailing `## Supplement` section whose body is one
  `<details><summary>Supplement — <what it holds></summary>` block, and
  the last must-read line points at it ("Details in the supplement
  below."). A reader who needs more opens it; a reader who does not never
  scrolls past it. Section headings, rule and clause IDs, tags and the
  §5 table keep their exact shapes — the fold changes placement, never
  the things the hooks and checkers parse.
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
    ("(b) a subset → say which"). One bullet per option, never prose: the
    forge renders consecutive lines as one paragraph, and guard-gate
    denies a question comment without them (rule F, #109).
  - The why as **one italic line**.

### A4. Commit + push
Dispatch the **commit** sub-agent (the plugin default `general-purpose`, on
`helper_model` from `bin/roz-config --json` when set; it dispatches nothing
itself) with, as its whole prompt,
`${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the `<spec-branch>` worktree
path, the branch, the two spec docs and the commit message. It returns one
`branch · sha · hook` row; the pre-commit output stays in its context, not
yours. Push `<spec-branch>` from the returned `sha`; a `no-verify:` row is said
so in the report; a `failed:` row is a STOP with its excerpt in the report.

### A5. Open the CR
CR-OPEN from `<spec-branch>` targeting `<default_branch>`, title
`Spec: #<n> <title>`, body: "Stage (2) spec refinement for #<n>. For review.
Closes #<n>" — the (7) merge of this CR is the signature that closes the
issue; where the forge does not close on it, patrol's close-out does.

### A6. Post open questions as inline review threads
**Sweep first:** check the other spec docs for question-shaped content (an
open-questions section, unresolved "TBD"/"open:" items). Found → **move** it:
copy it verbatim into `spec.md`'s `## Open Questions`, tagged with the raising
role, and **delete it from the source document** — the section goes; at most a
one-line pointer to the Q-ID stays (A3's rule: the owning document never
carries the question body). A copy left behind is a second home for the same
text, and two homes drift — and guard-gate denies the commit mechanically
while a `technical-spec.md` under `<specs_dir>` still holds the section (the
deny message is the remedy). Do this before posting anything — a question
outside the threaded surface is invisible to every gate that counts threads,
and resolves the only way it can: silent interpretation. Then, for EACH item
in the `## Open Questions` section of `spec.md`:
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

### A6c. Remove the worktree
`git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch>`
then `git worktree prune` — `<spec-branch>` is on the remote; nothing local stays.

### A7. Flip labels — only AFTER the CR and threads are created
LABEL-REMOVE `status: ready-for-spec` and `status: processing`;
LABEL-ADD `status: in-spec-review`.

### A8. Report
Print the CR URL and the list of open-question threads. Never write code beyond
the two spec docs. **Next:** the user answers the threads;
`/roz-gate:spec-answers` folds them in; when all are resolved, the user
applies `status: ready-for-dev`.

---

## Path B — implementation + review (3)+(5)

The spec CR (`<spec-branch>`) must already exist and be approved (its Q&A threads
resolved). If `<spec-branch>` does not exist, stop and say so. Since 2.0.0 this
path builds and reviews the implementation **only**; QA starts in Path B2
once the implementation has landed on `<spec-branch>` (#140).

**Reserved-word check (before anything else):**
`grep -nwi unverified <specs_dir>/<n>/*.md` — the whole word, anywhere:
`unverified` is reserved for the evidence tag (A3), so its own parenthesis,
a tag merged into another (`(from Q4, unverified)`), a wrap-split compound
and the word loose in a sentence are all hits, and nothing a line break can
do hides one; the two-axis writing rule (A3) is the first line of defense,
this grep the second. Any hit → the STOP exit, listing the hits, the
recommendation by what each is — a tag: measure (implementer, at (2) cost)
or demote to `(assumed-empirical: <named risk>)`; the word in prose: reword
the sentence (the gate reads words, not intent — #123). This is the signing
moment — B2 stamps
the approval — and it is the only gate that can reach the false-GREEN branch:
a claim false only under conditions the acceptance run never produces passes
(4), (5q) and (6), because **a faithful transcription of a falsehood
satisfies fidelity**. Zero hits in a spec that carries evidence tags is a
clean check; zero hits in a spec written before the vocabulary existed is
**not** — say which one the report means.

**Test-port check (beside it):**
`grep -nE '^\*\*Test port\*\* — ' <specs_dir>/<n>/technical-spec.md` —
exactly one hit, reading `none` or a comma-separated list of repo-relative
paths (A3's line). Zero hits, two or more, or a value that is neither →
the STOP exit, naming the line's shape; the remedy is the implementer's at
(2) cost — a spec written before the line existed (1.40.0-) has none and
gains one here. Its paths are what the QA dispatch (B2.4) and the fidelity dispatch
(B2.7) write into the marker as `read=` lines (#125).

### B1. Lock
LABEL-ADD `status: processing`.

### B2. Stamp the approval + cut the implementation branch off the spec branch
The gate label just applied is the human's approval of `<spec-branch>` **as it
stands**: COMMENT-EDIT the spec-gate kit to append one line —
`approved at <<spec-branch> HEAD SHA>` — the anchor for the final-gate kit's
since-you-approved diff. Also note in the report whether the spec changed
after the kit's last update (the gate-produced-change signal,
gate-kit.md § Instrumentation).
`git fetch` first, then create `<feat-branch>` off `<spec-branch>` **in its own
worktree** (`<feat-branch>`: Lookup — a previous B run's
branch is reused — else Expand):
- `git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<feat-branch> -B <feat-branch> origin/<spec-branch>`
  (implementer). The seat is dispatched **into its worktree** (its cwd); it
  never sees the user's checkout. No `<qa-branch>` is cut here: QA's branch
  is cut from the spec tip **after** the implementation lands (B2.3).

### B3. Dispatch the implementer
- **implementer** on `<feat-branch>`: implement per
  `<specs_dir>/<n>/technical-spec.md` + write **unit** tests. For a non-API
  feature, also provide the documented test **port** QA tests against, at
  the path(s) `technical-spec.md`'s `**Test port**` line names — **with the
  Given-state control points** §5 lists for every scenario's setup: QA never
  persists entities or touches the persistence layer, so a Given with no
  control point is a contract defect it will report (#140).
  **The contract as built**: correct `technical-spec.md` on `<feat-branch>`
  as you build — a `G<k>` / `C<k>` clause, a §5 row — in the same CR as the
  code, and return the list of every change (clause, what changed, why) for
  the CR's `## Contract deviations` section; `none` when nothing changed. A
  correction that would move what a **rule** (`R<k>`) means is not a
  deviation to declare: it is the ambiguity below.
  **A contract gap you cannot resolve from the spec docs → stop and report
  to the main agent; never decide unilaterally in code** — the same
  mid-flight route QA has, and the ambiguity takes the same backward
  transition through the spec CR.

### B4. Commit + push + open the implementation CR (target = the spec branch)
- Commit the branch's files through the **commit** sub-agent — one dispatch,
  on `helper_model` when set,
  `${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the
  worktree path, branch, files and message (the hook rules and the
  `branch · sha · hook` return live in the brief, nowhere else) — then push
  from its returned `sha`. A `no-verify:` row is said so in the report;
  a `failed:` row is a STOP with its excerpt in the report.
- CR-OPEN for `<feat-branch>` targeting `<spec-branch>`, title `feat: implement #<n>`.
  The body carries a fixed section **`## Contract deviations`** — the
  implementer's list, one bullet per changed clause (`G<k>` / `C<k>` / a §5
  row): what changed and why; or the single line `none`. Guard-gate rule H
  denies a CR-OPEN whose diff touches `<specs_dir>/*/technical-spec.md` and
  whose body lacks the heading — the section is where the (5) reviewer and
  the (4) and (5q) dispatches learn what the contract became.

### B5. Code review (5) on the implementation CR
- Dispatch the **reviewer** agent on the CR's diff
  (`git diff <spec-branch>...<feat-branch>`), **attaching
  `<specs_dir>/<n>/spec.md` and `technical-spec.md`** — the reviewer's
  mandate is "does it do what it claims", so it receives the claim; it
  never reviews code against its own inference of intent. It wraps
  `/code-review` where available. Attach too the **as-built contract
  diff** (`git diff origin/<spec-branch>...<feat-branch> -- <specs_dir>/<n>/technical-spec.md`)
  and the CR's `## Contract deviations`: the reviewer checks every deviation
  against `spec.md`'s rules — a deviation the list omits, or one that moves
  an `R<k>`, is a finding.
- Post its findings as severity-graded inline threads on the implementation CR —
  THREAD-POST-INLINE, body starts
  `**[reviewer] · blocking|should-fix|nit|question**`, anchored to file:line.
  Rule/scenario IDs in a finding follow the citation convention (A3): first
  mention carries the ID's title and a link to its definition.
- **The record — posted last, even with zero findings**: one top-level
  CR-COMMENT opening with `**[reviewer] · code-review**`, carrying
  `reviewed-sha: <the CR head SHA reviewed>` on its own line and the finding
  count by severity (`blocking 1 · should-fix 0 · nit 2 · question 0`). It is
  the **record that the review ran**: zero threads because nobody reviewed
  is not zero findings (#95's lesson, now on the implementation side —
  #140 ruling 9). **Review-clean** is defined in `workflow.md` (5) and read
  everywhere else: the record present **and** its `reviewed-sha` equal to
  the CR head **and** zero open review threads. A head pushed after
  `reviewed-sha` without a re-check is a stale record — patrol's
  `code-review` action re-runs the review; its address-review re-check
  re-stamps `reviewed-sha` (COMMENT-EDIT) when the last thread resolves.
- **A finding that is really a contract ambiguity routes to a spec-CR
  thread through the main agent** (the (2a) machinery) — never settled
  reviewer-to-implementer on the implementation CR, where the contract
  stays unamended, the decision never reaches the ledger, and QA keeps
  testing the old text. (The fidelity brief already routes
  scenario-meaning disputes this way; the same rule applies here.)

### B6. Remove the worktree, flip labels + report
- `git worktree remove --force` `…/roz-gate/wt/<feat-branch>`, then
  `git worktree prune`.
- LABEL-REMOVE `status: ready-for-dev` and `status: processing` (the open CR
  is now the in-flight state).
- Report the implementation CR, its open threads and its record.
  **Next:** `implementer` addresses the threads (patrol's address-review
  engine; the reviewer re-checks, resolves what satisfies it, re-stamps the
  record). **Review-clean** — the record current, zero threads — is the
  scanner's `actionable: next-stage (qa)` row: `/roz-gate:next-stage <n>`
  runs **Path B2**, which lands the implementation on `<spec-branch>` and
  launches (4)+(5q). A CR with no `**[reviewer] · code-review**` record, or a
  stale one, is patrol's `code-review` action first.

---

## Path B2 — validation (4)+(5q), once the implementation has landed

Entered from an in-flight `track: spec` issue (no `status:`) whose
implementation CR is **review-clean or merged** and which has **no QA CR**
yet — the row the scanner computes as `actionable: next-stage (qa)`. This
path merges the review-clean implementation into `<spec-branch>`, cuts
`<qa-branch>` off the new tip, dispatches `qa` under
`${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md` with guard-blind rule E on,
posts QA's contract-review findings as `[qa]` threads on the spec CR, opens
the QA CR as a draft, and runs the fidelity review (5q). The spec CR
(`<spec-branch>`) must exist; the two Path B checks above already passed at
`ready-for-dev` and are not re-run.

### B2.1 Lock + preconditions
LABEL-ADD `status: processing`. Then, read-only: CR-FIND **in its all-states
form** (`--state all` / `--all`) for `<feat-branch>` and `<qa-branch>`.
- A QA CR exists in any state → not this path's entry: unlock and report
  (an open one is address-review / fidelity-audit / integrate territory).
- No implementation CR → unlock and report (Path B never ran, or its CR was
  closed unmerged).
- The implementation CR `merged` → the implementation is already in
  `<spec-branch>`; B2.2 merges nothing.
- The implementation CR `open` → it must be **review-clean**
  (`workflow.md` (5)): CR-COMMENTS-LIST carries a `**[reviewer] · code-review**`
  comment whose `reviewed-sha:` equals the CR's head (`git ls-remote --heads origin <feat-branch>`),
  **and** THREADS-LIST shows zero open review threads. Any of the three
  missing → unlock and report which: no record or a stale one is patrol's
  `code-review` action, open threads are address-review — never merge on
  zero threads alone (#95; #140 ruling 9).

### B2.2 Land the implementation on the spec branch
`git fetch`, then
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> <spec-branch>`
and work **in that worktree** (`cd` there or `git -C`); a refusal (the branch
is checked out elsewhere) → the STOP exit. First `git merge --ff-only origin/<spec-branch>`:
the worktree starts at the **remote's** tip, never at a stale local ref (a
ref that cannot fast-forward → the STOP exit, naming both SHAs). Then, unless
the implementation CR is already merged, `git merge --no-edit origin/<feat-branch>`
— the implementation and its as-built `technical-spec.md` land together. **Any
conflict** (the usual one: an as-built edit of `technical-spec.md` on
`<feat-branch>` against a `spec-answers` fold on `<spec-branch>`), or a failure
of config `env_sync` → the **STOP exit**: the conflicting files in the
must-read, nothing pushed. Then push `<spec-branch>` — the forge marks the
implementation CR merged. This is the one remote write of the loop that lands
code before a verdict: the verdict is (6)'s, and `<spec-branch>` is the
feature's umbrella, merged to the default branch only at (7).

### B2.3 Cut the QA branch off the new tip
`git fetch`, then create `<qa-branch>` off `<spec-branch>` **in its own
worktree** (`<qa-branch>`: Lookup — a previous run's branch is reused — else
Expand):
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<qa-branch> -B <qa-branch> origin/<spec-branch>`.
The branch **carries the implementation** — that is the point of the order,
and it is why the next step's blindness is the hook's, not the topology's.

### B2.4 The QA dispatch procedure
- **Contract currency, by you — not blind** (the same step the fidelity
  dispatch takes): THREADS-LIST on the implementation CR and on the spec
  CR. A thread that settled a contract question on the implementation CR is
  the (5) breach — route it to a spec-CR thread through you, LABEL-ADD
  `status: in-spec-review` (the backward transition), and **do not
  dispatch**; the paused side resumes through (2a). Otherwise assemble two
  lists for the dispatch text: the **amendment list** — every amendment
  agreed in spec-CR threads and issue comments since `technical-spec.md`'s
  last commit, under the heading `Amendment list:`, one line per amendment,
  `<what> — folded at <ID>` or `<what> — unfolded`, or the single line
  `Amendment list: none since <sha>` — and the **deviations**: the
  implementation CR's `## Contract deviations` section, copied **verbatim**
  from its body (CR-VIEW with `body` among the fields) under the heading
  `Contract deviations:` (or `Contract deviations: none`). QA never opens the
  implementation CR — its threads quote the code QA must not see — so the
  copy is how the as-built changes reach it.
- **Blindness is hook-enforced while the dispatch runs** (guard-blind,
  rule E): immediately before the dispatch, write the marker
  `mkdir -p "$(git rev-parse --git-common-dir)/roz-gate" && printf 'issue=<n>\nfeat=<feat-branch>\nread=<path>\nseat=<seat>\n' > "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"`
  — `feat=` is the bound implementation branch, the ref the hook denies by
  name; one `read=<path>` line per path the `**Test port**` line
  of `technical-spec.md` names (none when it says `none`); `seat=qa` here
  (the hook names the dispatch in its deny message). The dispatch text
  carries the same paths on a line of its own, `Test port: <path>[, <path>]`
  or `Test port: none`. Immediately after it returns,
  `rm -f "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"`.
  While the marker exists, every read of `src/` outside
  `<acceptance_dir>` and the port the marker names, and every git action on
  `<feat-branch>` (or any `feat/` ref), is denied mechanically, with the
  remedy in the message — QA may run `acceptance_test` in its worktree all
  it likes; it may not read the code it runs against.
- Dispatch **qa** in the `<qa-branch>` worktree with
  `${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md` as its contract, the seat's
  R&R row, the two lists and the `Test port:` line. It returns: the
  step-zero **finding batch** (contradictions, untestable clauses, port
  gaps — or `none`), the suite, `test-spec.md`, the result of its last run,
  and whether the suite is **complete**. A red it classified as an assertion
  that disagrees with observed behaviour arrives as a finding, never as an
  edited assertion (the brief's rule; the fidelity audit checks it).

### B2.5 QA's findings → threads on the spec CR
For a non-empty batch: append each item to `spec.md`'s `## Open Questions`
in the `<spec-branch>` worktree — A3's shape, `Q<k>` assigned append-only by
you, role `[qa]` — commit it through the **commit** sub-agent and push
`<spec-branch>`; then THREAD-POST-INLINE each item verbatim on the spec CR,
anchored to its line (every agent question comment starts with `**[`; the
options are `- (a)` / `- (b)` bullets — rule F). LABEL-ADD
`status: in-spec-review`: the backward transition. The answers fold through
`/roz-gate:spec-answers`, whose mid-flight re-entry re-dispatches `qa` with
the amended contract. QA did not stop — the scenarios the batch does not
touch are already written — so B2.6 still opens its CR. An empty batch
writes nothing here.

### B2.6 Commit + push + open the QA CR (target = the spec branch)
- Commit the QA branch's files through the **commit** sub-agent — one
  dispatch, on `helper_model` when set,
  `${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the worktree path,
  branch, files and message — then push from its returned `sha`; a
  `no-verify:` row is said so in the report; a `failed:` row is a STOP with
  its excerpt in the report.
- CR-OPEN-DRAFT for `<qa-branch>` targeting `<spec-branch>`, title
  `test: #<n> black-box (QA)`. **The QA CR opens as a draft.** CR-READY only
  if `qa` reported its suite complete **and** B2.5 posted no thread (no
  `[qa]` thread is open); a partial deliverable, or one waiting on a
  `Q<k>`, stays draft. Draft = QA still working/paused; ready = complete.
  This is the machine-readable signal `/roz-gate:patrol` and
  `/roz-gate:integrate` key on.

### B2.7 QA fidelity review (5q) on the QA CR
- **Contract currency, by you — not blind.** B2.4's listing is yours and
  stands; re-run THREADS-LIST on the spec CR if B2.5 posted threads — an
  item still open is not an amendment yet. Put the **amendment list** in
  the dispatch text **in this shape**: the heading `Amendment list:`, then one
  line per amendment, `<what> — folded at <ID>` or `<what> — unfolded`; or
  the single line `Amendment list: none since <sha>` when there is none —
  and the `Contract deviations:` block B2.4 copied. A
  mention is not a list — the reviewer aborts on anything else. The
  reviewer verifies them against the contract and never opens the
  implementation CR (its threads quote the code the reviewer must not see).
  The listing is **yours**, in your own context — the scanner's read of the
  CRs while classifying is not this check.
- Dispatch the **reviewer** seat in a **fresh context** (never a
  continuation of B5's), with
  `${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md` as its contract,
  in the `<qa-branch>` worktree — a branch that, since 2.0.0, carries the
  implementation, which is why the marker below is what makes the dispatch
  implementation-blind.
- **Blindness is hook-enforced while the dispatch runs** (guard-blind,
  rule E): immediately before the dispatch, write the marker
  `mkdir -p "$(git rev-parse --git-common-dir)/roz-gate" && printf 'issue=<n>\nfeat=<feat-branch>\nread=<path>\nseat=<seat>\n' > "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"`
  — the `feat=` line is the bound implementation branch, the ref the hook
  denies by name; one `read=<path>` line per path the `**Test port**` line
  of `technical-spec.md` names (Path B's check read it; no `read=` line
  when it says `none`) — the port the hook lets the dispatch read beside
  the suite (#125); `seat=reviewer` here; the dispatch text carries the same
  paths on a line of
  its own, `Test port: <path>[, <path>]` or `Test port: none`. Immediately
  after it returns,
  `rm -f "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"`.
  While the marker exists, every read of `src/` outside
  `<acceptance_dir>` (a suite under `src/test/…` stays readable — it is
  what the dispatch audits; so is the port the marker's `read=` lines
  name) and every git action on
  `<feat-branch>` (or any `feat/` ref) is denied mechanically, with the
  remedy in the message. The
  brief's "you never read the implementation" stays in the dispatch text —
  the marker is what makes it a fact. This is **the fidelity-dispatch
  procedure** — the contract-currency step, the marker, the dispatch, the
  marker off; every implementation-blind dispatch on `<qa-branch>` uses it
  (the QA dispatch of B2.4 is the same procedure under the QA brief).
- It audits the QA suite's fidelity to the spec (four questions:
  scenario fidelity, vacuous assertions, coverage honesty, over-assertion)
  and posts two-way-cited findings as inline threads on the **QA CR**
  plus one top-level summary comment opening with `**[reviewer] · fidelity**`
  — the record that the audit ran, which integrate requires and patrol's
  `fidelity-audit` action produces when B2.7 never did. Its findings are
  evidence for the human, never a verdict.

### B2.8 Remove the worktrees, unlock + report
- `git worktree remove --force` both `…/roz-gate/wt/<spec-branch>` and
  `…/roz-gate/wt/<qa-branch>`, then `git worktree prune` — after B2.7's marker
  is gone, never while it is on.
- LABEL-REMOVE `status: processing` only. `status: in-spec-review`, when B2.5
  applied it, stays: the QA CR is the in-flight state and the threads are
  the human's.
- Report: the implementation landed at `<sha>` (or was already merged), the
  QA CR (draft or ready), the `[qa]` threads posted, the open fidelity
  threads. **Next:** the human answers the `[qa]` threads
  (`/roz-gate:spec-answers` folds them and resumes `qa`); `qa` addresses the
  QA CR's fidelity threads, and a **fresh implementation-blind reviewer
  dispatch re-checks and resolves** what it is satisfied with (patrol's
  address-review engine — the audited party never closes the audit's
  findings). QA CR ready, audited and thread-clean → `/roz-gate:integrate <n>`
  merges it and runs the recorded verdict. A QA CR with no
  `**[reviewer] · fidelity**` record is patrol's `fidelity-audit`.

---

## Path C — fast track

The main agent implements this itself (the one R&R exception). No spec branch,
no QA branch, no integration stage — the guards are unit tests, CI, the
reviewer, and the user's CR review.

### C1. Lock
LABEL-ADD `status: processing`.

### C2. Branch
**The branch may already exist** — a previous attempt at this stage. Before
the cut, **Lookup** the fast kind of #<n> (`git ls-remote --heads origin`
matched against the template — `references/branch-names.md`). A match →
CR-FIND (all-states form) its CR: **open** → illegal state, **STOP** (someone
is still reviewing it; the gate label is wrong, not the branch); **closed
unmerged, or no CR** → this is a **re-spec**, and the route is the
template's. It carries **`{seq}`** → `<fast-branch>` is the **next sequence**
(Expand); the previous attempt stays on the remote, readable in its closed
CR — cite it in the report — and the cut below proceeds. It carries **no
`{seq}`** → the stale branch is the
human's to remove: **STOP**, and the `blocked` comment and the report carry
the remedy verbatim — `git push origin --delete <fast-branch>` — *the human
runs this; the agent never does*: an agent never deletes or force-pushes a
remote branch, and the previous attempt stays readable in its closed CR
(cite it). The resume line reads: run the delete, then re-apply the gate label; the next pass cuts fresh (the cut
uses `-B`, so the previous attempt's local ref cannot block it).

Create `<fast-branch>` from `<default_branch>` **in a worktree** —
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<fast-branch> -B <fast-branch> origin/<default_branch>` (`-B`, not `-b`: after a re-spec the previous attempt's **local** `<fast-branch>` ref may survive its removed worktree, and `-B` resets it onto the base; a local ref is not a remote branch — the invariant is untouched; a `-B` refused because the branch is checked out elsewhere is the mutex, a STOP)
— and work there from here on (`git fetch --prune` first — a stale tracking ref would pass the check for a base the forge deleted; then verify `origin/<default_branch>` exists — `git rev-parse --verify -q origin/<default_branch>` — and if it does not, **STOP**: the base the config names is not on the remote; never cut from anything else).

### C3. Implement — with the escalation valve armed
- Make the minimum change that satisfies the issue's acceptance criteria. A bug
  fix MUST carry a unit test reproducing it.
- **Escalation valve:** the moment this stops being trivial — a real design
  decision, user-facing behaviour beyond the issue's AC, a growing diff — STOP.
  Relabel atomically: LABEL-REMOVE `track: fast`, `status: ready-for-dev`,
  `status: processing`; LABEL-ADD `track: spec`, `status: ready-for-spec`.
  Delete `<fast-branch>` if empty, and report why it escalated. The issue rejoins
  the loop at (2).

### C4. Verify
Run the affected tests plus the existing suite (config `test`). The suite must
stay green before opening the CR.

### C5. Commit + push + open the CR (target = default branch)
Commit through the **commit** sub-agent, on `helper_model` when set —
`${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the `<fast-branch>` worktree
path, branch, files and message; it returns one `branch · sha · hook` row and
the pre-commit output stays out of your context. Push from the returned
`sha` (`no-verify:` → say so; `failed:` → STOP with the excerpt). Then
CR-OPEN from `<fast-branch>` targeting `<default_branch>`, title
`fast: #<n> <title>`, body ending `Closes #<n>`.

### C6. Code review (5)
- Dispatch the **reviewer** agent on `git diff origin/<default_branch>...<fast-branch>`,
  **attaching the issue body** (story + acceptance criteria — the claim the
  diff is reviewed against) — same inline-thread mechanics as B5, **and the
  same record**: one top-level `**[reviewer] · code-review**` comment with
  `reviewed-sha: <head>` and the counts, posted last, even with zero
  findings — patrol's hand-off to `in-user-review` reads it (review-clean =
  record current + zero threads, `workflow.md` (5)). The main
  agent wrote this code, so the reviewer is the independent check; it is NOT
  skippable — except for **doc-only** diffs (a doc-only CR carries the record
  all the same, with `skipped: doc-only` in place of the counts).

### C7. Remove the worktree, flip labels + report
- `git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<fast-branch>`
  then `git worktree prune`.
- LABEL-REMOVE `status: ready-for-dev` and `status: processing`.
- Report the CR and any review threads. **Next:** address review threads; once
  review-clean (the record current, zero threads), LABEL-ADD `status: in-user-review` — then
  the user reviews and merges the CR; merging closes the issue (patrol's
  close-out finishes it where the forge does not).
  `/roz-gate:integrate` does not apply.

---

Process exactly **one** issue per run.

**Failure = the STOP exit.** If any step after the lock fails — or you hit
anything this command cannot or should not decide — follow the STOP protocol
(`references/workflow.md` → The main agent): `git worktree remove --force` every
worktree this run created (then `git worktree prune`) — never touch the user's
checkout — replace
the issue's status labels with `status: blocked` alone, and post the issue
comment. This command **creates remote artifacts as it goes**, so the comment
must inventory what already exists — branches pushed, CRs opened, partial
deliverables committed — say which step it died on, and recommend how to
continue; that is the must-read, the evidence folds under
`<details><summary>Evidence</summary>`. The must-read opens with
`**[next-stage] · blocked**` and ends with the resume line — **To resume:**
clear `status: blocked`, apply the gate label this run consumed
(`status: ready-for-spec` or `status: ready-for-dev`) — yourself, or tell the
main agent; nothing to answer — run the remedy first, if there is one. Path
B2 consumed no gate label (it entered from in flight): its line reads
**To resume:** clear `status: blocked` — nothing else; patrol's next pass
re-runs it, or run `/roz-gate:next-stage <n>`. A B2.2 STOP names the
conflicting files and says nothing was pushed. The escalation valve (C3) is **not** a failure — it is a designed
transition and never uses the STOP exit.
