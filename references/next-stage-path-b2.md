# next-stage — Path B2

Routed here by `commands/next-stage.md` §4: `track: spec`, no `status:`, the implementation CR
review-clean or merged, no QA CR.
You have read that file's §0–4 (config, forge adapter, branch names,
workspace, invariants, the map); they hold here. The STOP exit and the
one-issue rule are at the end of `commands/next-stage.md`.

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
  edited assertion (QA-4; the fidelity audit checks it).

### B2.5 QA's findings → threads on the spec CR
For a non-empty batch: append each item to `spec.md`'s `## Open Questions`
in the `<spec-branch>` worktree — A3's shape, `Q<k>` assigned append-only by
you, role `[qa]` — commit it through the **commit** sub-agent and push
`<spec-branch>`; then THREAD-POST-INLINE each item verbatim on the spec CR,
anchored to its line (every agent question comment starts with `**[`; the
options are `- (a)` / `- (b)` bullets — rule F). LABEL-ADD
`status: in-spec-review`: the backward transition. The answers fold through
`/roz-gate:spec-answers`, whose mid-flight re-entry re-dispatches `qa` with
the amended contract. QA did not stop — every scenario the contract can drive
is already written, a questioned one included (only an undrivable scenario
waits) — so B2.6 still opens
its CR. An empty batch
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
  `${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md` as its contract and
  the seat's R&R row, in the `<qa-branch>` worktree — a branch that, since 2.0.0, carries the
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
