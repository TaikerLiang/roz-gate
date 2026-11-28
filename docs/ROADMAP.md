# Roadmap — the 2.0.0 question

A complete record of the 2.0.0 deliberation (2026-08-10 → 08-11), written
so any future session can resume it cold. This documents **potential**
direction, not commitment: Paul deferred the 2.0.0 decision; v1.7.x
shipped the parts that stood on their own.

## The quality-audit track (added 2026-08-16, after the first closed loop)

ADMC #63 closed the first full spec-track loop (intake → spec Q&A ×9 →
parallel impl+QA → review → mid-flight contract amendment → green
integration) — **condition 1 of the report's three is met**. The gate
holder's pain points became a proposal package; a four-seat evaluation
(product/em/qa/reviewer, independent dispatches) produced this pipeline:

- **v1.8.0 (shipped)**: reviewer dispatch now receives the spec docs (was
  reviewing against its own inference); integrate gains the third RED
  class — *contract defect* (faithful assertion, reality disagrees →
  STOP → amend → QA re-derives; "a RED is never resolved by editing a QA
  assertion to match observed behaviour"); exhaustive numbered rules
  `R<k>` with provenance `(from Q<j>)`/`(from AC-<j>)`/`(assumed)`;
  titled+linked ID citations.
- **v1.9.0 (shipped) — QA fidelity review (stage 5q)**:
  `references/fidelity-brief.md` (four questions, 12-item checklist,
  origin rule, contract-currency step zero, two-way citations, three
  dispositions); B5b blind dispatch on `qa/<n>`; patrol routes QA-CR
  threads through address-review (qa addresses, blind reviewer
  re-checks); integrate gains the symmetric thread-clean precondition;
  R&R reviewer row updated; `test-spec.md` map derived from
  machine-readable trace markers (`trace_marker` config; qa declares one
  if absent).
- **v1.10.0 (shipped) — gate-holder legibility**:
  `references/gate-kit.md` (binding rules, sections, computed sort keys,
  four coverage buckets); one kit comment per spec CR edited in place
  (new COMMENT-EDIT forge op, both adapters); posted at A6b, ledger
  updated by spec-answers 6b, approved-SHA stamped at B2 (+ the
  gate-produced-change instrumentation line), final-gate extension at
  integrate green finalize (evidence cards from captured run output +
  since-you-approved annotated diff). Success metric: artifact-change
  rate at gates, not approval rate.
- **v1.11.0 (shipped) — stage (7) gets a listener, then a host**. Field
  defect #5, found the hard way: `in-user-review` was a terminal-wait row
  in patrol's table, so three of Paul's comments on ADMC #63 sat a day.
  1.10.0 had just given (7) a *reading* surface with no *hearing* one —
  and a kit that works generates comments. Four evaluation rounds
  (ADMC strawman → seats → two reframes by Paul) landed here:
  - **(7) is a discussion stage hosted by the main agent**, not a
    routing problem. It answers by quotation (verbatim + permalink at a
    SHA, or marked *interpretation:*), dispatches a seat for any *new*
    judgment, reads a change back before making it, and acts only on the
    user's word. Silence is never consent; 👍 confirms a single-change
    readback only. `/roz-gate:review-answers`, ranked above integrate;
    answer-only turns exempt from the one-issue-per-pass rule.
  - **Detection**: three channels (threads + review bodies + top-level
    comments — REVIEWS-LIST and CR-COMMENTS-LIST are new adapter ops),
    track-aware CR, and the agent-marker test widened to `**[` / `✅ [`.
    That bracket is load-bearing twice: a human's own `✅ 看起來可以` is
    the highest-value message in the channel and the old test swallowed
    it, and the prefix invariant is also the livelock brake — a readback
    that opens with a quote block makes the conversation answer itself
    every pass. Only the main agent writes to the CR.
  - **Seat-on-edit**: any resolution that would edit a file gets one
    seat opinion *before* the readback. Trigger on the act (a fact), not
    on whether the comment implies behaviour change (a judgment the
    boundary rule reserves for the specialist). It is the only mechanism
    at (7) that puts a failure branch in front of the gate holder.
  - **The hook** (`hooks/guard-acceptance.*`, new PreToolUse matcher on
    Edit|Write|MultiEdit): acceptance files are not editable on a
    `spec/*` branch. Branch-and-path only — no stage detection, no
    exemption list — so "the main agent is not exempt" becomes
    unstatable rather than merely stated. (7) is the one stage with no
    adversarial second party: the main agent hosts, authors, commits,
    runs the verdict and assembles the page the human reads.
    Verified against ADMC's history before shipping: zero commits
    authored on a `spec/*` branch have ever touched the acceptance dir.
    **If you re-audit that claim, the query is
    `git log --no-merges spec/<n> ^qa/<n> -- <acceptance_dir>`** — the
    natural form without `^qa/<n>` lists everything the qa merge brought
    in and returns a convincing false positive.
  - **The hand-back rule**, named in workflow.md and cited from
    integrate 5.2 and (7): any SHA wearing `in-user-review` has a
    captured green *full* acceptance + unit run at that SHA, cards
    regenerated wholesale (matched pair), `cards-sha` stamped. The claim
    it licenses is weakened to *"green against the pre-rework spec, at
    SHA `<x>`"* — a weaker claim needs fewer guards to stay true.
  - **Back to intake** as a first-class outcome: strip `track:` and
    `status:` and the issue is the inbox again, ledger intact and
    carried forward as prior answers to confirm. Redoing work is cheap;
    re-answering rulings is not.
  - Prose: stage (7) renamed **Merge → Review** (label unchanged);
    *"nothing is left but your review"* deleted; (7) has **no `blocked`
    exit** (it is already at the human's gate). Also fixed a live defect
    the design exposed: `spec-answers` step 7 had no post-integration
    branch and told a shipped feature it was "ready to move to
    implementation".
  - **The exchange rate that decided the shape** (Paul's ruling —
    "重做在 AI 的時代裡面代價是很小的", never forget the start-over path
    — sharpened by the seats into a usable test): *cheap redo reprices
    guards against failures whose artifact is **silent**; it does not
    reprice guards against failures whose artifact **affirmatively
    asserts something false***, because the start-over strategy runs on
    a signal it would destroy. Corollary: *redo is cheap up to merge —
    the gate is the last cheap point.* Applying it deleted three rounds
    of accreted protocol (offer formats, offer IDs, confirmation
    grammars, roll-calls, routing tables) — one of which had
    reintroduced an approve keyword the project deliberately removed at
    intake.
- **v1.12.0 (shipped) — the spec artifacts learn what kind of sentence
  they hold**. ADMC reviewed #63's artifact set end to end and sent three
  findings; four seats amended all three. The meta-lesson, ADMC's own
  words on receiving it: their findings "patched where the failure
  appeared rather than where the class lives" — each was one stage
  narrower than the failure class (their keep: *when a finding names one
  stage and one seat, check the same failure at every other stage and
  seat before proposing*).
  - **Question routing**: `spec.md`'s `## Open Questions` is the single
    collection point for every seat; seats return batches, the main
    agent appends and assigns `Q<k>` append-only (em owns the file);
    A6 sweeps other docs for strays; **folds land in the document the
    raising seat owns** (`[implementer]` answers amend the contract —
    else the pipe is one-way); and the mid-flight ambiguity route now
    covers **QA, the implementer at (3), and (5) findings that are
    really contract ambiguities** — the motivating trap was alive at
    two other stages.
  - **Rulings vs empirical claims**: the jurisdiction test ("can the
    implementer be ordered to make this sentence true?") separates
    requirements from claims about pre-existing reality; the shall/is
    split is what makes the rule satisfiable (future-system sentences
    are guarantees, enforced by (4)/(6) as ever). Evidence tags:
    `(measured, <date>, <scope>)` (scope mandatory — the date says when,
    the scope is the falsifier), `(unverified)`, and the distinct
    demotion `(assumed-empirical: <named risk>)`. Enforcement is a
    three-layer stack: kit attention key 1, the spec-answers promote
    grep, and a **Path B entry STOP** at the signing moment. The
    carrying argument was the **false-GREEN branch**: the (6)
    contract-defect class fires only on RED — a claim false only under
    conditions the acceptance run never produces goes green through
    (4), (5q) and (6), because *a faithful transcription of a falsehood
    satisfies fidelity*; nothing downstream of (2) can reach that
    branch, so the invariant is coverage, not economy. Holder-supplied
    empirical claims fold as `(from Q<j>, unverified)` — the holder is
    not an oracle about reality (Q9's false claim entered via a fold).
    Honest framing: a labeling regime whose teeth are the kit; an
    untagged claim is the status quo ante, backstopped by one fidelity-
    brief line.
  - **Port observability walk at (2)**: the implementer walks every
    scenario against its §5 port design, table in the contract; a
    **limitation is a verdict exemption the implementer never
    self-grants** — new kit sort key, the holder countersigns. QA
    re-walks independently at (4), every mismatch a mandatory finding
    both directions; (5q) audits the reconciliation trace; walk-currency
    check at promote; under-exposure named a contract defect in the
    port principle (over-exposure already was).
  - Also: the **Resolved-block trim** (spec.md = current truth: ruling +
    attribution + one-sentence rationale + fold pointers, never
    restating rule text; the argument lives in ledger + thread — full
    evacuation was rejected because the ledger is a CR comment that
    doesn't survive checkout/migration, and #61's seats read the repo);
    the scenario boundary rule (S13-class content is a rule wearing a
    scenario's costume); `C<k>` clause numbering for technical-spec
    (anchor-free contract prose can't be cited or audited); B6 wording
    aligned with patrol (blind re-dispatch resolves fidelity threads —
    the audited party never closes the audit's findings).
  - **Instrument #61, don't judge the ratio**: holder wall-clock per
    gate; artifact-change rate; **ledger reuse rate** (the safety check
    on the trim — re-asks rising means it cut too deep); dead spec
    weight (lines no test, thread, or comment ever consumed); question
    trajectory; fold cost.
  - **The `blocked` asymmetry, for whoever later tries to unify it**:
    1.11.0 ruled (7) has *no* `blocked` exit; 1.12.0's Path B entry
    check STOPs *into* `blocked`. Both are right for the same reason.
    At (7) the issue is already at the holder's gate — `blocked` adds
    no information and would strip the only label saying the work
    passed the verdict. At Path B entry the issue is machine-actionable
    (patrol re-invokes next-stage on the gate label unconditionally, and
    a stop that left the label in place would loop, posting a fresh STOP
    comment every pass) — `blocked` is the only exit that terminates,
    and patrol surfaces it in the user's queue with the STOP comment's
    "measure or demote, then re-apply the gate" instruction. The rule
    underneath: `blocked` exists to stop the *machine*, not to inform
    the human.
- **red-proof (DEFERRED 2026-08-17, not rejected — Paul's ruling)**: wait
  for real usage of the 1.8.0–1.10.0 surface first; accumulated fidelity
  findings from live cycles become the "what A catches statically"
  baseline the kill criterion needs, so the deferral improves the
  eventual experiment design. ADMC reopens it when Paul calls it.
  Design as settled: standalone
  `/roz-gate:red-proof <n>`, post-GREEN only, disposable worktree,
  authored at execution time (structural blindness + zero staleness),
  exhaustive rule enumeration (the denominator is the finding), sealed
  two-part plans, two mutations per rule with one reserved, survivor
  messages carry rule statement + coverage claim but never the mutated
  build's behavior; one strengthening round then surface; survivors don't
  block merge. Run on 3–5 issues; kill criterion: drop B only if
  B-catches-that-A-missed is empty AND survivors ⊆ A's static findings.
  Prior-art anchors: Google FSE'21 (no scores, ~7 probes/CL, suppression
  list 15%→89% productive), Meta ACH FSE'25, causality protocol (named
  test red, green on revert, mutated line executed).
- Constraint riding every new artifact: agent comments never land as the
  last comment in an unresolved thread (patrol/spec-answers would flip it
  to waiting-on-user) — top-level CR comments only.

## The measurement track (2026-08-21 →)

The quality-audit track above stops at 1.12.0. What followed was a change
of question: not "what rule is missing" but "how do we know any of them
hold". Everything below is recorded in the release notes (`CHANGELOG.md`)
and the eval ledger (`evals/README.md`).

- **Architecture self-review (2026-08-21)**: the plugin's prose was
  counted — 175 rules, 2 of them mechanically enforced, 46–72 live in any
  one invocation's context. The number that mattered was the second one.
- **Lint tier, 1.13.0**: ten static cases, each a defect that shipped or
  its identical shape; writing the specs found two more shipped defects
  (B1, C6 — both fixed where the rule was written, never where it was
  read). Release gate on every push.
- **Rule C, 1.14.0**: the quote-open guard — B4 promoted from prose to
  hook; 1.14.1 per-segment classification after a dogfooded false
  positive.
- **Replay tier (PR #1 → #7)**: the real commands in a sandbox against a
  stateful forge stub, 18 cases, pass^k. The instrument lied before it
  measured anything, and each lie became a fix with a red-proof: a vacuous
  pass on an empty run; every-iteration-invalid published as 0%; a
  spoofable reply count; quota exhaustion scored as FAIL; the stub blind
  to bodies passed by file; and D2's "mention is not use" three times over
  (a prohibition in the prompt, an exclusion pathspec, a shell string).
- **Rule D, 1.15.0**: E2 measured 0/5 *after* the prose was made explicit
  ("move it … delete it from the source document") — every run copied and
  never touched the source again. Predicate became a commit-time hook,
  same literal held in hook, checker and lint; re-run 5/5. The eval
  loop's first full cycle: measure → find → fix → verify.
- **Rule E, 1.16.0**: D2 measured 4/5 — one QA child read `src/app.txt`
  under the fidelity dispatch, invisible at the gate. Hook-enforced
  blindness scoped by a marker the dispatching command writes; 1.16.1 /
  1.16.2 narrowed two mention false positives found by the re-runs (one
  of them a real bypass caught by review). Re-run 4/4, zero attempts.
- **Judgment tier (PR #10)**: four ADMC issues frozen at the moment before
  the loop ran, opus judge, quote-verified, recall/precision never
  blended. k=2 on 1.16.2: F-51 correct silence 2/2; F-54 P8 1/2; F-63
  P1 2/2 but P2 (the trigger-surface question that changed the design)
  0/3 including calibration, N5 raised 3/3 — a consistent recall miss
  pointing at the seat brief, not at sample size; F-67 finding surfaced,
  question cap missed. Historical row for F-63: 2/2 · 0/2.
- **Enforced rules: 2 → 5** (A, B, C, D, E) plus the acceptance guard.
- **Open**: the pruning question (which of the 175 rules earn their
  context) — deferred by Paul; the rules-compile proposal (rules →
  compiled context, design debated, pilot was waiting on the baseline —
  now unblocked); the experiment notebook (a SQLite ledger keyed by
  experiment with an autopsy class per anomaly) — pending Paul's
  direction.

## State on 2026-09-21 (v1.16.2) — a snapshot

- **v1.16.2 shipped; 1.16.3 is this docs catch-up** (two clauses in
  `references/workflow.md` — behaviour prose, so the release gate
  required the bump). Five hook rules (A–E) plus the acceptance guard,
  99 hook tests; three eval tiers built (lint 70 checks on every push,
  replay 18 cases, judgment 4 fixtures / 7 items); opus baseline recorded.
- **GitHub App `roz-gatekeeper`**: installed on ADMC — agent comments
  post as `roz-gatekeeper[bot]` since 2026-08-12; the bot never holds a
  gate.
- **ADMC** (the first real project): bot-mode identity config in place
  (in the untracked `CLAUDE.local.md` since its PR #62); the judgment
  fixtures re-create the config block on each sandbox.

## Since then

- **2.0.0 shipped on 2026-10-17.** #140 gave it a vehicle (the stage order
  changed); the frozen protocol pages below ship with it (#142); the patrol
  gate-label audit is #144, on its own merits.
- This page is a record, not a status board. What is current lives where
  it is kept current: `CHANGELOG.md` for what shipped, `evals/README.md`
  for the case counts and the recorded baselines (both rendered).

## November 2026 (v2.7.3 → v2.19.0) — a snapshot on 2026-11-15

**Shipped**, 2026-11-05 → 11-14 (each release's note in `CHANGELOG.md`):

- **Hooks.** Every hook rule has a ledger row (2.7.3). Rule K: the loop
  merges only the base or its own branches (2.9.0), reading redirections
  and an unresolved `cd` for what they are (2.17.1). Rule E: a heredoc
  body is a mention, not a read (2.10.0, 2.10.1); a cwd inside `.git`
  resolves the main worktree (2.13.0). `guard-acceptance` judges the edited
  file's worktree, and every guard fails closed through `run-guard.sh`
  (2.18.0; #277, #281 PR 1).
- **The loop.** The seat pane draws every spawn (2.7.4). Up to N issues
  per pass (2.8.0). A gate label on a passed stage is illegal, and a missing
  dependency in the base is a STOP (2.9.0). A fold may ask once (2.11.0).
  Every unreached row is `queued:` (2.12.0). A questioned scenario still
  gets its test (2.13.0). Patrol reads forge-native blockers (2.14.0,
  2.14.1). One branch-name resolver, `bin/roz-branch` (2.15.0). QA-4 has
  one definition, and `bin/roz-state` runs in shadow (2.16.0). A deleted
  head keeps its CR, and `bin/roz-check integrate` runs in shadow (2.17.0).
  Dispatch lists name the R&R row (2.17.1). `next-stage` loads only the
  routed path, `references/next-stage-path-{a,b,b2,c}.md` (2.19.0).
- **Evals.** QA-brief variants and the D10–D19 frame (2.9.0); the
  `haiku55` SUT row for new baselines (2.12.0); the evaluation charter,
  Judgment V1 and the Workflow Value pilot's Phase A (2.17.0); the shared
  seed repaired, so every earlier replay result is stale (2.17.1, #293);
  SUT isolation, the runtime's own token totals and the runner CLI —
  `--list`, `--dry-run`, everything checked before spend (2.18.0); lint
  L20, the `path_files_read` signal and the L21 prose caps (2.19.0).

**On `main`, not yet released:** #320 (#319: a system event's string
`message` no longer crashes the runner); #322 (#321: SUT sessions get
`sut_base_env` and their own `TMPDIR`); #323 (#197: `spec.md` § Glossary,
QA's *term conflict* finding, D22–D24 on `fx/kv-cli-expiry`, `TOTAL_CAP`
52,040 → 52,231); #324 (#198: `bin/roz-persona`, an unusable seat stops
the run, L22, D25 and D26, the `init` cap 1351 → 1358).

**Still open:**

- **#281 PR 2** — `guard-blind` still hard-codes `src/`; PR 1 (fail
  closed) shipped in 2.18.0.
- **#325–#330** — what the 2026-11-15 haiku55 sweep found: stub fields and
  routes a real `gh` serves (#325); rule E denying a forge write whose body
  mentions `src/` (#326); the D6 checker counting the scanner (#327); the
  F11 fixture (#328); `path_files_read` missing a path file read with Bash
  (#329); checkers rejecting correct wording (#330).
- **#256** — review an unsupported guarantee before demoting it to an
  empirical assumption.
- **#296** — bind Judgment V1's gold approval to review evidence.
- **#299–#303** — the executable-prose module model: define it (#299),
  machine-readable dependencies (#300), the QA path classified with no
  behaviour change (#301), deterministic QA dispatch composition (#302),
  then every seat and operation (#303).
- **#199** — the QA-seat component regression corpus and prose ablation.
- **Baselines.** Every replay batch is `superseded` since 2.17.1, so the
  next full sweep is the first valid baseline; it and the new cases'
  baselines are the maintainer's quota call.

## Project memory — a learning-system proposal (2026-11-27)

**Requirements and architecture direction settled on 2026-11-28; not a
release commitment.** Eight rounds of discussion and final technology
choices established the design below; detailed implementation contracts
remain open. The motivating failure is not another missing rule:
the agent can finish a ticket, yet the next ticket starts without the
experience that the previous one paid to acquire. The first success
criteria are fewer repeated human questions and fewer repeated errors.

### Scope and authority

- One long-lived memory pool per repository, shared by roles, with
  per-entry applicability (scope and roles). Cover project knowledge
  (semantic), past events (episodic), learned methods (procedural),
  decisions with rationale, and human preferences. Memory is advisory
  context, never a new workflow rule or permission.
- Atomic entries, each traceable to original evidence; distinguish fact
  from inference. Record creation/update times without a TTL. Keep
  original experiences alongside derived lessons. Documentation summaries
  cite their source rather than becoming an independent authority.
- Prefer reusable knowledge, explicit human feedback, failures with
  established causes, and reviewer findings accepted and fixed by the
  developer. A decision or successful experience can qualify when
  reusable; the precise eligibility boundary is still open.

### Collection and publication

- Every role (including future roles) searches at stage entry and reflects
  at stage exit, initially via prompt instructions rather than a new
  guard. Roles and humans propose candidates to a separate, ticket-linked
  store; a zero-candidate outcome is valid but collection completion is
  recorded. Unfinished tickets do not publish formal memories.
- A ticket can close once valuable findings are durably collected; it
  need not wait for the scheduled acquisition. The closure check must
  account for every accepted reviewer finding: a stored candidate or an
  explicit reason for exclusion. Collection completeness beyond those
  findings remains an eval concern.
- On a fixed schedule, a dedicated memory agent works on a copy of the
  existing snapshot plus pending candidates from completed tickets.
  Integrate, deduplicate, resolve conflicts and reassess affected entries;
  allow additions, edits and removals. Validate deterministically and
  semantically, including evidence fidelity and checks for secrets and
  unnecessary personal information. Consolidation is a separate scheduled
  job deriving lessons while retaining original experiences.
- Before publication, validate the entire draft snapshot deterministically
  and with an LLM, and run the memory regression suite. Repair and retry
  within a bound; reject the whole draft on exhaustion. Proposed
  publication contract: readers see either the old or the new validated
  snapshot, never a partially updated one; failed publication preserves
  the old snapshot and pending input. Enforce one snapshot writer per project, across acquisition,
  consolidation and administrative mutations; the locking mechanism is TBD.
- Bootstrap once across all historical tickets in a single logical run;
  publish only after validation and regression gates. Internal batching,
  resource limits and restart/checkpoint mechanics remain implementation details.

### Recall and lifecycle

- Pin one snapshot at ticket start. At each stage, the role searches
  independently using ticket title/body, role, stage, affected
  components/files, keyword relevance and evidence trust. Agent judgment
  supplies semantic interpretation; no embedding model is required. Return an
  index or summaries first, then read selected entries as needed, with
  a cumulative cap of N full entries per stage. Prefer facts over
  inferences. Do not inject original evidence by default; retain its
  references for inspection. Record injected/read entries and the
  agent's claimed usage separately.
- Empty results are a normal outcome, explicitly reported; retrieval
  failure blocks execution. If memory conflicts with current rules or
  documentation, stop for human confirmation. Suspected incorrect memory
  yields a correction candidate for the next acquisition.
- States: active, superseded, invalidated. New validated knowledge
  replaces conflicting old knowledge as judged by the memory agent;
  facts take precedence over contradictory inferences, which are
  reassessed or withdrawn. Human confirmation, code/tests and independent
  supporting events inform evidence trust.
- Humans can inspect entries, evidence and derivations, invalidate/remove
  entries, inspect snapshot diffs and roll back. Removal affects the
  latest snapshot only (not a permanent erasure across history).
  Keep strictly the latest N snapshots. An emergency rollback pauses
  affected in-flight tickets; switching their pinned snapshot is allowed
  only if it is invalid, withdrawn or unavailable after retention cleanup.
  In that case switch to a valid snapshot and rerun affected stages;
  never silently mix versions. Project-level opt-out disables the memory
  subsystem.

### Evaluation and acceptance

Reuse the existing eval infrastructure, with a separate memory suite:
collection completeness (deterministic checks plus LLM judge),
acquisition fidelity (LLM comparison with original evidence), and
retrieval quality (human gold cases and historical ticket cases). Cover
irrelevant, stale, incorrect, contradictory and rule-conflicting
memories, prompt injection, and unavailable retrieval/snapshots. Reuse
the existing repeated-run/statistical approach. Ordinary replay uses
the latest published snapshot; the pre-publication regression gate evaluates both the active and draft
snapshots. Production memory is read-only during eval; collection and
acquisition tests may create temporary artifacts in a fully isolated
sandbox, never publish to production or enqueue production candidates.

Track repeated questions, repeated errors (deterministic classification
plus semantic root-cause judgment), and review iterations over real
usage. Require reproducible improvement in at least one core metric;
define denominators, baseline and observation windows before claiming
success. No controlled A/B experiment is required in v1, so observed
improvement alone does not establish causation. Claimed memory usage is
a trace, not proof that memory caused an outcome. Keep held-out evaluation
answers out of acquisition and bootstrap inputs.

### Architecture decisions (settled 2026-11-28)

- Local-first, single-machine v1. Store project data outside the repository
  in the roz-gate runtime data directory. Implement memory as an independent
  internal module with a boundary suitable for later extraction; cross-machine
  and multi-user synchronization are deferred.
- SQLite is the sole authoritative storage engine. Use one database with
  snapshot IDs rather than one database per version. Persist candidates,
  atomic memories, evidence/derivation links, snapshots, index and traces.
  Use transactional publication of the active snapshot; a logical working
  copy need not physically duplicate all rows. Exact schema, migrations,
  locking and export format remain implementation decisions.
- Keyword search plus metadata filtering, with no embedding model or
  vector database. The memory agent generates a hierarchical categorized
  navigation index per snapshot; keyword search remains independent of
  that hierarchy. Validate index references deterministically.
- CLI is the operation interface for agents and humans. Provide separate
  acquisition and consolidation commands sharing core implementation.
  A dedicated background memory service executes learning work; scheduling
  is external to the core and invokes the standalone CLI commands on fixed
  schedules. The scheduler product and service lifecycle are not prescribed.
- Single snapshot writer per project. Readers use their pinned snapshot;
  publishing must not expose partial changes. Candidate collection and
  usage tracing must remain safe while a draft is being prepared.

### Open design questions and known trade-offs

- Specify schema and migrations, runtime directory/project identity,
  CLI contract, background service lifecycle, external scheduler setup,
  lock/recovery mechanics, snapshot and retrieval limits, and bootstrap
  resource management. No external database service is needed.
- Strict N-version retention can remove a pinned snapshot before a ticket
  finishes; the chosen recovery is to switch and rerun affected stages.
  Define how affected stages are identified and interrupted safely. Removal
  from the latest version can be undone by rollback; cross-history secret
  purging is unresolved.
- Prompt-only collection/retrieval can be skipped by the agent. The closure
  check now requires accepted reviewer findings to be accounted for; exact
  enforcement and completeness for other evidence sources remain open.
- Conflict resolution by an LLM can be inconsistent; older evidence
  acquired later must not be confused with a newer project decision.
  The precise conflict policy is not yet settled. Authority conflicts
  deliberately stop the workflow but stale memory may increase human
  intervention.
- Define sandbox mechanics, active-versus-draft regression thresholds,
  failure/retry budgets and metric baselines before implementation.

Implementation direction: storage and data model first. Proposed
milestones (individual scope and acceptance contracts to be specified):

1. Architecture contracts, SQLite schema and storage/snapshot foundation.
2. Candidate collection and closure accounting.
3. Acquisition, validation and transactional publication.
4. Retrieval, hierarchical index and independent keyword search.
5. Role integration, snapshot pinning/recovery and project opt-out.
6. Consolidation, retention, inspection, diff, removal and rollback.
7. Memory eval suite and active/draft regression publication gate.
8. Background service, external scheduling and historical bootstrap.
9. Longitudinal effectiveness measurement.

Add tests with each increment; run historical bootstrap only after the
publication gate is ready. Memory remains a reference-client capability proposal,
not a change to the forge wire protocol unless separately agreed.


## The vision (why 2.0.0 exists)

Team members join over time, each free to bring **their own agent** —
roz-gate is an option, never a requirement. The interop substrate is
deliberately boring: **comments on issues/PRs + correctly used labels.**

The reframe that motivates a major version: **the protocol is the forge
conventions themselves; the plugin is a reference client.** The
human-legible-forge-state layer has no competitor (Google's A2A is a
JSON-RPC machine layer — complementary, not competing). And the honest
reason the version is a *major*: technically the identity work was
backward compatible — the real event is **publishing a spec**, which
widens the compatibility surface from "plugin config" to "wire
conventions". Once anyone implements against the page, markers and label
semantics become breaking changes.

## Design decisions (settled in assessment, shipped in 2.0.0)

1. **Protocol version decoupled from plugin semver.** The spec carries its
   own stamp (`protocol v1`); plugin 2.0.0 would *ship* protocol v1.
   Change policy: within v1, additive only; markers never change meaning.
2. **"Many participants, one driver."** Foreign agents as *participants*
   (comment, answer, review, `**[`-prefixed input) are safe **today** —
   every classification mechanism holds. The *driver* seat (moves
   transient labels, posts batches/summaries, finalizes, opens CRs) is
   **exactly one per repo**: the `processing` lock has no owner and no
   TTL, batches are asked-once, patrol acts on its N issues one after
   another (#204) — all single-writer assumptions. Goes in spec §5 as an explicit limitation.
3. **The spec's IN/OUT boundary.**
   - IN (wire; changing = breaking): label taxonomy + state machine +
     gate/transient ownership; the `**[` agent prefix; `**[intake]**` /
     `**[intake] · summary**` markers; the summary first/last-line rule;
     gate holder rules incl. bot-never-holds-a-gate and
     human-assignee-at-birth; the said-or-seen body invariant; honor
     locks; stop-don't-repair.
   - OUT (reference-client internals; free to change): the five role
     seat names (spec shows them as examples; prefix is "role-or-name"),
     branch naming (`spec/<n>`, `feat/<n>`, `qa/<n>`), batch formatting
     (SHOULD, not MUST), spec-doc structure, hook implementation, persona
     mechanics.
   - Principle: **the spec commits to what gets read and written, never
     to how anyone thinks.**
4. **Enforcement is three layers** (a self-built agent isn't bound by the
   hook — the honest answer):
   - *Prevention*: **capability containment** — each agent's token gets
     only its role's scopes (an intake-only agent with Issues:RW
     physically cannot push or merge). GitHub has **no per-label
     permissions**, so token scope is the only real forge-side control.
     Spec §4.
   - *Detection*: patrol audits gate-label events via the timeline API
     (`labeled` events carry the actor) — a bot applying a gate label is
     reported as a violation, **including foreign agents the hook can't
     reach.** (Shipped: #144, 2.1.0.)
   - *Honesty*: a per-client conformance disclaimer — the reference
     client self-enforces; for anything else, review its code and contain
     its token.
5. **Counterpart guide** (`docs/participating.md` draft): humans need
   three moves — answer the numbered questions, say `summary`, apply the
   label. Batch/summary footers link to it. Open item: the canonical URL
   (GitHub Pages vs repo blob) — **resolved in 2.0.0 (#142): GitHub Pages**; the intake footer
   links `https://taikerliang.github.io/roz-gate/participating.html`.
6. **GitLab multi-bot note**: project-bot usernames are opaque hashes —
   name the tokens meaningfully and keep the mapping in the config's
   `bot_login` list (comma-separated support already shipped in 1.7.0).

## The prove-or-reject verdict (2026-08-11)

Full report: https://claude.ai/code/artifact/255d2a60-adbe-4986-8412-3ea459c0f366
(four-party: three seats + red team, independently converged).

Claim verdicts: C1 gates enforceable & load-bearing — **PROVED** (27/27
against stubbed forges; the #54 real violation reproduced as a test; zero
real-world interceptions yet — that's what the guard log will measure).
C2 spec-stage defect finding — **PARTIAL** (findings real, attribution
not isolated, none fixed yet). C3 blind QA — **UNPROVEN** (never
executed). C4 team-async — **REJECTED in the v1.x configuration**
(0 of 22 questions answered; confounded: agent posted under the human's
own account, which suppresses every notification — exactly what 1.7.0
fixed, untested since). C5 async latency — **REJECTED** (all multi-day
delays were human-side; no igniter existed). C6 market differentiation —
**PROVED (narrow)**. C7 protocol play — **CONDITIONAL**: the niche is
uncontested but "a protocol is ratified by adopters, and adopters are
zero."

**Overall: CONDITIONAL.** Mechanisms proved (enforceable, testable, fast
to evolve); the core value proposition (team-async) unproven. Success
redefined: **"make the second human possible."** Protocol marketing waits
for the first closed loop. Three conditions to convert:

1. Close one full loop (through an integration verdict).
2. A second human uses it for real.
3. Run the persona ablation (multi-role debate vs one strong agent).

Market facts recorded: GitLab Duo Flows ships the opposite philosophy
natively (incl. self-managed/air-gapped); GitHub itself calls PR approvals
"not a security control"; surviving competitors converge on risk-tiered
gating (roz-gate over-gates by comparison); no competitor combines the
four-capability matrix. Positioning line: **"Duo gives you automation;
roz-gate gives you accountability."** Kill criteria and the top-3 metric
details live in the report.

Instrumentation shortlist (from the implementation-side input): human
touches per issue (fast vs spec), spec-caught reversals vs post-ship
rework, blind QA's independent catch rate, gate-wait vs agent-work time,
hook interception count, assumption-overturn rate.

## Backlog ledger

**Protocol v2 agenda** (not before adoption exists): multi-driver
coordination, lock ownership + TTL, driver handoff.

**2.0.x (small, agreed):**
- Guard log: append one line per hook denial to
  `.git/roz-gate-guard.log`; also warn there when `load_bot_logins()`
  fails to read config (currently a silent fail-open in bot mode).
- Cron-patrol igniter recipe in docs (event-driven via Actions +
  claude-code-action = a 2.1 exploration, not the light path).
- Patrol report: age of unanswered intake batches.
- Patrol step 0: warn on configured paths that don't exist.

**Research / later:** GraphQL `__typename` as a structural bot flag (the
hook's `--json comments` path has none — normalized-login comparison is
current law); measure GitLab minimal access level (40 verified, 30
unmeasured); re-tier fast/spec by blast radius once loop data exists; the
stringly-typed role attribution debt; hook-verify the credential
coexistence discipline (bot token never exported).

**Shipped already (don't redo):** identity separation (1.7.0), batch cap
5 + gate-label-direct header (1.7.0), init mkdir (1.7.0), README/guide
identity + hook sections (1.7.1), App logo (post-1.7.1).

## Onboarding & adoption context

Three user types: **operator** (runs the loop), **counterpart** (human
who only answers/labels — the most undervalued; the participating guide
exists for them), **agent-builder** (teammate with their own agent — the
spec page is for them). Patrol's report carries teaching duty: it tells
each human what's waited on, with links. A demo issue in a fresh repo is
the cheapest onboarding artifact.

PMF experiment for the protocol play: publish the spec page and see
whether an agent-building teammate can integrate **without asking a
single question**. Three-lane positioning to revisit: GitLab self-hosted
accountability gap; methodology/protocol brand (conventional-commits
precedent); compliance-audit angle.

## Frozen artifacts

Draft `docs/protocol.md` (wire spec) and `docs/participating.md`
(counterpart guide) were written and design-reviewed, then pulled from
the v1.7.0 tree per Paul's split. They are **not in git history**.
Copies live in the maintainer session's scratchpad (`frozen-2.0.0/`) and
durably in the project memory directory
(`~/.claude/projects/-Users-taiker-dev-roz-gate/memory/frozen-2.0.0-drafts/`).
Retrieval condition: Paul green-lights 2.0.0. If lost, regenerate from
the "Design decisions" section above — it is the complete outline.

**Resolved 2026-10-17 (#142):** both pages were regenerated against the
2.0.0 workflow and ship in `docs/` — `docs/protocol.md` (protocol v1) and
`docs/participating.md` (four moves: the (7) review conversation joined the
three). The drafts in memory are superseded. The timeline audit (item 4,
*Detection*) shipped as #144.
