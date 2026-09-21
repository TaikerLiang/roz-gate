# Roz Gate — an AI-agent development workflow, as a Claude Code plugin

![Roz Gate — no stamp, no merge](images/roz-gate-banner.png)

**[▶ Interactive guide](https://taikerliang.github.io/roz-gate/)** — the loop,
the labels, an issue's life, and "what should I do now?", in one clickable
page (EN/中).

Roz Gate turns a repository into a **role-driven, human-gated development
pipeline** run by a team of specialized AI agents: a product advocate, an
engineering manager, an implementer, a black-box QA tester, and an independent
reviewer. Agents do the work; **you make every decision that matters** — the
pipeline stops at explicit gates and cannot cross them without you.

Works with **GitHub (`gh`) and GitLab (`glab`)**, gitlab.com or self-hosted.

```
(1) intake → (2) spec → (2a) Q&A → (3)(4) impl ∥ QA → (5) review → (6) verdict → (7) merge
      ▲gate            ▲gate                                                    ▲gate
```

## Why

A single AI assistant asked to "build and test the feature" grades its own
homework: its misunderstandings flow into the code *and* the tests, so green
proves nothing. Roz Gate splits the work across agents with strict
information walls — the QA agent **never sees the implementation**; it writes
black-box tests from the spec and a technical contract only, and the two sides
meet for the first time at an **integration verdict**. Disagreements surface as
real test failures before merge, not in production. Every open question an
agent hits stops the line and comes to you as a written, answerable thread —
agents are forbidden to guess.

## Requirements

- Claude Code with this plugin installed
- `gh` (GitHub) **or** `glab` (GitLab) authenticated for the repo's host
- A git repo on that forge, with issues and PRs/MRs enabled
- A test runner invocable from the CLI
- Python ≥ 3.12 and `uv` **only to run the eval suite** (`evals/`) — not to
  use the plugin

**Developing the plugin itself?** A fresh clone's gates are inert until git
is pointed at them — run once:

```sh
scripts/dev-setup.sh        # = git config core.hooksPath .githooks
```

That wires `.githooks/pre-commit` (naming convention) and
`.githooks/pre-push` (hook tests + lint tier + version-bump check). CI runs
the lint tier as the backstop for a clone that never did this.

## Install

```
# GitHub-hosted:
/plugin marketplace add <owner>/roz-gate
# or any git host (GitLab, self-hosted):
/plugin marketplace add https://<host>/<path>/roz-gate.git

/plugin install roz-gate@roz-gate-marketplace
```

Then, inside each project you want to run the loop in:

```
/roz-gate:init
```

`init` is one-time and idempotent. It detects the forge from your git remote,
creates the labels, writes a workflow pointer + a small config block into
your project's `CLAUDE.md` (the workflow doc itself stays in the plugin, so
upgrades apply everywhere at once), **seats the agent team** — if you already
have agents you like, it links them into the fixed role seats instead of
replacing them; the rest default to the plugin's — and adds an "Idea" issue
template for mobile capture.

## The loop in one page

| Stage | Who | Deliverable |
|---|---|---|
| (1) Intake | main agent + you | one issue = one user story, with observable acceptance criteria and a `track:` label |
| (2) Spec | em + product + implementer | `spec.md` (scenarios) + `technical-spec.md` (the contract), opened as the **spec CR** |
| (2a) Q&A | you + role agents | every open question a thread on the spec CR; your answers folded back into the spec |
| (3) Implementation | implementer | `feat/{n}`: code + unit tests |
| (4) Black-box QA | qa | `qa/{n}`: test plan + acceptance suite — written blind, from spec + contract only |
| (5) Review | reviewer | severity-graded inline threads (`blocking`/`should-fix`/`nit`/`question`) until review-clean |
| (6) Integration | main agent | both branches merged locally, QA's suite runs against the code for the first time — **the verdict** |
| (7) Review | **you** + main agent | you review the spec CR (spec + code + tests + green verdict); the main agent answers your comments there and changes only what you confirm; you merge, or send it back |

**The mental model: owner, contractor, inspector.** The loop is the
time-honoured commercial structure for buying work you cannot fully watch:

| Stage | Commercial counterpart |
|---|---|
| (1) Intake | the **MOU** — intent, scope, roughly how big; no binding terms |
| (2) Spec + (2a) Q&A | **contract** drafting + negotiation rounds — each open thread a clause you settle |
| (3) Implementation | performance — the contractor builds |
| (4) Black-box QA | the third-party inspector writes the acceptance procedure **in advance, from the contract alone** — never visiting the site |
| (5) Review | site supervision — checks workmanship, not outcomes |
| (6) Integration | **acceptance** — the procedure meets the finished work for the first time; the verdict |
| (7) Review | the walk-through: the owner inspects, asks, gets answers, has snags fixed — then signs off, or sends it back |

Two structural carry-overs give the verdict its credibility. The acceptance
procedure is written in parallel with the build, blind — a standard agreed
after construction, together with the builder, is theatre (the qa branch
carrying no implementation code enforces this). And a contract ambiguity
mid-build is never interpreted by the contractor: it goes back through a
**change order** — (2a), the loop's only backward transition. You are the
owner throughout: you sign (gate labels, the merge) and never build. Small
deals (`track: fast`) skip the contract and close on the MOU alone.

> **Note — the test port.** QA drives the system only through the contract.
> For an HTTP feature the contract is the API doc, so black-box testing is
> natural. A feature with **no natural external interface** — a scheduled job,
> a bot command, an internal service — still owes QA a front door: the
> implementer must ship a **test port** as part of `technical-spec.md`, a
> small, documented, stable driver the acceptance tests call instead of
> reaching into internals. Example: offer expiry runs on a schedule, so the
> port exposes `advance_clock(minutes)`, `run_expiry_sweep()`, and
> `get_offer_state(id)` — control and observation points, nothing internal.
> Because the port is promised in the contract at stage (2), QA can write its
> suite in parallel with the build; because it exposes only observable
> behaviour, the tests survive refactors and the black box stays sealed. In
> hexagonal-architecture terms: a driving port whose actor is the acceptance
> suite — the inspector's access hatch, reserved in the contract, never a
> hole cut in the fence. A port that "conveniently" exposes internals defeats
> the point; treat that as a contract defect.

**Two tracks.** Design-bearing stories take the full loop (`track: spec`).
Mechanical changes (chores, config, doc fixes) take the **fast track**
(`track: fast`): direct implementation + review + your merge, with an
**escalation valve** — the moment a fast change grows a real decision, it is
relabelled back onto the spec track.

**Three gates, all yours.** `status: ready-for-spec` (design this),
`status: ready-for-dev` (build this), and the final merge. Commands and agents
never apply gate labels — structurally, the machine can run the pipeline but
cannot authorize it.

## Commands

| Command | What it does |
|---|---|
| `/roz-gate:init` | one-time repo bootstrap (labels, config, personas, templates) |
| `/roz-gate:to-issues` | live intake: the `product` agent (under the intake brief) clarifies your idea one question at a time; the main agent only relays and publishes the confirmed story — one issue = one story |
| `/roz-gate:next-stage [n]` | advance one gated issue — spec stage, parallel impl+QA+review, or fast track — routed by its labels; prints the workflow map first |
| `/roz-gate:spec-answers [n]` | fold your answers on spec-CR threads back into the spec, resolve the threads |
| `/roz-gate:integrate [n]` | run the stage-(6) verdict: merge locally, run the acceptance suite, classify red, finalize green |
| `/roz-gate:review-answers [n]` | host one turn of your stage-(7) review: answer your CR comments from the artifacts, dispatch a seat when judgment is needed, change only what you confirm |
| `/roz-gate:patrol` | one supervisory pass: scan every open issue's state, invoke whichever command is already authorized, triage the inbox, report what waits on you |
| `/roz-gate:uninit` | retire the loop from this repo: verify nothing is in flight, remove the scaffolding `init` installed, keep every work product — run before `/plugin uninstall` |

Run `/roz-gate:patrol` manually as a "what's next" button, or schedule it
(e.g. every 30 minutes) for an unattended loop — it acts on one in-loop issue
per pass but triages the whole inbox every pass, treats the `processing` label
as a lock, and never applies a gate label.

## The inbox: filing ideas from your phone

Open an issue from the forge's mobile app with **no labels** — two rough
sentences are enough (the "Idea" template `init` installs reminds you). An
issue with no `track:` label is the **inbox**: invisible to the rest of the
loop. Three beats — **ask once, summarize on demand, the label confirms**:

1. Patrol posts **one** batch of clarifying questions (numbered, each option
   with a marked recommendation), then leaves the thread to the humans —
   free-form discussion, anyone may weigh in, from any device.
2. The **issue assignee** (unassigned → the author) ends a comment with the
   line **`summary`** whenever the discussion feels settled — or
   immediately, if the recommendations look right; corrections and the
   request can share one comment. The agent condenses the body + all
   comments into one summary: story + acceptance criteria + suggested track
   + an attributed decision trail; unanswered questions become explicit
   assumptions, disagreements become contested points shown with both sides.
3. Looks right? The assignee applies the gate label — `ready-for-spec` (spec
   track) or `ready-for-dev` (fast track). **The label is the confirmation**,
   and it reads: *build the story from everything I said* — only the
   assignee's words drive the issue body; bystander comments never fold in
   without their endorsement. Patrol then rewrites the body and applies the
   track that label choice confirms, and the loop takes over. Off? Reply
   corrections — end with `summary` to re-read first, or label directly:
   finalize folds your corrections either way.

Both intake paths run the same brain: the `product` agent dispatched under
`references/intake-brief.md`. The orchestrator never does clarification
thinking in its own context — it relays, posts, and publishes.

## Labels & state machine

| Label | Kind | Applied by |
|---|---|---|
| `track: spec` / `track: fast` | track | intake, after your confirmation |
| `status: ready-for-spec` / `status: ready-for-dev` | **gate** | **you, only ever you** |
| `status: in-spec-review` | transient | spec stage (also the mid-flight re-entry state for QA ambiguities) |
| `status: in-user-review` | transient | main agent — work that passed the verdict, waiting on your review; the (7) conversation lives here |
| `status: processing` | lock | any running command; coexists with the phase label (a stale pair = crash forensics) |
| `status: blocked` | transient | a stopped command — evidence + recommendation posted as an issue comment; you decide |

No `track:` label = inbox (pre-loop). No `status:` label = in flight (the open
CRs are the state). Commands validate invariants and **stop on violations —
they never repair labels**.

The rules that protect you from the agents are not just prose: bundled
**PreToolUse hooks** enforce them at the tool layer, before the tool runs,
fail-closed, with a message pointing back at the protocol. *Prompt
discipline is the manners; the hook is the law.*

| rule | blocks | why | since |
|---|---|---|---|
| **A** | an `**[intake] · summary**` posted without the gate holder's `summary` request (or a gate label) | the summary is a human decision point; answered questions alone never trigger it | 1.5.0 |
| **B** | an agent applying `status: ready-for-spec` / `ready-for-dev` | a gate label is an authorization — only the human moves it | 1.5.0 |
| **C** | a marker-carrying comment that opens with a quote block | patrol classifies by the opening token; a quote-opening agent comment reads as a human answer and the loop replies to itself | 1.14.0 |
| **D** | a `git commit` while `technical-spec.md` still carries an open-questions section | a question outside the threaded surface resolves by silent interpretation; the prose measured 0/5 after it was made explicit | 1.15.0 |
| **E** | inside a fidelity dispatch, any read of `src/` or git action on a `feat/<n>` ref | the blindness the integration verdict rests on — a green looks identical either way | 1.16.0 |
| **acceptance** | editing the acceptance suite on a `spec/<n>` branch | a weakened assertion re-runs green and turns the verdict into an echo of the implementation | 1.11.0 |

Details, the fidelity-dispatch marker, and how to add a rule: `hooks/README.md`.

Every state-mutating command has exactly two exits: **Done** (deliverable
produced, lock removed) or **STOP** (discard local work, set `blocked` alone,
post evidence + a recommended next step). No third exit — so any terminal state
is readable from the labels alone. The single exception is stage (7), which has
no `blocked` exit: the issue is already at your gate, so a failure there is a
comment saying so.

## Forge support

Commands are written against ~12 named forge operations (LABEL-ADD,
CR-OPEN-DRAFT, THREADS-LIST, THREAD-RESOLVE, …). Two adapters map them to
concrete CLI:

- `references/forge-github.md` — `gh` (+ GraphQL for review threads)
- `references/forge-gitlab.md` — `glab` (REST discussions API)

Notable GitLab differences, handled by the adapter: MRs instead of PRs; inline
threads need the MR's diff SHAs; and labels use **scoped labels**
(`track::spec`, `status::ready-for-dev`) so the platform itself enforces
"exactly one track, at most one status" — while the `processing` lock stays a
plain label on purpose, because it must *coexist* with the phase label it
locks. Issue templates live at `.github/ISSUE_TEMPLATE/idea.md` vs
`.gitlab/issue_templates/idea.md`.

Adding another forge = writing one more adapter file with the same operation
names; no command changes.

## Agent identity

By default the agent acts as **you** — your `gh`/`glab` session (`user`
mode, zero setup). Opt into **bot mode** and it gets its own face on the
forge: a **GitHub App** (`your-bot[bot]`) or a **GitLab project access
token** bot. Three things change:

- **You can tell who's speaking** — agent comments carry the bot author;
  authority checks compare authors, not text markers.
- **Your phone finally rings** — an agent posting under your own account
  suppresses every notification; a bot's questions and summaries actually
  ping the assignee. Async intake starts working from anywhere.
- **Your credentials stay yours** — the agent holds a short-lived
  installation token or a revocable project token, never your session.

One invariant holds in both modes: **a bot never holds a gate.** Bot-created
issues are born with a human assignee, and gate labels stay human-only —
hook-enforced.

Setup is a one-time human task (the plugin never creates credentials):
follow [`references/identity-github-app.md`](references/identity-github-app.md),
then add three keys to the config block:

```
- agent_identity: bot
- bot_login: your-bot            # app slug / project-bot username
- operator: your-forge-login     # default assignee for bot-created issues
```

Keys absent = user mode, unchanged.

## Per-project configuration

`init` writes a `### Roz Gate config` block into your `CLAUDE.md`; every
command reads it before acting:

```
- forge: github | gitlab
- default_branch: main
- test: <full-suite command>            e.g. uv run pytest / npm test
- acceptance_dir: tests/acceptance
- acceptance_test: <one feature's acceptance command>
- env_sync: <dependency sync command>   e.g. uv sync / npm ci
- lockfile: <lockfile name>             the only mechanical merge carve-out
- lockfile_regen: <regen command>
- specs_dir: docs/specs
- acceptance_layout: <convention> # optional — suite layout; absent = one folder per feature
- trace_marker: <marker syntax>   # optional — scenario-trace marker on tests; absent = qa declares one
- agent_identity: bot            # optional — see "Agent identity"; absent = user
- bot_login: <bot username>      # optional
- operator: <your forge login>   # optional
```

`init` also writes a `### Roz Gate personas` block — **fixed seats, swappable
occupants**. The five role names (product, em, implementer, qa, reviewer) are
the workflow's vocabulary and never change; each seat maps to the subagent
actually dispatched. Already have a `backend.md` you've tuned for months?
Link it — your file stays yours, unmoved and unrenamed:

```
- product: roz-gate:product        ← plugin default
- em: roz-gate:em
- implementer: backend             ← your existing agent, seated
- qa: roz-gate:qa
- reviewer: roz-gate:reviewer
```

**Persona is swappable; the contract never is.** Every dispatch attaches the
seat's Owns/Never contract (qa never reads the implementation, the reviewer
never writes code, …) — and at link time `init` reads your agent against its
seat's contract and flags text that fights it, so a linked persona can't
quietly break the loop's information walls. An unlinked implementer seat gets
the classic treatment: the plugin's charter template instantiated into
`.claude/agents/implementer.md`, its `## Stack` section filled with *your*
stack's anti-patterns.

## Adopting on a less mature project

Don't turn everything on at once. The staged path, each stage stable on its
own: **(1)** independent review only — route every AI diff through the
reviewer; **(2)** add the spec stage + Q&A threads for one real feature;
**(3)** add blind QA + the integration verdict; **(4)** add patrol when enough
work is in flight that manual advancement is the bottleneck. A project with no
tests should start at (1) and build test culture before (3) can mean anything.

## Leaving Roz Gate

Retirement is two steps, **in this order**:

1. In **each** adopted project: `/roz-gate:uninit`. It refuses to run
   mid-flight (open issues with `track:`/`status:` labels, open loop CRs),
   then removes what `init` installed — the CLAUDE.md section, the
   `implementer` persona (asked first), the idea issue template. Forge labels
   are **kept** by default: deleting them would erase them from closed issues'
   history; ask explicitly if you want them gone. Specs and the acceptance
   suite are work products, never touched — from that point they're ordinary
   project assets.
2. Only when every project is clean: `/plugin uninstall roz-gate`. Order
   matters — uninstalling first deletes `/roz-gate:uninit` along with the
   plugin, leaving the cleanup to you by hand.

## Repository layout

| directory | role | who reads it | when it takes effect |
|---|---|---|---|
| `commands/` | the entry points (`/roz-gate:*`) | Claude Code, then the agent | invocation |
| `references/` | protocol docs, seat briefs, forge adapters | the agent, on every invocation | runtime |
| `agents/` | the built-in personas (product, em, qa, reviewer) — referenced, never copied | the agent, at dispatch | dispatch |
| `templates/` | consumer scaffolding, instantiated by `init` and removed by `uninit` | the consumer repo | install time |
| `hooks/` | deterministic enforcement and its tests ([hooks/README.md](hooks/README.md)) | the machine, before a tool runs | tool time |
| `evals/` | the eval ledger — lint, replay, judgment ([evals/README.md](evals/README.md)) | developers of the plugin | dev time; lint on pre-push and CI |
| `.githooks/` | this repo's own release gate | git, on push | push |
| `docs/` | human-facing pages (roadmap, site) | humans | never loaded by the agent |
| `scripts/` | operator utilities | operators | on demand |
| `.claude-plugin/` | the manifest (name, version) | Claude Code | install |

Two axes organize this. **Who reads it**: the agent at runtime
(`commands/`, `references/`, `agents/`), the machine (`hooks/`,
`.githooks/`), humans (`docs/`, `evals/`), or the consumer repo
(`templates/`, instantiated). **When it takes effect**: install
(`templates/`, the manifest), runtime (everything the agent loads), or dev
time (`evals/`, the gate).

One deliberate asymmetry: four personas live in `agents/` and are
*referenced* by the consumer's config, but the implementer lives in
`templates/` and is *copied* — it is the only seat that must absorb the
consumer's own coding guidelines, so it has to be a file the consumer owns.

File names: Python is `snake_case` (importable), shell is `kebab-case`,
markdown is lowercase-kebab except the ecosystem caps (`README`,
`CHANGELOG`, `ROADMAP`, `CLAUDE.md`) and the eval fixtures, which are data
keyed by ledger case id. Enforced by `.githooks/pre-commit` and re-checked
by the lint tier on push and in CI (one predicate: `evals/lint/naming.py`).

And the line between `references/` and `docs/`: everything in
`references/` is agent input on every invocation, so every line there is a
token cost on every turn (the 46–72 live-rules figure in the roadmap);
`docs/` is for humans and is never loaded. Do not put human reading
material in `references/`.

## How we know it works

Three evidence tiers under `evals/` (the ledger: `evals/README.md`):

- **lint** — static checks on the plugin's own prose and hook code, on every
  push: each case is a defect that actually shipped, or its identical shape,
  proven against positive and negative fixtures.
- **replay** — the real commands run headless in a sandbox repo against a
  stateful forge stub, graded by code from the forge journal, the transcript
  and the pushed refs; pass^k with Wilson intervals — rates, never booleans;
  an invalid run is never a red.
- **judgment** — LLM-as-judge on real historical issues frozen at the moment
  before the loop ran: "did it surface the thing that changed the human's
  mind", quote-verified, recall and precision reported separately.

The release gate runs lint and the hook unit tests on every push. The opus
baseline as of 2026-09-21: replay 17/18 cases at 100% (k=5), F6 no
in-session decay across three 12-turn sessions; judgment at k=2, F-63 recall
1/2 · precision 1/2 against the historical run's 2/2 · 0/2. Every case
derives from one repository and one operator — green proves no regression on
work shaped like that, nothing about shapes never run.

## Design principles (the short version)

1. One accountable orchestrator; specialists never share a session.
2. Roles are defined by what they must **not** do — that's what buys
   independent derivations.
3. Contracts, not conversations: exchanges between agents are written and on
   the record, or don't happen at all (QA).
4. Implementation and QA run in parallel, blind; the verdict at integration is
   the only honest "does it match the spec".
5. Ambiguity stops the line — agents surface questions, never guess.
6. Humans hold the gates; the machine cannot authorize itself.
7. State lives in labels and CRs, never in a session — crash-safe, auditable,
   schedulable.
8. A rule either has teeth or is measured; prose alone is a hope.

## Troubleshooting

- **Stale `processing` + a phase label** — a run was killed mid-flight. Look at
  what the dead run left (the phase label says where), clear the lock, re-run;
  commands are idempotent on re-entry.
- **`status: blocked`** — read the issue comment: evidence + recommendation.
  Decide, clear the label; the step re-runs from clean state.
- **Illegal label state reported** — a command found an invariant violation and
  stopped on purpose. Fix the labels by hand (you have the evidence); commands
  never repair labels themselves.
- **QA CR never leaves draft** — QA is paused on an open question; check the
  spec CR for an unresolved thread, or the issue for `in-spec-review`.

## License / provenance

Extracted from a working single-repo implementation of the methodology
described in *AI-Native Software Development: The Roz Gate* — role charters,
label state machine, STOP protocol, and the integration-verdict design are
ports of that system, generalized and made forge-neutral.
