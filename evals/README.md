# The eval ledger

Three tiers of evidence that the workflow's rules hold.

| Tier | Cases | Status | Cost class |
|---|---|---|---|
| **lint** | 14 | built — `lint/run_lint.py` | static text checks, milliseconds, deterministic |
| **replay** | 18 | built — `replay/run_replay.py` | needs a running loop and pass^k over repeated runs |
| **judgment** | 7 items / 4 fixtures | built — `judgment/run_judgment.py`, k=2 baseline complete (2026-09-21) | a real repo per iteration plus an opus judge; the only tier that measures whether the spec stage earns its cost |

Every case, across all three tiers, is indexed in [`LEDGER.md`](LEDGER.md)
— IDs, families, and the ledger text each checker cites.

Two failure modes exist, and only one of them is what people expect:

1. **A rule is not followed.** Replay-tier work catches this. Stochastic,
   needs repeated runs.
2. **The rule itself is broken.** No amount of compliance testing catches
   this — every stage faithfully executes the broken rule and reports
   green.

Everything in the lint tier is class 2, and each case is either a defect
that actually shipped (version annotated in the runner) or a preventive
check on the identical shape. These checks are proofs, not samples: a lint
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
an eval tier: it drives each hook through its `.sh` shim and
stdin/exit-code contract, exactly the interface Claude Code invokes.

## Method: linting rules that a model executes

The checks under test are not code — they are grep commands and
conventions written into prose that a model executes at runtime. A lint
cannot execute prose, so every case that guards a runtime check gets two
layers:

- **Pattern proof** — the canonical pattern lives once in `run_lint.py`
  and runs against positive AND negative fixtures (`fx/`). Proves the
  pattern behaves.
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

**The alternative with teeth.** C4 (`track: fast` + `ready-for-spec`
refused) is in the case list but has no lint: it is enforced by
`hooks/guard-gate` and proven in `hooks/tests/`, which the
same release gate runs. It is the worked example of the stronger option —
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

## Baseline results (opus SUT, plugin v1.14.2 → v1.16.2, 2026-09-16 → 21)

**Replay, k=5 (F6 = three 12-turn sessions):** 17 of 18 cases at 100%.
The two genuine violations the sweep found were both promoted to hooks
and re-measured green: E2 0/5 → 5/5 (rule D), D2 4/5 → 4/4 with zero
denied attempts (rule E). D2's remaining shortfall is one stub-route
invalid, not a miss. F6's curve is all-true at turns 1/3/5/8/12 in every
session — **no in-session decay observed**, against the literature's
prediction of ~5.6% odds loss per step. Cost ≈ $150 API-equivalent
including re-runs; cache reads dominate.

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
prototype for `evals/status.py`.

## The gate

`.githooks/pre-commit` (live once `tools/dev-setup.sh` has set
`core.hooksPath`; CI is the backstop for a clone that never did) refuses a staged file
that breaks the naming convention (`tools/naming.py` — repo hygiene, run
again by CI over the tree; deliberately not a ledger case). `.githooks/pre-push`
(same wiring) runs this suite
(`python3 evals/lint/run_lint.py`), the hook unit tests and the replay
checkers' red-proofs (`python3 evals/replay/run_redproofs.py`, seconds —
seeded sandboxes, no model) on **every push** and blocks on red. "Must pass before
every version bump" is a subset of that; unconditional is simpler and the
cost is seconds. `git push --no-verify` is the documented human
override; `.github/workflows/checks.yml` is its backstop.

Run locally:

```sh
python3 evals/lint/run_lint.py     # or, from the repo root: uv run evals/lint/run_lint.py
python3 evals/replay/run_redproofs.py   # every replay case's redproof.py
```
