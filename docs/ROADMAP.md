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

## Current state (as of 2026-08-11)

- **v1.7.1 shipped.** Agent identity separation is live: `agent_identity:
  bot` with a GitHub App or GitLab project access token, bot never holds a
  gate, hook enforcement at 27 test cases, intake batches capped at 5 with
  the gate-label-direct hint, init creates `acceptance_dir`/`specs_dir`,
  README/guide surface identity + hook.
- **GitHub App `roz-gatekeeper`**: registered, public, logo shipped
  (`images/roz-gate-logo.png`) — awaiting installation by emilyorz.
  Ops learning: cross-account installation on personal repos needs the
  repo owner to install; if multi-repo friction grows, the fallback lane
  is a machine account + PAT (config change = `bot_login` only).
- **ADMC** (the first real project): identity config keys not yet filled.
- **2.0.0: deferred.** The frozen items below are design-approved but
  unshipped.

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

## Design decisions (settled in assessment, awaiting release)

1. **Protocol version decoupled from plugin semver.** The spec carries its
   own stamp (`protocol v1`); plugin 2.0.0 would *ship* protocol v1.
   Change policy: within v1, additive only; markers never change meaning.
2. **"Many participants, one driver."** Foreign agents as *participants*
   (comment, answer, review, `**[`-prefixed input) are safe **today** —
   every classification mechanism holds. The *driver* seat (moves
   transient labels, posts batches/summaries, finalizes, opens CRs) is
   **exactly one per repo**: the `processing` lock has no owner and no
   TTL, batches are asked-once, patrol acts one-issue-per-pass — all
   single-writer assumptions. Goes in spec §5 as an explicit limitation.
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
     reach.**
   - *Honesty*: a per-client conformance disclaimer — the reference
     client self-enforces; for anything else, review its code and contain
     its token.
5. **Counterpart guide** (`docs/participating.md` draft): humans need
   three moves — answer the numbered questions, say `summary`, apply the
   label. Batch/summary footers link to it. Open item: the canonical URL
   (GitHub Pages vs repo blob) — **Paul has not ruled.**
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
