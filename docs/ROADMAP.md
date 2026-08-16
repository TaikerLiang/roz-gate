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
- **1.9.0 (awaiting ruling) — QA fidelity review**: `test-spec.md` gets a
  required scenario→test map; an implementation-blind reviewer dispatch
  (against a `qa/<n>` checkout — blindness is structural via branch
  topology) audits assertion fidelity with verbatim two-way citations, a
  12-item vacuous-assertion checklist, an over-assertion check (false
  REDs), and a contract-currency step zero (unfolded amendments block);
  findings as QA-CR threads + integrate precondition; duties land in the
  R&R table, not command prose. Prior-art notes: every expected literal in
  an assertion needs a spec-text origin (no origin ⇒ read off the
  implementation); the scenario→test map must be **derivable from
  machine-readable markers in the test source** (marker syntax is project
  config, like `acceptance_test`) — hand-maintained trace matrices are
  complete, tidy, and stale.
- **1.10.0 (awaiting ruling) — gate-holder legibility**: decision ledger
  (quote the holder's answer *and the fold*); since-you-approved spec
  diff at (7) (stamp the SHA at gate time); evidence cards at (7) only,
  actual observed values or "not observed" (target rendering:
  Concordion-style inline substitution); issue-delta instead of summary;
  flagging as computed sort, never filter. Binding rules:
  quote-never-paraphrase, no conclusions, exhaustive-or-say-so, kit
  states its own blind spot. Success metric: artifact-change rate at
  gates, not approval rate.
- **red-proof (experiment track, no version)**: standalone
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
