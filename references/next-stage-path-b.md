# next-stage — Path B

Routed here by `commands/next-stage.md` §4: `track: spec` + `status: ready-for-dev`.
You have read that file's §0–4 (config, forge adapter, branch names,
workspace, invariants, the map); they hold here. The STOP exit and the
one-issue rule are at the end of `commands/next-stage.md`.

## Path B — implementation + review (3)+(5)

The spec CR (`<spec-branch>`) must already exist and be approved (its Q&A threads
resolved). If `<spec-branch>` does not exist, stop and say so. Since 2.0.0 this
path builds and reviews the implementation **only**; QA starts in Path B2
once the implementation has landed on `<spec-branch>` (#140).

**Passed-stage check (first, read-only):** Lookup `<feat-branch>`
(`references/branch-names.md`); a match → CR-FIND it in the all-states
form. **Merged into the bound `<spec-branch>`** (its base; an earlier
`{seq}` attempt's merged CR targets an earlier spec branch — history, not
this stage) → the stage this label gates has passed: B6 consumed it
and the implementation has landed, so the label was applied again
(ConsoleAPI #27, #209). Take no lock and write nothing — **not** the STOP
exit, whose resume line would have the holder re-apply the label this
check refuses — and report the CR, its state, and the remedy: **remove
`status: ready-for-dev`, nothing else**; patrol's next pass resumes from
the CRs (Path B2, integrate). Open → continue: a STOP's resume line
re-applies the label over an open CR, and step B2 reuses the branch. Closed
unmerged, or no CR → a re-implementation; continue.

**Reserved-word check (before anything else but the passed-stage check):**
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
since-you-approved diff. **Deferred questions resolve by default here**
(#206): every `## Open Questions` item whose title ends `· deferred` and
carries no `**Resolved:**` block is resolved to its recommended option by
this label — append to the same kit line `resolved by default: Q<k> →
(<option>), …` — and the implementer's dispatch (B3) says so: a rule or
contract line born from a deferred item carries `(assumed)` as its
provenance, never `(from Q<k>)`. Also note in the report whether the spec
changed after the kit's last update (the gate-produced-change signal,
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
  deviation to declare: it is the ambiguity below. **Deferred questions**
  (#206): a `· deferred` item in `## Open Questions` with no
  `**Resolved:**` block is resolved to its recommended option by the gate
  label (B2); build to that option, and a contract line born from it
  carries `(assumed)` as its provenance.
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
  (`git diff <spec-branch>...<feat-branch>`), **attaching the seat's R&R
  row, `<specs_dir>/<n>/spec.md` and `technical-spec.md`** — the reviewer's
  mandate is "does it do what it claims", so it receives the claim; it
  never reviews code against its own inference of intent. It wraps
  `/code-review` where available. Attach too the **as-built contract
  diff** (`git diff origin/<spec-branch>...<feat-branch> -- <specs_dir>/<n>/technical-spec.md`)
  and the CR's `## Contract deviations`: the reviewer checks every deviation
  against `spec.md`'s rules — a deviation the list omits, or one that moves
  an `R<k>`, is a finding.
- Post the findings and the record per
  `${CLAUDE_PLUGIN_ROOT}/references/code-review-mechanics.md` — read it now.
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
