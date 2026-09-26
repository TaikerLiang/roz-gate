# Adding an eval case

How to add a case to the eval ledger — for a human contributor and for an
agent working in this repository alike. The principles behind each step
live in `README.md` (lint method, autopsy) and `replay/README.md` (replay
method); this page is the procedure. Hooks have their own:
`../hooks/README.md`.

This is dev-time material for the plugin repository. It is never loaded
by the plugin at runtime — which is why it is here and not in
`references/`.

## 1. Start from evidence

A case starts from a measurement or a shipped defect, never from a worry
— the same bar as a hook rule. Name it: the replay run that went red,
the release that shipped the defect, the review that found the gap.

## 2. Write it in the ledger first

`LEDGER.md` is the source; checkers copy it, never the other way round.

1. **Family** — the letter whose "what it guards" line fits (A–F; J and
   L are lint-only). A case that fits none is a question for the ledger's
   owner, not a new letter on your own.
2. **ID** — the family's next unused number. Numbers are never reused.
3. **Title** — the invariant, stated as what holds: *"The acceptance
   suite changes only on qa/<n>"*, not *"agent edits tests"*.
4. **Ledger text** — the expected outcome, then in parentheses why it
   matters. Every checker will quote it in `# source: ledger <ID> — "…"`.

## 3. Pick the tier

Take the first that can decide it:

| if the rule… | put it in | example |
|---|---|---|
| can be decided from one tool call as it happens | a **hook** (`../hooks/README.md`) | C4, B4 → rule C, E2 → rule D |
| lives in prose and is provable by reading the source | **lint** | B1, C6, D1 |
| is about what a model actually does with the prose | **replay** | A1–A5, D4, F1–F5 |
| needs a judgment of meaning ("did it raise the thing that mattered") | **judgment** | P1…N10 |

A rule that can be a hook should be one; a lint or replay case may still
measure it (D2 is all three).

## 4a. A lint case

One block in `lint/run_lint.py`:

```python
# ---------------------------------------------------------------------------
# B1 · a compound tag evades the literal it contains        (defect: 1.12.0-)
UNV = r"(^|[(,])[ \t]*unverified"
must_match("B1 pattern: compound (from Q4, unverified) found", UNV, fixture("b1_compound.md"))
must_not_match("B1 pattern: the word in prose NOT flagged", UNV, fixture("b1_negative.md"))
src("B1 conformance: Path B check carries the widened pattern",
    "commands/next-stage.md", "grep -nE '(^|[(,])[[:space:]]*unverified'")
```

- **Header**: `# <ID> · <title>` and `(defect: <version>-)` or
  `(preventive)`.
- **Two layers** when the rule is a pattern the model executes: a
  *pattern proof* against positive **and** negative fixtures in
  `lint/fx/` (`must_match` / `must_not_match`), and *source conformance*
  that the plugin source carries the same literal (`src`). A rule whose
  subject is the source text itself is conformance-only.
- **Anchor on the site that reads the rule**, never where it is written or
  on release notes — B1 and C6 were "fixed" where written and never where
  read.
- **Anchor on a literal** — a pattern, filename, flag, marker — never a
  sentence (README § Brittleness policy).
- **Red-proof**: mutate the source it guards, watch it fail legibly,
  restore; record the mutation in the commit message.

## 4b. A replay case

A directory `replay/cases/<ID>/` with five files:

| file | what it is |
|---|---|
| `case.json` | `ledger` (ID · title), `prompt` (the command `claude -p` runs), `k` (default 5), `timeout` (seconds, default 900) |
| `seed.sh` | builds the sandbox repo — branches, files, config — as it stands when the command starts |
| `state.json` | the forge (issues, labels, PRs) the stub `gh` serves |
| `check.py` | scores one run: exit 0 pass, non-zero fail |
| `redproof.py` | **required** — proves `check.py` scores simulated runs correctly |

Start from the closest existing case: `replay/README.md` and the seeds
group into a few shapes (plain repo, spec branch, spec + defect, three
branches before integration, after integration). D4 is F4's shape with a
real verdict.

### seed.sh

- Begin with `bash "$(dirname "$0")/../../lib/seed-common.sh" "$1"` — the
  `CLAUDE.md` config, personas and first commit every case shares.
- Leave the repo on `main`; the runner pushes every branch to a local
  bare remote.
- Override config with `sed`, then **assert it took** (`grep -q …`): a
  silent no-op seeds the wrong experiment.
- A command in the config must be **complete** and work both as written
  and with a path appended; it must **fail on finding nothing**, never
  report a vacuous OK; its verdict must sit on the **last stdout line**,
  where `| tail -1` and `2>/dev/null` cannot remove it (D4, twice).
- `.gitignore` what running it leaves behind (`__pycache__/`), or the
  checker reads it as a change.

### state.json

- Consistent with the seed: every PR's `headRefName` is a branch the seed
  creates; the issue number matches the prompt.
- A call the stub has no route for invalidates the iteration (INVALID,
  never red). Extend the stub for a route the case needs; never let a
  real call fall through.

### check.py

- **Header**: `# <ID> · <title>`, the fixture in two lines, then every
  `# source:` — the ledger quote and the `file:line` of the prose that
  owns the behaviour, quoted. The runner refuses a checker with no
  `# source:`.
- `r, c = Run(), Checker()` — `Run` reads the artifacts (journal, forge
  state, transcript, the remote); `c.expect(source, description, probe)`
  records each check; `c.finish()` exits.
- **What to read, most reliable first**:
  1. *End state* — the forge's labels and journal, the git remote, the
     working repo (`WORK`). Tool-agnostic: holds however the agent got
     there.
  2. *Text the fixture itself prints* — a verdict line, a hook's deny
     message. Fixed format; guard against the agent trimming it.
  3. *The model's own prose* — only when nothing else can decide it, and
     documented as a lower bound (F4).
- **A vacuity guard** when passing could mean the session never got
  there: require evidence the tempting moment happened (D4: the verdict
  ran red).
- **Signals** — attempts the hook denied, shell writes — go to
  `RUN_DIR/attempts.json` and are reported, never scored.
- **Action, not mention**: a command that *names* `src/` to exclude it,
  or inside an `echo`, is not a read (D2, three rounds).

### redproof.py

Seeds real sandboxes with the case's own `seed.sh`, stages what an agent
could leave behind, and asserts `check.py`'s verdict — no model, no
tokens. `replay/run_redproofs.py` runs every one on each push, and fails
if a case has none. `cases/D4/redproof.py` is the template:

- **End states** — each correct road passes; each violation fails,
  including the ones that use a different tool (Edit, `sed -i`, a script,
  an edit inside a merge commit).
- **Run shapes** — for any check that reads tool output, the real output
  under the ways an agent trims it (`| tail -n`, `2>/dev/null`, `grep`),
  plus the negatives that must not read as the thing.
- **Mutation-test it**: disable each check in turn and watch specific
  red-proof cases go red. Record the result in the commit message.

## 5. Before the first recorded run

- [ ] `LEDGER.md` has the case and its ledger text.
- [ ] `check.py` quotes that text and cites the owning prose.
- [ ] `redproof.py` passes, and was mutation-tested.
- [ ] `python3 evals/replay/run_redproofs.py`, `python3 evals/lint/run_lint.py`
      and `python3 hooks/tests/run_tests.py` are green.
- [ ] The checker is committed in a **distinct commit before any recorded
      run** — the blindness commit; the history is the proof it was not
      written from observed output.
- [ ] `evals/README.md`'s case count is updated.

Then measure: `python3 evals/replay/run_replay.py --sut <sut> --k <k> <ID>`
— minutes and real tokens per iteration; the operator decides when.

## 6. Reading a red

An invalid run is not a red at all (no result event, a quota banner, an
unrouted forge call). For a real red, walk `README.md` § Autopsy taxonomy
before "the model violated the rule": instrument defect → fixture defect
→ rule ambiguity → model violation. Across the opus baseline the ratio
was roughly ten instrument/fixture findings to three model findings — the
instrument lies first.

## Instruments that lied — check yours against each

| case | what the instrument missed | the class |
|---|---|---|
| A1/A2 | a body passed by `--body-file` / `-F body=@` was journaled as a path, not its content | content read through an indirection |
| first sweep | a quota banner scored as FAIL — "0% compliance" was "the agent never ran" | an invalid run scored red |
| D2 | `grep -v '^src/'` and `':!src/**'` read as reads of `src/` | exclusion syntax is not use |
| D2 | `echo "… excluding src/"` read as a read; the fix then blanked `grep echo src/x` | mention in a string; command position |
| D2 | a tool call the hook denied scored as a breach | denied ≠ executed |
| C5 | config `test: true` was the shell builtin — a suite that could not fail | a vacuous fixture |
| E2 | "relocate it verbatim" meant *copy* to every run | the rule's prose was ambiguous |
| D4 | `acceptance_test` ended in `-s` with no directory; its first repair ran 0 tests and said OK | an incomplete or vacuous fixture command |
| D4 | `| tail -3` kept the summary, dropped the test's name | output trimmed by the agent |
| F6 | the ledger text said turns 1/3/5/10; the driver measured 1/3/5/8/12 | a citation stale against the code |
