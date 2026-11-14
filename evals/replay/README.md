# The replay tier

Run a roz-gate command against a frozen forge fixture and measure whether
the loop's rules hold. **This tier produces a measurement, not a gate**:
per-case observed rates with Wilson 90% intervals, no pass thresholds
anywhere. The number nobody has — *how often does the agent break its own
rules?* — comes first; what to gate on is decided from the baseline, not
in advance of it.

It is also a **model-portability benchmark**: the question is "is the
roz-gate protocol operable by other models, and at what compliance rate".
Claude Code is the runtime for every row; `--sut` swaps the model,
whole-stack — seats ride the same endpoint as the main agent, because
"the loop operated end-to-end by X" is the honest number.

## Running

```sh
uv run evals/replay/run_replay.py [--sut NAME] [--k N] [--variant A|B|C] [case ...]   # from the repo root
uv run evals/replay/run_replay.py --list [case ...]      # default k, baseline status, tier — no model
uv run evals/replay/run_replay.py --dry-run --sut haiku55 D10   # k, done, pending, smoke sessions — no model
# (plain `python3 run_replay.py` works identically — the tier is stdlib-only;
#  uv standardizes the interpreter, python >= 3.12. The uv project root is
#  the root pyproject.toml — one environment for evals/, hooks/, tools/.)
```

- **Checked before spend** (#282): the SUT, the variant, every named case,
  each checker's `# source:` citation and the driver/variant pairing are
  checked for the whole batch before the report dir is created or the
  smoke gate starts — a typo or `--help` costs nothing. `--list` and
  `--dry-run` start no model, need no API key and write nothing.
- SUT rows live in `models.yaml`. `opus` is the fixed reference baseline
  the rows published before 2026-11-08 were measured on; new baselines run
  on `haiku55` (quota); `fable` is the current operator. Rows of different
  SUTs are never compared with each other. API rows (translation proxy) are a
  marked TODO — the resolution architecture accommodates them unchanged.
- **Baseline note, verbatim in every report**: the baseline measures the
  protocol's ceiling reference, not necessarily the production loop's
  current operator; the current operator appears as its own row.
- **Resumable**: every iteration persists to
  `report/<sut>/<case>/run-<i>/`; completed iterations are never re-run.
  A sweep interrupted at case 12 continues from case 12.
- **Never CI, never pre-push**: replay costs minutes and millions of
  tokens per sweep. CI runs the lint tier only. Replay is local,
  on-demand, pre-release manual.
- Cost: API-mode rows record dollars from response usage; subscription
  rows record tokens labeled quota, no dollar figure. Measured single-run
  costs (fable, on the old counter — see below): a quiet patrol pass
  ≈ 209k in / 2.7k out; a review-turn pass ≈ 114k in.
- **Tokens are the runtime's own totals** (#308,
  `replaylib.session_tokens`). The last `result` event's `modelUsage` is
  the process's running total, seats included; without it the `result`
  events' `usage` is summed (one per turn, the main thread only); with no
  `result` event, each message is counted once at its last usage. A
  resumed session (F6's turns, one process each) sums its transcripts.
  `tokens` holds `in` (input + cache creation), `out`, `cache_read` and
  `counter` (`replaylib.TOKEN_COUNTER`, now 2). A result without `counter`
  was counted by version 1, which summed every stream event — an API call
  streams one event per content block, each repeating the call's usage
  with a partial output count, so input was double-counted and output
  about 40× low (F-51: 56,774 in / 100 out recorded, 30,177 / 4,231
  true). `report.json` sums only runs on the current counter; the others
  are counted in `tokens_old_counter` and their figures left out. An old
  run cannot be re-counted from its result; its transcript can.

## Exporting runs to Langfuse

A run dir already holds the whole model interaction; Langfuse is the viewer
(issue #80). The instance is local and ships in the repo:

```sh
cd evals/langfuse
cp .env.example .env     # dev-only secrets; first boot creates org/project "roz-gate" and its keys
docker compose up -d     # web UI on 127.0.0.1:3000 only (login in .env); nothing else published
set -a; . ./.env; set +a # LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY for the exporter
```

With the three variables set, `run_replay.py` exports every iteration
right after its `result.json`; a failed export is one stderr line and
never changes a verdict. Unset → nothing happens. Existing run dirs:

```sh
python3 evals/replay/export_langfuse.py report/opus/C12/run-*            # backfill a sweep
python3 evals/replay/export_langfuse.py --dry-run report/opus/A1/run-1   # the payload, no network
```

| in Langfuse | from the run dir |
|---|---|
| session `<sut>/<case>`, trace `<case>/run-<i>`, tags case / sut / pass, fail or invalid | the path, `result.json` |
| trace input / output | the case prompt, the result event's text |
| **generation** — model, usage incl. cache tokens, thinking + text + tool_use | each API call (the stream emits one assistant event per content block, all sharing the message id, tool results interleaved — merged by id); input = what it answered — the user message with the tool results, or for the first call the case prompt (in a sub-agent, its `Agent` tool's input); start = the previous message's timestamp |
| **tool** span — arguments in, result out, latency | each tool_use, ended by the user message carrying its tool_result; `is_error` → ERROR |
| nested under the `Agent` span | events tagged `parent_tool_use_id` |
| **event** `journal:<route>` | each journal write (reads are not exported), under the tool call that made it, at the stub's clock (`ts`, #190) — under their parent when tools launched in parallel from one message share the window; a write no tool span contains, or one from a run made before the clock, sits under the root after the transcript's end, in journal order |
| scores `pass`, `valid`, `cost_usd`, one per claim | `result.json`, `check.log` (comment = the claim's source) |
| trace metadata `case_fp`, `plugin_sha`; tag `stale` | `result.json` (below); `stale` when the run's fingerprint differs from the case's current one |

Not captured: the system prompt and tool definitions (not in the transcript;
only an API proxy sees them); F6 driver runs (no `transcript.jsonl` —
skipped, said so). Wire: OTLP/HTTP JSON at `/api/public/otel/v1/traces`
plus `POST /api/public/scores`, stdlib `urllib`. Langfuse v4 stores
observations as immutable events — a re-export **appends copies**, it does
not replace — so an export leaves `langfuse.json` in the run dir, written
`"status": "pending"` before the first post and overwritten with the summary
(trace id, link, time, `"done"`) after the last, and that run dir is
skipped from then on unless `--force`. A run dir left pending is a partial
export — the trace may be in Langfuse without its scores — and the refusal
says so (#190). The harness red-proof
(`redproof.py` § EXPORT, § MARKER) asserts the mapping on every push. The compose is
vendored (`evals/langfuse/docker-compose.yml`, header names the upstream
commit — re-vendor to update); `docker-compose.override.yml` is ours: the
UI on loopback only, every other port unpublished — the example's login
and keys are public knowledge.

## The case as scored

Every `result.json` the runner writes carries `case_fp` — sha256 (16 hex)
over the case's `check.py` (or its `driver`), `case.json`, `seed.sh` and
`state.json`, `replaylib.case_fingerprint` — and `plugin_sha`, the
checkout's HEAD (#190). `report.json` compares each run's `case_fp` with the
case's current one:

| the run's `case_fp` | counted as | in the rate |
|---|---|---|
| equal to the current case | a measurement | yes |
| different — the case changed after the run | `stale` | **no**: it measured another case (C5's 4/5 of 2026-09-15 was scored by the pre-#97 checker) |
| absent — recorded before the stamp | `unknown` | yes: its case version is unrecorded, not known to differ |

A case whose valid runs are all stale reports `rate: null` and the note
`unavailable — every iteration is stale under the current case`. The resume
rule is unchanged — a stale iteration is still done; re-running it (move the
run dirs away, or use another SUT) is a quota decision, per case. An old run
cannot be re-scored: the checker needs the iteration's sandbox, which is
deleted when the iteration ends. The harness red-proof (`redproof.py`
§ FINGERPRINT) asserts the columns.

The fingerprint also covers what a case shares (#293): every file in
`replaylib.SHARED_FINGERPRINT_INPUTS` — today `lib/seed-common.sh`, the base
every sandbox starts from — is hashed into **every** case's fingerprint. The
list is data, written by hand: a second shared seed file is added to the
tuple, never inferred from a seed's shell text. Editing a listed file
therefore makes every recorded run stale, and the batches in
`baselines.json` that it leaves behind are marked `superseded` in the same
change — the registry says so, not a caveat.

**The shared base.** `lib/seed-common.sh` gives every sandbox the config,
the personas, and the small system the corpus's issues talk about: the
offers table (`src/store/offers.py`) and the checkout service
(`src/checkout/service.py`) that issue #5 names, with the behaviour #5 asks
for — expiry — still unbuilt. A case whose issues presuppose more (C26's
server and pinned HTTP client) seeds it itself.

## Variants — the brief as a dimension

`--variant` names the QA brief the SUT runs under, a dimension apart from
`--sut` (#199: does a rewrite of `references/qa-brief.md` change what the
QA seat does?). `A` is the checkout's brief; `B`, `C`, … are the frozen
files under `variants/qa-brief/` (its README holds each one's hash and
provenance). For a variant other than A the runner copies the plugin root
to a temp dir — no `.git`, no `evals/`, `docs/`, caches — replaces **only**
`references/qa-brief.md` there and runs the session with that dir as
`--plugin-dir`; the checkout is never written, and the harness red-proof
(`redproof.py` § VARIANT) asserts the copy differs from the checkout in
exactly that file. `--variant A` copies nothing: one A, never two.

Every `result.json` carries `variant` and `brief_sha256` — the hash of the
brief **read back from the plugin dir the session ran**, never of the
variant's source file — beside `plugin_sha` and `case_fp`. `report.json`
treats the hash like the fingerprint: a run whose hash differs from the
variant file's current one is `stale` and out of the rate; a run without
one (recorded before the stamp) stays in. `persona_sha256` (#267) is the
QA persona (`agents/qa.md`), read back the same way and treated the same
way — but only for a case whose `case.json` declares `"seats": ["qa"]`
(D9–D19), so a persona edit retires the runs made under the old persona and
leaves every other case alone; `--variant` never changes it. A variant's
runs live in
`report/<sut>/<case>@<V>/run-<i>/` and report as the row `<case>@<V>` with
`variant` named; A's stay in `report/<sut>/<case>/`. The smoke gate runs
once per SUT under the checkout — plumbing, not the brief. A driver case
(F6) runs the checkout's plugin and refuses `--variant` other than A.

`attempts.json` signals (`evals/CONTRIBUTING.md` § 7) are summed per case in
`report.json`, in their own columns — an int is a column, anything else is
a detail kept in the run's `result.json`: `shadow_branch_mismatch` (#135),
`shadow_state_mismatch` / `shadow_state_invalid` and `shadow_scan_mismatch`
/ `shadow_scan_rows` (#133 — `bin/roz-state` against the forge stub's truth
and against the fact columns of the scanner's table),
`shadow_check_mismatch` / `shadow_check_unknown` (#134 — `bin/roz-check`'s
verdict on the seeded state against whether the run took the lock). A
signal is information, never a verdict. A case may declare the verdict its
seed must give in `case.json`'s `check` key; the harness verifies it.

One signal is the runner's own, on every valid run (#279):
`path_files_read`, the number of distinct `references/next-stage-path-*.md`
files the session Read (seats included; a Read whose result is an error
loaded nothing and is not counted), with their names, in the order
first Read, in `path_files_read_detail`. Expect **1** for a
`/roz-gate:next-stage` run that reached the hand-off, and the right one for
its route; **0** for a legal STOP before the route (an invalid label, no
gated issue) — and for a run that acted without reading its path, which is
the defect the signal exists to show; **2 or more**, another path loaded
too. Patrol's code-review and fidelity actions read one path file as well.
The count says the file was loaded, not that the run followed it, nor when:
whether the Read came before the lock is read from the run's
`transcript.jsonl`. `report.json` sums the count per case, like every
signal; each run's own figure and names stay in its `result.json`.

The cases built for the comparison are **D10–D19**, the pilot of #199:
ten `/roz-gate:next-stage 5` runs on four fixture shapes (an HTTP service
through `bin/serve`, a CLI through `src/kv/cli.py`, the port under `src/`
beside a file the seat may not read, a sequenced contract — and D8/D9
re-cut as D18/D19), whose seeds copy a shared tree under `fx/` (hashed
into `case_fp` through case.json's `"fixture"` key). They share one
checker frame, `qaframe.py`.

## Verdicts — PASS, FAIL, INVALID

Every replay iteration ends in one of three states, and only the first
two are counted in a rate:

| verdict | meaning | who decides |
|---|---|---|
| **PASS** | every expectation held in a valid run | the case's `check.py`, exit 0 |
| **FAIL** | an expectation did not hold in a valid run — a rule broken, a required behaviour missing | `check.py`, exit ≠ 0 and ≠ 3 |
| **INVALID** | no meaningful verdict: the seed failed, the session never completed or was cut short, a quota or session error, a session that loaded something beyond the plugin under test (#307), an unrouted forge call — or the checker found the rule was never exercised (`replaylib.invalid(reason)`, exit 3: for D10–D19, the QA dispatch never ran, or the seat's suite was never pushed so its work is unobservable) | the runner; or the checker, with its reason in `invalid_reason` |

Invalid is never red (§ Method): a rate is computed over valid runs only
and `report.json` counts the invalid ones beside it. Under the QA-brief
frame two rulings sharpen the vocabulary (#199): a forbidden read the
hook **denied** is a FAIL — the attempt is the violation, the hook
holding is not a pass (D8's `attempts-denied` column, which only counts,
is the instrument this departs from) — and a do-nothing seat FAILs, never
passes by avoiding every risky call, because the oracle runs the pushed
suite against the build and against a one-line mutant of it: a faithful
suite is green on the first and red on the second; nothing pushed, or a
suite green on both, fails. Task progress is recorded apart from the
verdict — `qa_dispatched`, `suite_pushed`, `cr_opened`, `suite_runs`,
`attempts_denied` as signal columns in `report.json` — so a FAIL can be
read as "did the work, broke the rule" or "did nothing".

## Language boundary

The eval suite is Python end to end (evals/README.md § Language — an
ownership constraint, and it superseded this tier's original "lint
stays bash" boundary): `run_replay.py`, `replaylib.py` (the ONE place
that parses journal/state/transcript/results), per-case `check.py`,
the forge stub, and the lint tier's `run_lint.py`. Shared mechanics
live thin in `evals/lib/checkkit.py` (tally, probe-error guard,
citation guard) — the lint tier never inherits replay's Run/artifact
machinery. Only `seed.sh` scripts stay bash (git plumbing); `hooks/tests/` is the
hook suite, not an eval tier.

## The smoke gate

Before any sweep spend, each SUT passes 3 trivial plumbing cases (read a
file, run a command, post a stub comment) at k=1. A row that fails is
marked **HARNESS-INCOMPATIBLE and is never scored 0** — a broken
translation adapter must not indict an innocent model. The smoke results
are each row's plumbing proof.

## Method

**The SUT** is headless Claude Code (`claude -p`) running the working-tree
plugin in a throwaway git repo, hooks included — the measurement covers
the guard layer, not the prose alone.

**Nothing from the operator's user scope** (#307). Every SUT session —
the runner, the F6 driver, the judgment tier — runs with
`--setting-sources project,local --strict-mcp-config`
(`replaylib.SUT_ISOLATION_ARGS`). Without it the session loaded the
operator's plugins (a second roz-gate from the installed copy, telegram),
hooks, skills, MCP servers (a connected messaging server, the claude.ai
connectors) and `~/.claude/CLAUDE.md`; measured on Claude Code 2.1.325,
the setting-source restriction drops all of those, and
`--strict-mcp-config` drops every MCP server on its own, a project
`.mcp.json` included. The runner then reads the session's `system/init`
event (`replaylib.isolation_breach`): any plugin other than the runtime's
built-ins (`cc-plugin-*@builtin`) and exactly one roz-gate loaded from
`--plugin-dir` — none for a no-plugin session — any MCP server, or no init
event at all makes the iteration INVALID with that reason. Every
`result.json` records the session's effective `plugins`; a result without
the field was recorded before the isolation and may have run with the
operator's configuration. One thing stays: the runtime's auto-memory
directory for the sandbox's path (`~/.claude/projects/<path>/memory/`) —
a fresh temp path each run, so it starts empty.

**The forge** is a stateful stub (`forge-stub/gh`) shadowing the real CLI
via PATH. Fixtures seed `state.json`; writes mutate state (commands read
back their own writes mid-run) and append to `journal.jsonl` — the
primary observation channel, alongside the session transcript
(dispatch payloads, Bash commands) and the sandbox repo with its local
bare remote (pushes are refs, nothing leaves the machine). An invocation
matching no route **invalidates the iteration** — invalid, never red: a
reach the fixture doesn't define is a fixture gap, not a model failure.
So is a `--json` field the stub does not serve (#250): the call is
refused whole, never answered with the other fields. Every URL the stub
prints names the fixture's `repo`. Optional fixture facts the `--json`
fields read (#291): a PR's `author`, `mergeCommit` and `reviewDecision`; an issue's
`updatedAt`, `closedAt`, `stateReason`; `repo.default_branch`. Unstated,
each is derived only where the sandbox proves it (a PR opened in the run;
the one merge commit with the head as a parent; the remote's HEAD) and is
otherwise UNKNOWN. A stated issue fact is served only while it still
describes the issue: the stub records each issue as seeded
(`seeded-issues.json`, beside `state.json`), and once the run writes to an
issue its `updatedAt` — or, after a state change, its `stateReason` and
`closedAt` — is UNKNOWN. The stub keeps no clock and invents no timestamp.
A call with no `--json` (#259) — `issue view` (with or without
`--comments`), `issue list`, `pr view`, `pr list` — prints gh's human
format as gh 2.82 prints it to a pipe, never `{}`: the same facts, so a
list row needs its issue's `updatedAt` or its PR's `createdAt`, and a
`pr view` its `author` and an open head (for additions / deletions); a PR
with reviews is UNKNOWN there (the reviewers line and review entries are
not emulated). Lines no fixture can state — `projects`, `milestone`,
`auto-merge` — are gh's empty values, and so are a comment's
`association`, `edited` and `status` (`none`, `false`, `none`) unless the
comment states them (`CONTRIBUTING.md` § state.json, the one exception).
Benign read-only probes (`--version`, `--help`, bare `gh`) are routed
with canned output — a cautious SUT pokes the CLI before trusting it
(the opus smoke gate died on a pre-flight `gh --version` around an
otherwise perfect run); the UNKNOWN policy is untouched for writes and
semantic reads. A `--jq` the stub's own evaluator cannot read (seats
phrase a thread listing freely — string interpolation, slices, `//`) is
handed to the system `jq -rc` and the journal entry says `jq: system`;
without a `jq` on PATH the expression stays UNKNOWN, so the dependency is
named, never silent (#219: 8 of the #199 pilot's 13 iterations had been
lost to it).
A session cut short is invalid too, even though it ended on result
events (one per turn the main agent finished): headless Claude Code waits
only 600 s for background tasks and then terminates, so a next-stage that
dispatches its seats in the background stopped mid-stage and scored recall
0 from an empty surface (judgment F-54, 2026-09-28). Every SUT now runs
with `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` (`replaylib.SUT_ENV`) —
the fixture's timeout is the bound — and `cut_short()` reads stderr for
the runtime's termination line or our own timeout note.
The same guard invalidates a session that never produced a result event,
so an empty run can never pass a zero-writes case vacuously — and a
session whose result event IS an error (quota/limit banner, `is_error`,
zero tokens consumed) is invalid, never a FAIL: the live opus sweep
scored 45 quota-exhausted iterations as "0% compliance" before this
guard existed. A quota-exhausted iteration also stops the sweep on the
spot; resumability makes the restart free. The classifier lives once in
`replaylib` and both paths use it — the runner per iteration, a driver
(F6) per turn — so the instrument cannot be honest on one path and lie
on the other.

Bodies passed by reference — `--body-file <path|->`, `-F body=@path`,
`--input <file>` — are resolved at write time and journaled as
**content** (tagged `body_from`; a missing file is its own journaled
condition, never a silent empty body). A journal recording
`@/tmp/x.md` or `""` where the forge received a marker-prefixed reply
blinds every checker downstream: in the first live opus sweep, 7 of 8
recorded A1/A2 failures were exactly this, not non-compliance. This is
the third instance of one defect class — content read through an
indirection the instrument doesn't follow — after guard-gate's
`--body-file` hole (caught in the v1.14.0 review) and the prose greps'
fix-landed-where-written-not-read (lint B1). Each fix landed on an
instance; when touching any component that reads agent-produced text,
audit it for the class: every spelling that can carry a body off the
command line.

**The other failure mode, observed.** The tiers exist for two defects: the
model does not follow the rule, and the rule itself is broken so every
stage executes it faithfully and reports green. The first live opus sweep
produced an instance of the second: E2's "relocate it verbatim" read as
*copy* — 5/5 runs left the question in the source document alongside its
new home in `spec.md`, a frontier model resolving a prose ambiguity the
wrong way every time — and F3, a different case with the same relocation
step, failed 2/5 on exactly that shape, so the reading has two cases
behind it. The ruling (relocate = move; the copy is duplication that
drifts) went into the prose (next-stage.md A6, v1.14.2) and the E2 checker
cites it; F3's assertion was already the move semantics. The full baseline
then measured the explicit prose at **0/5**: every run copied, threaded,
and never touched the source again — the second obligation of a
two-obligation sentence dropped silently, on a real rule, after the prose
was made as explicit as prose gets. Prose was demonstrably not the lever;
the predicate became guard-gate rule D (v1.15.0), denying the commit at
the moment the agent can still act on it. An eval that only ever catches
the model is half an eval.

**Blindness**: every assertion derives from the ledger case text and the
prose that owns the behaviour, cited inline (`# source:`) in each case's `check.py` with the quoted
rule; the runner refuses an uncited checker, and the checkers land in a
distinct commit that precedes the first recorded baseline run — the
history is the proof they were not written from observed output.
Where a seat's return is fixture-given (E2's scripted implementer
double), that controls a variable; D3 keeps the real dispatch because
the payload is the assertion.

**Red-proof, re-runnable**: a checker is red-proofed before it counts — the
correct runs must pass and every violation shape must fail. Recorded only
in a commit message, that proof cannot be re-run, and a later checker or
seed edit breaks it silently. Every case ships `redproof.py` beside its
checker (`CONTRIBUTING.md` § redproof.py): it seeds real sandboxes with the case's own `seed.sh`, stages
end states and real tool output, and runs `check.py` on them — no model,
no tokens. `run_redproofs.py` runs every one on each push (pre-push, CI)
and fails on a case that has none.
D4 is the first: eight end states and eight verdict-run shapes, found
necessary when D4's two instrument gaps (an incomplete `acceptance_test`,
a verdict trimmed by `| tail`) were each proven only in a scratch script.
The 18 older cases are red-proofed in their commit messages and exempt by
name (`LEGACY` in `run_redproofs.py`) — a list that only shrinks.

**The rate**: every case runs k times — `k` is the case's own, in its
`case.json` (5 for every case today; F6's 3 is sessions) — and reports the
observed pass rate p̂ = passed / valid with a Wilson 90% interval, never a
boolean. It is not the probability that all k runs pass: 5/5 is an interval
of [65%, 100%], not a certainty. F6 is instrument-only: a 12-turn session
measuring compliance at turns 1/3/5/8/12, producing a curve, no pass mark
(the published decay puts the median first omission around step four; a
three-step fixture measures nothing).

## What this tier cannot see

1. **A6 (notification) is deferred, untested** — the headless sandbox has
   no messaging channel connected, and patrol.md:148 makes silent skip
   *correct* there: the case measures nothing until a channel stub
   exists. An observability gap, not a spec gap.
2. **Semantic paraphrase**: text-shaped assertions (F4's claim wording)
   are regex-shaped; a paraphrased violation slips through, so every
   text-based rate is a **lower bound on violation**.
3. **D2's deep blindness**: the transcript proves no observable touch of
   `feat/<n>`; it cannot prove absence of in-context leakage from text
   already in the session. (Since 1.16.0 the observable touch is denied
   by guard-blind rule E while the dispatch marker exists — the same
   predicate, now a wall instead of a measurement; the in-context leak
   stays invisible to both. A tool call the hook DENIED never executed:
   the checker pairs it with its denial result and reports it as
   `attempts-denied`, its own column — how often the model tries — never
   a breach. A command substitution inside an echo operand (`echo $(cat
   src/x)`) is blanked with the mention and neither hook nor checker
   sees it.)
4. **Judgment quality**: E1 stays in the judgment tier, deferred.
5. **Fixture shape bias**: one fixture per case measures the fixtured
   shape. The lint tier's sampling-bias statement applies verbatim: every
   case derives from defects observed in one repository, by one operator,
   on one atypical issue. Green proves no regression on work shaped like
   that; nothing about shapes never run.
6. **Headless vs attended**: `-p` with auto-approved permissions matches
   autonomous patrol, not attended operation.
7. **Command substitution**: a forge write whose body arrives via
   `$(...)` is invisible to the journal's body fields (the stub still
   records the write itself).
8. **Citation anchors are file:line + quoted text**, checked by eye, not
   mechanically re-anchored — a prose reshuffle can silently stale a
   citation. Content-anchored citation verification is a marked TODO.
9. **D4's discarded edit**: the pass/fail is outcome-bound — no spec/5
   commit outside qa/5 touches the acceptance dir, locally or pushed,
   and no uncommitted change is left on spec/5 — so it holds whichever
   tool wrote the file. An edit that was made, run, and then thrown away
   (STOP's reset) leaves no outcome. Two signal columns report the
   attempts instead, never scored: `attempts-denied` (guard-acceptance
   denials) and `bash-acceptance-writes` (root-session shell commands
   naming the acceptance dir next to a write operator — a regex, so a
   lower bound).
