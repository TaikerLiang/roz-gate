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

The issue that adds the case answers the six questions of
`charter.md § Rules for new eval work` first — its level, its product
question, why the oracle is trustworthy, what green proves and does not,
and both the **product decision** the result changes and the **stopping
rule**. A case that cannot name that decision is not added.

## 2. Write its ledger row first

The row is the case's own metadata; `LEDGER.md` is rendered from it by
`tools/ledger.py` (never edited by hand — `--check` goes red in CI and
pre-push while it is stale), and checkers copy the row, never the other
way round. A lint-only case carries the row as `META` in its file (§ 4a);
a replay case carries it in `case.json` (§ 4b) and its lint file, if it
has one, carries `META = {"id": …}` only — one source per row.

1. **Family** — the letter whose "what it guards" line fits (A–F; J and
   L are lint-only). A case that fits none is a question for the ledger's
   owner, not a new letter on your own.
2. **ID** — the family's next unused number. Numbers are never reused.
3. **Title** — the invariant, stated as what holds: *"The acceptance
   suite changes only on qa/<n>"*, not *"agent edits tests"*.
4. **Ledger text** — the expected outcome, then in parentheses why it
   matters. Every checker will quote it in `# source: ledger <ID> — "…"`.
5. Run `python3 tools/ledger.py` — the row appears on `LEDGER.md`, the
   counts in `README.md` move; commit both with the case.

## 3. Pick the tier

The tier picks the instrument; it does not set the level, which is the
issue's own answer to the charter. Take the first that can decide it:

| if the rule… | put it in | example |
|---|---|---|
| can be decided from one tool call as it happens | a **hook** (`../hooks/README.md`) | C4 → rule B, B4 → rule C, E2 → rule D, E7 → rule F, C18 → rule G, D7 → rule E (amended) |
| lives in prose and is provable by reading the source | **lint** | B1, C6, D1 |
| is about what a model actually does with the prose | **replay** | A1–A5, D4, F1–F5 |
| needs a judgment of meaning ("did it raise the thing that mattered") | **judgment** | P1…N10 (a stage on a frozen repo); `J-…` (one decision snapshot — `judgment/v1/README.md`) |

A rule that can be a hook should be one; a lint or replay case may still
measure it (D2 is all three).

## 4a. A lint case

One file, `lint/cases/<id>.py` (the ID lower-cased: `b1.py`, `c19.py` —
`tools/naming.py` wants snake_case), imported by `run_lint.py` in ID order;
the checks run at import against the shared checker in
`evals/lib/lintkit.py`:

```python
"""B1 · a compound tag evades the literal it contains        (defect: 1.12.0-)
Why the rule exists, in a few lines — the defect, the version, the issue.
"""

from lib.lintkit import fixture, must_match, must_not_match, src

META = {
    "id": "B1",
    "title": "a compound tag evades the literal it contains",
    "tier": "lint (defect 1.12.0-)",
    "ledger": None,  # lint-only rows show `—`; a case with a replay dir carries `id` only
}

UNV = r"(?i)\bunverified\b"
must_match("B1 pattern: compound (from Q4, unverified) found", UNV, fixture("b1_compound.md"))
must_not_match("B1 pattern: prose without the word NOT flagged", UNV, fixture("b1_negative.md"))
src("B1 conformance: Path B check carries the whole-word grep",
    "commands/next-stage.md", "grep -nwi unverified <specs_dir>/<n>/*.md")
```

- **Header**: the docstring's first line, `<ID> · <title>` and
  `(defect: <version>-)` or `(preventive)`; `META` is the ledger row
  (`tools/ledger.py` reads it with `ast`, never by importing). A pattern
  another case needs is imported from its owner (`from cases.b1 import
  UNV`), never copied — one canonical pattern, as before the split.
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
| `case.json` | `ledger` (ID · title), `tier` and `ledger_text` (the ledger row's last two columns — the quoted outcome and its parenthetical), `prompt` (the command `claude -p` runs), `k` (default 5), `timeout` (seconds, default 900); optionally `fixture` — a path or list of paths under `replay/` (fixture trees the seed copies in, the frame the checker imports), hashed into `case_fp` with the case's own files |
| `seed.sh` | builds the sandbox repo — branches, files, config — as it stands when the command starts |
| `state.json` | the forge (issues, labels, PRs) the stub `gh` serves |
| `check.py` | scores one run: exit 0 PASS, exit 3 INVALID (`replaylib.invalid(reason)` — the rule was never exercised; never red), any other exit FAIL (`replay/README.md` § Verdicts) |
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
  real call fall through. The same holds for a `--json` field the stub
  does not serve: every requested field is checked before anything is
  printed, one unserved field makes the whole call UNKNOWN, and the fix
  is to serve it from the fixture (`ISSUE_FIELDS` / `PR_FIELDS` /
  `REPO_FIELDS`) — never a default the fixture cannot state. A served
  field that this fixture cannot answer for this PR or issue (a merged PR
  with no `mergeCommit` and no single merge commit in the sandbox, a PR
  with no `author`, an issue with no `updatedAt`) is UNKNOWN too, and its
  note names the field: the fix is the fixture's — state the fact in
  `state.json`. A field gh itself rejects goes in `GH_REJECTS` only after
  a seat asked for it and real gh was seen to refuse it. URLs name
  the fixture's `repo` (default `acme/demo`). A free-form `--jq` is fine when `jq` is
  installed (CI's ubuntu runner has it; the stub falls back to it and
  journals `jq: system`); without it the expression is UNKNOWN.

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
- **INVALID is the checker's to say too**: when the iteration never
  reached the rule — the dispatch under test never ran, the seat's work
  was lost before it became observable — call `replaylib.invalid(reason)`
  (exit 3) instead of failing; a FAIL means the rule was exercised and
  broken. A do-nothing run is a FAIL, not an INVALID: the rule was
  reachable and nothing was done.
- **A case under a brief variant** (#199): the D10–D19 checkers build on
  `replay/qaframe.py` — the shared verdict (INVALID gate, the attempt
  rule, the blindness predicate, the outcome oracle that runs the pushed
  suite against the build and against a one-line mutant) — and add the
  case's mutant and its own expectations. Their seeds copy a fixture tree
  from `replay/fx/` through `lib/qa-fixture.sh`; `case.json` lists the
  tree, `fx/common`, `lib/qa-fixture.sh` and `qaframe.py` under `fixture`
  so the fingerprint follows every shared dependency of the verdict. A new QA-brief case is
  one `Frame(...)`, one `MUTANT`, and a `SHAPES` table for `Proof`.

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

- [ ] The case's metadata carries its ledger text and `python3
      tools/ledger.py --check` is green (`LEDGER.md` rendered, counts moved).
- [ ] `check.py` quotes that text and cites the owning prose.
- [ ] `redproof.py` passes, and was mutation-tested.
- [ ] `python3 evals/replay/run_redproofs.py`, `python3 evals/lint/run_lint.py`
      and `python3 hooks/tests/run_tests.py` are green.
- [ ] The checker is committed in a **distinct commit before any recorded
      run** — the blindness commit; the history is the proof it was not
      written from observed output.
- [ ] `.claude-plugin/plugin.json` is untouched — the version moves only in
      the release PR; the PR body carries `## Release note` instead
      (`docs/releasing.md`).

Then measure: `python3 evals/replay/run_replay.py --sut <sut> --k <k> <ID>`
— minutes and real tokens per iteration; the operator decides when. A
QA-brief case is measured once per variant (`--variant A`, `B`, `C`), on
the same fixture and SUT; the brief's hash is in every result
(`replay/README.md` § Variants).

Each run records the fingerprint of the case that scored it (`case_fp` in
`result.json`). Editing the checker, `case.json`, the seed or the state
after the baseline makes those runs **stale** in `report.json` — out of the
rate, never silently current — until the case is re-measured
(`evals/replay/README.md` § The case as scored).

A baseline that is to be cited is **recorded**: one batch in
`replay/baselines.json` — SUT, the exact plugin version or the range the
runs spanned, the date or the sweep's span, k, each case's valid and passed
counts, and where the numbers can be found — then `python3 tools/ledger.py`.
`README.md` § Recorded baselines renders from it; no page carries a
baseline figure by hand.

## 6. Reading a red

An invalid run is not a red at all (no result event, a quota banner, an
unrouted forge call). For a real red, walk `README.md` § Autopsy taxonomy
before "the model violated the rule": instrument defect → fixture defect
→ rule ambiguity → model violation. Across the opus baseline the ratio
was roughly ten instrument/fixture findings to three model findings — the
instrument lies first.

## 7. Shadow signals

A deterministic re-implementation of something the prose does — the branch
resolver (#135), later `roz-state` (#133) — runs **beside** the commands
before it replaces them. The comparison is a **signal**, never a verdict:
`Run.signal(...)` writes extra keys into the run's `attempts.json` and the
report sums the **counts** — an int value — in their own columns (D2's
`attempts_denied` pattern); any other value (a `*_detail` dict) is evidence
that stays in `result.json`, listed under `details`, and is never a column;
`c.expect` is not involved. `Run.shadow_branch([(kind, n), …], template,
acts)` is the first: the names the run **itself** bound — `Run.observed_bindings`
reads them from what it did, never from a fixture constant (`create`:
CR-OPEN's head, a push destination, a `roz-gate/wt/` worktree path,
`checkout -b`; `find`: CR-FIND's head) — against Lookup over the remote's
final heads; agreement is the observed set equal to the resolver's choice,
or both empty (an absent binding against a found branch is a mismatch).
C11's red-proof proves the signal discriminates. It writes
`shadow_branch_mismatch` (a count) and `shadow_branch_detail`. C10, C11,
C12, C20 and F9 carry it. One known difference until the commands switch:
the resolver also binds a head the forge deleted after its CR merged
(#272, `references/branch-names.md`), which the prose Lookup cannot see —
a mismatch there is that difference, not a defect.

`roz-state` (#133) has two. `Run.shadow_state(issues, template)` runs
`bin/roz-state` on the run's **final** forge state — in a fresh clone, with
a copy of the state, so not even the stub's journal line for a read reaches
the run's artifacts — and compares every fact with `replaylib.state_truth`,
the answer computed straight from the stub's `state.json` and the remote's
heads (it shares no code with the collector). It writes
`shadow_state_mismatch` (differing facts), `shadow_state_invalid` (an
output the contract rejects, or exit 3) and `shadow_state_detail`.
`Run.shadow_scan(issues, case_dir, template)` compares the scanner table's
**fact** columns — `track`, `status`, `cr` — with a snapshot of the state
the scanner **read**, not the run's final one: the pass acts after the
table, so a lock it takes later is no misread. The scan is patrol's first
step, so that state is the case's seeded one, rebuilt from `case_dir`; a
forge write journalled before the first listing breaks the premise and no
row is compared. It writes `shadow_scan_mismatch`, `shadow_scan_rows` and
`shadow_scan_detail`. It
never reads `waiting on`, `verdict`, `unheard` or `evidence`: those are the
scanner's interpretation, and a policy-level signal is `roz-check`'s
(#134). `redproof.py` § state proves both discriminate, and runs the
**seed sweep**: the collector against stub truth for every issue of every
case's seeded state — no model call. Its matrix is
`references/roz-state.md` § Shadow adoption; the sweep prints which seed
hits each cell and names the cells none does.

`roz-check` (#134) has one. `Run.shadow_check(issue, case_dir)` computes
`bin/roz-check integrate`'s verdict on the state the command **read** — the
case's seeded state, as `shadow_scan` does — and compares `may_start` with
whether the run took the lock (`status: processing` added to that issue):
`eligible` expects the lock; `ineligible` and `unknown` both expect none,
so a lock taken on an `unknown` verdict is a mismatch, never ignored. It
writes `shadow_check_mismatch`, `shadow_check_unknown` and
`shadow_check_detail` (the verdict, the failed and unknown codes, the
lock). The STOP reason is prose and is not compared. An integrate case
also **declares** what its seed must give — `case.json`'s `"check":
{"integrate": {"<issue>": {"verdict": …, "failed": […]}}}` — and
`redproof.py` § check runs the checker on every declared seed, with no
model call: a fixture that drifts from the preconditions it is meant to
satisfy fails there (D4's did — it had no fidelity record).

**Exit from shadow mode** — the commands switch to the resolver and the
prose Lookup is deleted — when all three hold (#239 § coverage + stability):

1. every cell of the scenario matrix has been observed in a recorded run:
   default template · custom template · foreign `{user}` · contiguous `{seq}`
   · gapped `{seq}` · `MULTIPLE_SAME_SEQ` · unreachable remote;
2. zero unexplained mismatches — every `shadow_branch_mismatch > 0` has an
   autopsy (collector defect, fixture defect, prose defect, or a genuinely
   ambiguous rule, each fixed or filed);
3. no mismatch across N consecutive recorded runs — N is set in the plan
   that performs the switch; it is a stability guard, not the definition of
   correctness.

Until then a mismatch is information, and the prose stays authoritative.
Each replacement's lifecycle (`identified → ready → shadow → authoritative
→ migrated`) is a row in `docs/prose-inventory.md` (#260); move the row in
the same PR that moves the rule.

## 8. Kernel rules

A semantic invariant that several executable files share has one owner,
which defines it, and consumers, which apply it by pointer (`docs/prose-inventory.md`
§ Kernel, #263; L14 holds the shape). A PR that changes a kernel rule's
**definition** names, in its body, every case listed in that rule's row.
Those consumers read the rule, so their earlier runs say nothing about the new
text. Re-running them is the maintainer's spend call; the PR names them
and does not start the runs. A consumer-only edit keeps the pointer and the
consumer's anchor in the same commit.

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
| C6 | the in-flight row's open-only guard read a merged CR as absent, so a cleared STOP never re-ran | a preventive guard outlived the rule it protected |
| C7 | its anchors required `git merge --no-edit <default_branch>` and `git diff <default_branch>...` byte-for-byte — the local ref — so the lint asserted the defect's own text (#90) | an anchor on a spelling protects every mistake inside it |
| judgment F-54 | headless `claude -p` killed background seats after 600 s; the session still ended on a result event and scored recall 0 from an empty surface | a session cut short, read as finished |
| D2 / rule E | a Maven layout's acceptance suite under `src/test/…` read as a read of the implementation; the fidelity dispatch could not read what it audits (#81) | a path is not provenance — the block says where the suite is |
| C5 | the post-integration re-run was green against the suite the fold had just outdated, and the cards were regenerated from it (#97) | a green against the wrong contract — ask what the suite derives from before taking its colour as evidence |
| C12 / C13 / F4 — integrate's precondition | "zero open fidelity threads" was true of an audit that found nothing and of an audit that never ran; a B5b that stopped before the reviewer posted left a thread-clean suite that integrated (#95) | an absence read as a pass — require the record of the act, not the absence of its findings |
| D2 / rule E | the brief itself sent the blind reviewer to the implementation CR's threads — code in the comments, reached through a forge call the hook saw as a listing (#96) | a read through the forge is a read — the instrument sees tool paths, not what comes back |
| every hook | four loaders opened `CLAUDE.md` only; a block kept in `CLAUDE.local.md` made the repo "not a roz-gate project" to the hooks while the commands ran it (#94) | a location is not presence — read every home the prose reads |
