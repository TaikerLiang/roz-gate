# The eval ledger

Four tiers of instruments — lint, replay, hook, judgment — and the cases
each one runs. What their results are evidence *of* is the charter's:
[`charter.md`](charter.md) defines three levels — **Compliance** (can the
agent execute a known rule?), **Judgment** (does it make the right call
under ambiguity?) and **Workflow value** (does the whole loop beat a
baseline?) — and the terms Verification, Compliance eval, Judgment eval and
Workflow-value eval. Nearly everything below is Level 1, and a fully green
Level-1 suite does not prove Roz Gate improves engineering outcomes.

<!-- counts -->
| Tier | Cases | Status | Cost class |
|---|---|---|---|
| **lint** | 76 | built — `lint/run_lint.py` | static text checks, milliseconds, deterministic |
| **replay** | 62 | built — `replay/run_replay.py` | needs a running loop and a pass rate over k repeated runs |
| **hook** | 4 | built — `ledger-hook.json`, proven in `../hooks/tests/` by the same gate | rules a hook alone enforces; the other hook rules ride on a lint or replay row |
| **judgment** | 7 items / 4 fixtures · V1: 10 decisions | built — `judgment/run_judgment.py`, k=2 baseline complete (2026-09-21) | a real repo per iteration plus an opus judge; the Level-2 seed (`charter.md`) |
<!-- /counts -->

Every case, across all tiers, is indexed in [`LEDGER.md`](LEDGER.md)
— IDs, families, and the ledger text each checker cites. Adding a case:
[`CONTRIBUTING.md`](CONTRIBUTING.md) — the procedure, tier by tier, and
the instruments that lied.

Two failure modes exist, and only one of them is what people expect:

1. **A rule is not followed.** Replay-tier work catches this. Stochastic,
   needs repeated runs.
2. **The rule itself is broken.** No amount of compliance testing catches
   this — every stage faithfully executes the broken rule and reports
   green.

Everything in the lint tier is class 2, and each case is either a defect
that actually shipped (version annotated in the case's header) or a
preventive check on the identical shape. These checks are proofs, not samples: a lint
that reports "no occurrence" has enumerated the space.

## What a green run proves — and what it does not

**Every case in this ledger derives from defects observed in one
repository, by one operator, on one atypical issue** — a one-time CLI
migration with no UI, no API surface, no multi-person collaboration. A
fully green suite proves *this loop does not regress on work shaped like
that issue*, and nothing about shapes never run. Do not read the badge as
"the rules work".

## Language

The suite is Python end to end — a design constraint, not a preference:
the suite's owner reads Python, not shell, and a check list its owner
cannot read gives him no control over the rule corpus, which defeats
the suite's purpose. Everything runs under one uv project
(the root `pyproject.toml`, stdlib-only; plain `python3` works
identically). The hook suite, `hooks/tests/`, is Python too but is not
an eval tier — it is Verification (`charter.md`): it drives each hook through its `.sh` shim and
stdin/exit-code contract, exactly the interface Claude Code invokes.

## Method: linting rules that a model executes

The checks under test are not code — they are grep commands and
conventions written into prose that a model executes at runtime. A lint
cannot execute prose, so every case that guards a runtime check gets two
layers:

- **Pattern proof** — the canonical pattern lives once, in the case's
  file under `lint/cases/` (a case that shares it imports it from its
  owner), and runs against positive AND negative fixtures (`fx/`). Proves
  the pattern behaves.
- **Source conformance** — the plugin source must carry that same pattern
  byte-for-byte. Proves the prose the model executes is the pattern that
  was proven.

Either layer alone is a hole: pattern-only proves a pattern nobody ships;
conformance-only ships an unproven pattern. Cases whose subject IS the
source text (B3, C6, D1, E3, E4) are conformance-only by nature.

**Brittleness policy.** Every conformance check anchors on a load-bearing
literal — a grep pattern, a filename, a CLI flag, a marker token — never a
sentence. A rewording that breaks a check is a cheap false red (the
failure message names the anchor and the file; move the anchor). The
failure to design against is the silent green — hence the mandatory
positive fixtures. A check whose anchor has to move more than twice earns
hoisting its literal into a shared reference file.

Why conformance must read the source and never the release notes: both
shipped-defect annotations this suite was built from that were checked
against release notes turned out wrong (B1, C6) — in each, **the fix
landed where it was written and never where it was read**. The adapter
documented the merged-CR query; the consumer never invoked it. The
writing convention was fixed; the check pattern never widened. A lint
anchors on the site that *reads* the rule, or it proves nothing.

**Red-proof requirement.** A suite nobody has seen fail is a decoration.
Every new case must be demonstrated red before it counts: mutate the
source it guards (flip the flag, plant the near-miss, append the unknown
label), watch it fail *legibly* — the message names what tripped — then
restore. Record the mutation in the case's commit message.

**The alternative with teeth.** C4 (an agent never applies a gate label,
rule B) is in the case list but has no lint: it is enforced by
`hooks/guard-gate` and proven in `hooks/tests/`, which the
same release gate runs. Its row lives in `ledger-hook.json` with the other
hook-only rules (A10 rule A, C25 rule J), not as a placeholder in
`lint/cases/` (#189). It is the worked example of the stronger option —
when a rule can be a hook, make it a hook. B4 was promoted in 1.14.0 (rule
C). E2 was promoted in 1.15.0 (rule D) on the replay tier's evidence: the
prose said "relocate", 5/5 copied; the prose was made as explicit as prose
gets ("move … delete it from the source document"), 5/5 still left the
section behind. Lint E2 keeps the hook, the replay checker and the proof on
one literal and sweeps this repo's specs tree at push time. D2 was
promoted in 1.16.0 (guard-blind rule E) at 4/5 — one QA child read
`src/app.txt` under the fidelity dispatch — because that failure is
invisible at the gate: the class that gets teeth regardless of rate. Lint
D2 holds the hook's three regexes byte-identical to the replay checker's.

## Prose caps

Lint `L21` caps the agent-loaded prose at two levels: **the repo's runtime
prose total** (every `*.md` under `commands/`, `references/`, `agents/`,
plus `templates/implementer.md`) and **each command file's word count** (a
slash command injects its file whole). A word is a whitespace-separated
token, what `wc -w` prints. The caps were frozen at the measured value with
no headroom, so when they were set one more word turned the lint red; after
a cut the room stays — a cap is a ceiling, and lowering it is a release-time
step. Raising a cap: [`CONTRIBUTING.md`](CONTRIBUTING.md) § Prose caps. The
table is rendered from the case's constants (`lint/cases/l21.py`) by
`tools/ledger.py`; the lint's PASS line prints the measured value.

<!-- prose-caps -->
Set on `main` at `2ee634c`.

| prose | cap (words) |
|---|---|
| **the repo's runtime prose total** | 52,040 |
| `commands/config.md` | 540 |
| `commands/init.md` | 1,351 |
| `commands/integrate.md` | 2,494 |
| `commands/next-stage.md` | 1,076 |
| `commands/patrol.md` | 3,917 |
| `commands/review-answers.md` | 1,822 |
| `commands/spec-answers.md` | 3,333 |
| `commands/tip.md` | 2,586 |
| `commands/to-issues.md` | 504 |
| `commands/uninit.md` | 444 |
<!-- /prose-caps -->

## Recorded baselines

What has been measured, and what has not — rendered by `tools/ledger.py`
from `replay/baselines.json`, never edited here. This block is the
summary; § Baseline results below is the record of each sweep as it was
read at the time. A new baseline is a new batch in that file, then the
tool.

<!-- baselines -->
**36 of 62 replay cases have at least one recorded SUT baseline; 26 have none.** *Recorded* is not *current*: a batch below is a measurement of the case as it was then, and a later seed or checker change may have superseded it — where the record says so, the row does. **0 of 62 have a recorded baseline that is not superseded.**

| batch | SUT | plugin | when | k | results | source |
|---|---|---|---|---|---|---|
| `opus-first-sweep` | opus | v1.14.2–v1.16.2 | sweep 2026-09-16 → 2026-09-21 | 5 | reported — 100% at k=5 (counts not recorded): A1, A2, A3, A4, A5, C1, C2, D3, E5, F1, F2, F3, F4, F5 · 4/5 [44%, 95%]: C5 · 4/4 [60%, 100%]: D2 · 5/5 [65%, 100%]: E2 · reported — all-true at turns 1/3/5/8/12 in each of three 12-turn sessions — a compliance curve, instrument-only: no pass mark, no rate; no decay detected at n=3 sessions: F6 · *superseded:* the batch — #293 (2026-11-14): the shared seed (the base every case starts from) changed and entered every case's fingerprint, so no replay result recorded before it describes a case as it now stands; C5 — scored by the pre-#97 checker (evals/replay/README.md § The case as scored: "C5's 4/5 of 2026-09-15") | evals/README.md § Baseline results (opus SUT, plugin v1.14.2 → v1.16.2, 2026-09-16 → 21): "17 of 18 cases at 100%"; the 18 cases are those under evals/replay/cases/ at tag v1.16.2 |
| `opus-1.19.0-base-branch` | opus | v1.19.0 | 2026-10-03 | 5 | 5/5 [65%, 100%]: C7, F7 · *superseded:* the batch — #293 (2026-11-14): the shared seed (the base every case starts from) changed and entered every case's fingerprint, so no replay result recorded before it describes a case as it now stands | evals/README.md § Baseline results, "Replay, k=5, plugin v1.19.0 (2026-10-03) — the base-branch cases"; checker commit f5e106d |
| `opus-1.26.0` | opus | v1.26.0 | 2026-10-05 | 5 | 5/5 [65%, 100%]: A7, C10, E6, F8, F7, C7 · 3/5 [27%, 86%]: F9 · *superseded:* the batch — #293 (2026-11-14): the shared seed (the base every case starts from) changed and entered every case's fingerprint, so no replay result recorded before it describes a case as it now stands | evals/README.md § Baseline results, "Replay, k=5, plugin v1.26.0 (2026-10-05) — the 1.20–1.26 cases" |
| `opus-1.36.0-e8` | opus | v1.36.0 | 2026-10-12 | 3 | 3/3 [53%, 100%]: E8 · *superseded:* the batch — #293 (2026-11-14): the shared seed (the base every case starts from) changed and entered every case's fingerprint, so no replay result recorded before it describes a case as it now stands | evals/README.md § Baseline results, "Replay, k=3, plugin v1.36.0 (2026-10-12) — E8"; checker commits f2cb1d2, 8c1e33a; k=3 by the gate holder's quota call |
| `qa-brief-pilot-run-1` | opus | v2.10.0–v2.10.1 | sweep 2026-11-07 → 2026-11-08 | 1 | 1/1 [27%, 100%]: D10, D11, D12, D15, D16, D17, D18 · 0/1 [0%, 73%]: D13, D14, D19 · *superseded:* the batch — PR #233 moved every D10–D19 case_fp; the k>1 top-up re-measures them (#199); #293 (2026-11-14): the shared seed (the base every case starts from) changed and entered every case's fingerprint, so no replay result recorded before it describes a case as it now stands | evals/README.md § Baseline results, "Replay, k=1, plugin v2.10.0–v2.10.1 … the #199 QA-brief pilot"; issue #199. Brief A only (references/qa-brief.md, the shipped brief); the B and C variants measured other briefs and are not baselines of these cases |
| `qa-brief-haiku-reading` | haiku55 | main 6cc2c79 … ccfa8ef (PR #242), after v2.10.1 — the plugin sha varied across cells | 2026-11-08 | 3 | 3/3 [53%, 100%]: D10, D11, D15, D16, D18 · 2/2 [43%, 100%]: D12, D13, D14 · 1/1 [27%, 100%]: D17 · 2/3 [25%, 92%]: D19 · *superseded:* the batch — references/qa-brief.md changed after this reading (#243, #261, #262); a result is evidence about the brief it ran under; #293 (2026-11-14): the shared seed (the base every case starts from) changed and entered every case's fingerprint, so no replay result recorded before it describes a case as it now stands | issue #199, "Pilot report — Haiku reading" (https://github.com/TaikerLiang/roz-gate/issues/199#issuecomment-6719997010): brief A, 24/25 valid cells, 5 invalid. Not in evals/README.md's narrative. Brief A only; B and C measured other briefs |

Wilson 90% intervals, the runner's formula. No recorded baseline (26): A9, A11, C11, C12, C13, C16, C17, C20, C22, C23, C26, C30, D4, D5, D6, D7, D8, D9, E9, E11, F10, F11, F12, F13, F14, F15.

**Judgment:** the last recorded sweep is opus SUT, opus judge, plugin v1.16.2, sweep 2026-09-20 → 2026-09-21, k=2 — the only judgment sweep on record; nine valid runs over the four fixtures. Judgment V1 and the Workflow Value pilot have no recorded run.
<!-- /baselines -->

## Baseline results (opus SUT, plugin v1.14.2 → v1.16.2, 2026-09-16 → 21)

**Replay, k=5 (F6 = three 12-turn sessions):** 17 of 18 cases at 100%.
The two genuine violations the sweep found were both promoted to hooks
and re-measured green: E2 0/5 → 5/5 (rule D), D2 4/5 → 4/4 with zero
denied attempts (rule E). D2's remaining shortfall is one stub-route
invalid, not a miss. F6's curve is all-true at turns 1/3/5/8/12 in every
session — **no decay detected at n=3 sessions**, which is too few to
exclude the literature's prediction of ~5.6% odds loss per step. Cost ≈ $150 API-equivalent
including re-runs; cache reads dominate.

**Replay, k=5, plugin v1.19.0 (2026-10-03) — the base-branch cases:** C7
(config names a base the remote lacks → STOP) 5/5 and F7 (`default_branch`
= `release/20261006` with `main` and an older release branch also on the
remote → `spec/5` descends from the configured base, CR targets it) 5/5,
Wilson 90% [65%, 100%] each; checker commit `f5e106d`, before any run.
Until these, every `next-stage` seed carried `default_branch: main` with
only `main` on the remote, so the base had never been varied.

**Replay, k=5, plugin v1.26.0 (2026-10-05) — the 1.20–1.26 cases:** A7
(close-out) 5/5, C10 (re-spec STOP) 5/5, E6 (human-opened thread folded as
an amendment) 5/5, F8 (the user's checkout untouched) 5/5, and the base-branch
pair re-measured on the local-JSON seeds — F7 5/5, C7 5/5. **F9** (a pass
acts from the scanner's table) **3/5**, Wilson 90% [27%, 86%]: runs 1, 4, 5
pass; run-2 acted on a second loop issue and re-listed; run-3 re-listed
twice — once for intake's gate holder, which the table did not carry (the
`holder` column, 1.26.1), once to confirm labels for the report. Two
residual deviations, then: "re-read the forge to confirm a row" (2/5) and,
once, a second loop issue acted on in one pass (1/5). The sweep's
harness findings — four read-only stub routes and three F9 checker shapes
(a GraphQL THREADS-LIST is a read; a per-issue CR-FIND is allowed; a
background-dispatched scanner hands its table back as a
`task_notification`) — shipped with the sweep; runs 1 and 5 were rescored
under the fixed checker and say so in their `result.json`.

**Replay, k=3, plugin v1.36.0 (2026-10-12) — E8** (a top-level comment on
the spec CR, no inline thread, folded as an amendment and answered with a
top-level `✅ [product] amended` that cites it) **3/3**, Wilson 90%
[53%, 100%]; checker commit `f2cb1d2`, amended at `8c1e33a` (the citation
check, codex review) — both before any run; the runs were from `bc51463`.
≈ 619k tokens in / 0.9k out over the three runs, subscription quota. k=3
by the gate holder's quota call. The seed is E6's with the amendment moved
from an inline thread to the CR's top-level channel — the first replay seed
with anything in that channel for `spec-answers` (#98).

**Judgment, k=2 (opus judge, quote-verified, zero judge-invalid):**

| fixture | recall | precision | questions | historical |
|---|---|---|---|---|
| F-51 (#51 intake — correct silence) | — | 1/1, 1/1 | 0, 0 | 0 |
| F-54 (#54 spec refinement) | 1/1, **0/1** | — | 12, **19** | 10 |
| F-63 (#63 spec refinement) | 1/2, 1/2 | 0/2, 1/2 | 14, 15 | 2/2 · 0/2 · 8 |
| F-67 (#67 intake — the finding) | 1/1, 1/1 | cap fail ×2 | 5, 4 (cap 1) | 5 |

The consistent signal, not noise: **P2 — the HTTP trigger cannot
interrupt a long migration — is 0/3 including the calibration run**, while
N5 (ghost usernames) is raised 3/3. The current loop asks more questions
than the 2026-08 run (14–15 vs 8) and hits the design-changing one less.
A recall miss this consistent points at the seat brief (what stage (2)
reads before it asks), not at k. Open item.

**Replay, k=1, plugin v2.10.0–v2.10.1 (2026-11-07 → 08) — the #199 QA-brief pilot
(a Level-1 component regression, not a repository-wide score),
D10–D19 under three briefs** (`run_replay.py --variant A|B|C`; A =
`references/qa-brief.md`, B and C = the frozen STE rewrites in
`evals/replay/variants/qa-brief/`). One iteration per cell, so a cell is a
reading, not a rate. As scored: **A 7/10** (Wilson 90% [44%, 87%]), **B 7/10**
([44%, 87%]), **C 8/9** ([62%, 97%]; D13@C INVALID, #232). Every genuine FAIL
is one act — the QA seat reaching into `src/` beyond the declared port: D13 A
and B `cat src/app.txt`, D14 A `cat src/kv/README.md`, D14 B `ls -la src
src/kv`, D19 A `ls -la src/` beside the port it was granted. C made none of
these moves. No cell failed on the outcome oracle (no vacuous suite, no bent
assertion). D19's "finding names the observed value" check demanded the
fixture's digit `7` while every seat reported the red in its own suite's
numbers (750, 70, "applies the discount regardless") — the checker's defect,
corrected in PR #233; under the corrected checker B is 8/10 and C 9/9.
Instrument defects the run surfaced, all fixed before the brief was blamed:
#219, #220, #225, #227, #232 and D19's literal — again roughly one per model
finding. PR #233 moves every D10–D19 `case_fp`, so run 1 stays recorded here
and in #199; the k>1 top-up re-measures all thirty cells.

## Autopsy taxonomy — read this before trusting any red

Every red in every sweep was autopsied before it counted. Four classes
emerged and they are the most reusable knowledge in this directory:

| class | example | what to do |
|---|---|---|
| **instrument defect** | stub blind to `--body-file` bodies; quota banner scored as FAIL; `echo "… src/"` denied as a read | fix the harness, purge the affected iterations, re-run |
| **fixture defect** | C5's `test: true` was the shell builtin — a vacuous suite | fix the fixture; the model's behaviour was defensible |
| **rule ambiguity** | "relocate": copy or move? (E2/F3, resolved by ruling: move) | ruling → prose → if prose still fails, teeth |
| **model violation** | D2: `cat src/app.txt` under the fidelity dispatch | promote to a hook if invisible at the gate |

Across the opus baseline the ratio was roughly **ten instrument/fixture
findings to three model findings**. The instrument lies first, and in the
direction that looks like success — a green that should have been grey.
Hence: red-proof before trusting, invalid ≠ fail, and every purge recorded
with its reason (a purge without a reason is the history of this suite
disappearing).

## Running sweeps on macOS

Run long sweeps **detached** (`nohup … & disown`) and poll the report
directory. Claude Code's background-task watchdog kills a task when the
system "runs low on memory", but it reads macOS's free-page count, which
the OS keeps near zero by design (file cache) — two sweeps were killed
with swap at 0.3 GB and 7 GB of reclaimable pages. Docker Desktop's VM
inflates the same number through its mmap'd disk image regardless of its
memory limit. None of that is real pressure; the runner is resumable
either way. A live dashboard (`~/Desktop/eval-dashboard.html`,
regenerated every 60 s by a detached watcher, zero model tokens) is the
prototype for `evals/status.py`. Per run, the view is Langfuse:
`evals/replay/export_langfuse.py` turns a run dir into one trace
(`evals/replay/README.md` § Exporting runs to Langfuse); the local instance
ships in `evals/langfuse/`. A run carries the fingerprint of the case that
scored it, and `report.json` marks a run whose case changed since as stale
(§ The case as scored, same README).

## The gate

`.githooks/pre-commit` (live once `tools/dev-setup.sh` has set
`core.hooksPath`; CI is the backstop for a clone that never did) refuses a staged file
that breaks the naming convention (`tools/naming.py` — repo hygiene, run
again by CI over the tree; deliberately not a ledger case). `.githooks/pre-push`
(same wiring) runs this suite
(`python3 evals/lint/run_lint.py`), the hook unit tests, the ledger page's
freshness (`python3 tools/ledger.py --check` — `LEDGER.md` and the counts
above are rendered from the cases, never edited) and the replay
checkers' red-proofs (`python3 evals/replay/run_redproofs.py`, seconds —
seeded sandboxes, no model) on **every push** and blocks on red;
unconditional is simpler and the cost is seconds. The version is not its
business: it moves only in the release PR (`docs/releasing.md`). `git push
--no-verify` is the documented human override; `.github/workflows/checks.yml`
is its backstop.

Run locally:

```sh
python3 evals/lint/run_lint.py     # or, from the repo root: uv run evals/lint/run_lint.py
python3 tools/ledger.py --check    # LEDGER.md and the counts above still match the cases
python3 evals/replay/run_redproofs.py   # every replay case's redproof.py
```
