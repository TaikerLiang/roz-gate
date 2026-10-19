# Hooks — the rules with teeth

Bundled `PreToolUse` hooks (`hooks.json`) run before a tool call in every
repo where the plugin is enabled. Exit 0 allows the call; **exit 2 blocks it
and feeds stderr to the model** — every deny message states the remedy, not
just the reason, because the agent is the reader. A repo with no Roz Gate
config block in `CLAUDE.md` or `CLAUDE.local.md` — in the checkout or in the
main worktree; `config_block.py` is the one reader every guard uses — is not
a roz-gate project: the guards allow everything there.

Each hook is two layers: a shell prefilter that costs nothing on the
overwhelming majority of calls (a grep of the raw input, one git call, one
stat), and a Python judge that runs only when the prefilter says so.

## Start here

What a hook sees and answers:

```
agent wants: gh issue edit 5 --add-label "status: ready-for-dev"
  → Claude Code pipes {"tool_name": "Bash", "tool_input": {"command": "…"}} to the hook's stdin
  → the hook exits 0 (run it) or 2 (block it; stderr goes back to the model)
```

The files:

| file | what it is |
|---|---|
| `hooks.json` | the registry: which event (`PreToolUse` only, today), which tools (matcher), which `.sh` runs |
| `guard-gate.sh` · `guard_gate.py` | Bash commands — rules A–D, F–H |
| `guard-blind.sh` · `guard_blind.py` | Bash / Read / Glob / Grep during an implementation-blind dispatch — the fidelity review, or QA's own since 2.0.0 — rule E |
| `guard-acceptance.sh` · `guard_acceptance.py` | Edit / Write / MultiEdit on a spec branch (`spec/<n>`, or whatever `branch_template` renders) — the acceptance rule |
| `config_block.py` | the config block's reader: `CLAUDE.md`, then `CLAUDE.local.md`, in the toplevel, then in the main checkout (`core.worktree` when set, else the common git dir's parent — a separate git dir without `core.worktree` is unreachable from a linked worktree: keep the block in the tracked `CLAUDE.md` there) — the first block wins, whole |
| `tests/test_guard_*.py` | the cases, one file per guard, one class per rule: synthetic hook input in, exit code and stderr asserted |
| `tests/test_fixtures.py` | every fixture carries the fields the guard reads |
| `tests/hooktest.py` | `HookTest`: runs a guard's `.sh`, builds throwaway repos, swaps fixtures |
| `tests/run_tests.py` | the runner: one PASS/FAIL line per case, then the tally |
| `tests/bin/gh`, `tests/bin/glab` | fake forge CLIs on `PATH` — rule A reads comments, tests never touch the network |
| `tests/fx/*.json` | what the fake CLIs return: "the holder asked for `summary`", "nobody did", … |
| `config-menu.tsx` | the `/roz-gate:config` mod (`hooks.json` `modules`) — see [The mod](#the-mod) |
| `tests/config-menu.test.ts` | the mod's cases, run by `claude plugin test` |

Should this be a hook? All three must be yes:

1. **Is there evidence?** A red replay case or a shipped defect — not a
   worry (see *How to add a rule*, step 1).
2. **Can the tool call alone decide it?** A hook sees one command or path
   plus local state (files, git, a marker). "Is this spec good" needs
   judgment — measure it in replay or judgment instead.
3. **Can you live with its wrong answers?** Pick the fail direction up
   front; fail toward the visible side (an over-block shows up as a deny,
   an under-block shows up as nothing).

Any "no" → a replay case, not a hook, and never prose alone.

| rule | file · matcher | predicate | deny says | fail direction |
|---|---|---|---|---|
| **A** intake-summary trigger | `guard-gate` · Bash | an `**[intake] · summary**` write is allowed only if the gate holder's latest comment requests `summary` (first or last line) or a gate label is present, and no summary was posted after that request | wait for the gate holder; do not retry or work around | forge API failure fails **closed**, with a message that says it is an API failure, not a protocol block |
| **B** human-only gate labels | `guard-gate` · Bash | `--add-label` (gh) / `issue update --label` (glab) naming `ready-for-spec` or `ready-for-dev`; a command shlex cannot tokenize is judged on the add flag's value alone — after `=`, whitespace or a `\`-newline continuation — never on a gate word elsewhere in it | the gate holder applies the label themselves | static, no API |
| **C** quote-open guard | `guard-gate` · Bash | a comment-shaped forge write whose body carries a roz-gate marker and opens with `>` (per shell segment; `--body-file` read back, heredoc parsed) | put the marker on line one | an unreadable marker-carrying `--body-file` fails **closed** |
| **D** open questions have one home | `guard-gate` · Bash | a `git commit` while any `<specs_dir>/*/technical-spec.md` — working tree **or** index — carries a heading matching `^#+ .*open questions` | move it to `spec.md`'s Open Questions, delete it here, `git add`, commit | index checked too: a fixed file never re-staged would commit the stale section |
| **E** a blind dispatch is blind | `guard-blind` · Bash, Read, Glob, Grep | while the marker exists — the fidelity review's, or since 2.0.0 the QA dispatch's (`seat=qa`; #140: `qa/<n>` is cut after the implementation landed, so the branch carries the code and the hook is the blindness) — a Read/Glob/Grep path under `src/`; in Bash, a git checkout/switch/diff/show/log/merge/restore/worktree on a `feat/` ref or on the ref the marker's `feat=` line names (the bound implementation branch, `references/branch-names.md`), or a read of `src/` outside `<acceptance_dir>` after blanking exclusion operands (`grep -v`, `:!`, `--exclude`, `-not -path`), echo/printf operands, comments, and operands under the suite (a suite under a `src/` segment — Maven's `src/test/…`, a multi-module `<module>/src/test/…` — is what the dispatch audits; so is the test port the marker's `read=` lines name — `technical-spec.md`'s `**Test port**` line, a file or directory under a `src/` segment, exempt exactly as the suite is (#125); `src` or `<module>/src` itself exempts nothing, a climb out of the suite or the port is not blanked; the suite resolves under **every worktree of the repo** — the dispatch's `qa/<n>` worktree while the hook fires from the main checkout (#107) — except a tree on a `feat/` ref or the marker's ref, the hook's own tree included); running the suite (`acceptance_test` names no `src/` operand) is never denied — QA may run what it may not read | what you need is on `qa/<n>`; a required read is a **finding**, not an action; the message names the dispatch (`fidelity` / `QA`) and its brief | a **stale marker keeps the rule ON** — over-blocking is visible, under-blocking is not; a grep whose *pattern* is `src/` (`grep 'src/' hooks/guard-blind.sh`) is denied — a pattern operand looks like a path operand, the visible direction; the rule cannot see a forge read of the implementation CR (a THREADS-LIST on it names no `src/`) — the brief's step zero and the dispatcher's contract-currency step close that, replay D6 proves it (#96) |
| **F** question options are bullets | `guard-gate` · Bash | a comment-shaped forge write (rule C's detection, `--body-file` read back, heredoc parsed) whose body carries a stand-alone question title — `**[<role>] · Q<k> · <label>**` or `**Q<n> · <label>**`, bold optional, a list item allowed — followed by fewer than two option bullets (`- (a) …`, any list marker) before the next title; the label is free text; a title whose line carries a ruling (`→ (a)`) or a resolution (`— resolved.`) opens no block, so answers, folds and summaries are out of scope by construction | one bullet per option: `- (a) …` / `- (b) … ← ✅ recommended` | static, no API; the recommended marker and the why stay prose — a block with its bullets passes whatever else it lacks (#109) |
| **G** a STOP comment names its resume move | `guard-gate` · Bash | a comment-shaped forge write (rule C's detection, `--body-file` read back, heredoc parsed) whose body carries the STOP title `**[<command>] · blocked**` alone on a line and whose must-read (the text before the first `<details`) does not end on a line opening `**To resume:**` | end the must-read with `**To resume:** clear status: blocked, apply status: <phase> — yourself, or tell the main agent; <where the answer goes>` — the command's STOP section names its phase and channel | static, no API; the title carries `**[`, so the prefilter already escalates it; a STOP comment posted without the title is not seen — the title is the protocol's fixed first line and lint C18 anchors it in every STOP section; a resume line hard-wrapped onto two source lines, or followed by more must-read prose, is denied — the visible direction, and the remedy is one line (#98; codex review, PR #114) |
| **H** a CR declares its contract deviations | `guard-gate` · Bash | a CR-OPEN (`gh pr create`, `glab mr create`; per shell segment) whose head's diff against its base (`--base`/`--head`, `--target-branch`/`--source-branch`; head absent → `HEAD`; base absent → gh's own default, the head branch's `branch.<head>.gh-merge-base` config, else `origin/HEAD`; a ref resolved as given, else as `origin/<ref>`) touches `<specs_dir>/*/technical-spec.md` and whose body (`--body`, `--body-file` read back, heredoc parsed, `--description`) has no line opening `## Contract deviations` | add the section — one bullet per changed clause, or `none` — and retry (next-stage B4) | one `git diff --name-only <base>...<head>`, no API; a diff that cannot be computed fails **closed** with a message that says the diff failed and names the refs to fetch, not the protocol; a body the guard cannot read fails closed; a repo without a config block is not a roz-gate project and is left alone (#140, 2.0.0) |
| **acceptance** | `guard-acceptance` · Edit, Write, MultiEdit | on a spec branch — `spec/*`, or HEAD matching your `branch_template` (the local file, `.claude/roz-gate.local.json`, here or in the main checkout — #165) rendered for the spec kind — a write under `<acceptance_dir>` | make the change on `qa/<n>`, merge it in | branch-and-path only; no exemption list |

## The dispatch marker (rule E)

Subagents share the session; a hook cannot tell *which* dispatch it is
inside (the fidelity review and the stage-(5) code review are the same
`reviewer` seat; since 2.0.0 the QA seat's own dispatch is blind too —
#140). So the **dispatching command** says so:

```sh
mkdir -p "$(git rev-parse --git-common-dir)/roz-gate" && printf 'issue=<n>\nfeat=<feat-branch>\nread=<path>\nseat=<seat>\n' > "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"
# one read=<path> line per path technical-spec.md's `**Test port**` line names; none for `none`
# seat=qa for the QA dispatch (next-stage B2.4), seat=reviewer for the fidelity dispatch (B2.7)
# … Task/Agent dispatch …
rm -f "$(git rev-parse --git-common-dir)/roz-gate/fidelity-dispatch"
```

Written immediately before the dispatch, removed immediately after it
returns (next-stage B2.4 and B2.7, patrol's address-review steps 2 and 3,
its fidelity-audit action). Its `seat=` line (2.0.0) names the dispatch
the marker guards — `qa` or `reviewer` — so the deny message names the
brief the reader is under; the predicate is the same either way, and a
marker without the line is a fidelity dispatch, as every 1.x marker was.
The file keeps its 1.16.0 name. Its
`feat=` line is the bound implementation branch — under a
`branch_template` that is not a `feat/` ref, and the hook denies a git
action on that exact name as it does on `feat/`; a marker without the line
(the 1.16–1.28 shape) enforces the `feat/` literal alone. Its `read=<path>`
lines (1.40.0, #125) name the test port `technical-spec.md` declares; a
read under one is exempt as a read under the suite is. It lives
under the **common** git dir — `guard_blind.py` resolves it with
`git rev-parse --git-common-dir` — which the checkout and every linked
worktree share, so a dispatch running in the `qa/<n>` worktree
(commands work in worktrees, issue #37) is governed by it whatever its
cwd; a per-worktree `--git-dir` would be that worktree's private
`worktrees/<name>` dir, where a marker written from the checkout is
invisible and the rule silently off. One marker per checkout means a
dispatch in one session also blinds another session on the same
checkout: over-blocking, the fail direction this rule chooses. Never
tracked, never in `git status`.
The prefilter is one git call plus one stat. **Stale marker = rule still
ON**: if a dispatch crashed and a later, non-blind read is denied, the deny
message names the file to remove. `agent_type` from the hook input is
reported in the message but never relied on.

## This repo's own gates (not plugin hooks)

`.githooks/` guards the plugin repository itself — **only after
`tools/dev-setup.sh` (= `git config core.hooksPath .githooks`) has been
run once in the clone**; a fresh clone's gates are silently inert until
then, and CI's lint tier is the backstop. Two gates: **pre-commit** rejects a staged file whose name breaks the naming
convention (Python `snake_case`, shell `kebab-case`, markdown
lowercase-kebab outside the ecosystem caps and fixture data — one
predicate, `tools/naming.py`, which CI re-runs over the tree so a
`--no-verify` commit is caught one step later) and runs ruff on the staged
`.py` files — skipped when `uv` is absent, CI's ruff step is the backstop;
`tools/naming.py` stays the file-NAME check while ruff is code; **pre-push** runs the hook unit
tests, the lint tier, the ledger check and the replay red-proofs (the
version moves only in the release PR — `docs/releasing.md`).

## Running the tests

```sh
python3 hooks/tests/run_tests.py                # one PASS/FAIL line per case — the hooks and bin/roz-config
python3 -m unittest discover -s hooks/tests     # same tests, unittest's own output
claude plugin validate --strict .               # the manifest and the mod, as the engine reads them
claude plugin test .                            # the mod's cases (hooks/tests/config-menu.test.ts)
```

Synthetic `PreToolUse` JSON is piped into each hook's `.sh` shim — the
real entry point, so a prefilter that never escalates fails here too; the
exit code and a stderr substring are asserted. Stdlib `unittest`, Python
3.9-compatible: it runs on the same plain `python3` as the hooks. The release gate (`.githooks/pre-push`, CI)
runs this suite and the eval ledger's lint tier on every push.

A rule is a class; a stateless rule is two tables — denied cases with
the stderr substring the deny must carry, and allowed ones:

```python
class RuleB_GateLabelsAreHumanOnly(HookTest):
    guard = "guard-gate"

    DENIED = [
        ("gate label add blocked (gh)",
         'gh issue edit 5 --add-label "status: ready-for-spec"', "gate labels"),
    ]
    ALLOWED = [
        ("gh list filter allowed",
         'gh issue list --label "status: ready-for-spec" --json number'),
    ]

    def test_denied(self):
        for name, cmd, says in self.DENIED:
            with self.case(name):
                self.assertDenied(self.bash(cmd), says)
```

Every check sits inside `with self.case(name):` — that is what the runner
prints and counts. A rule that needs state walks it in order inside one
test method (rule D's staged / unstaged steps, rule E's marker on / off).

Every rule needs both kinds: the **live shape** that motivated it (denied)
and its **legitimate neighbours** (allowed) — look-alikes, list filters,
a mention inside an `echo`. Walk the cautionary list below for each.
Forge-reading rules add a fixture under `tests/fx/` and wrap the case in
`with self.fixture(gh="gh_<name>.json"):`; git-state rules build one with
`self.new_repo(files, commit=..., branch=...)`.

Fixtures are not a format of ours — each is the real output of the one
forge call the guard makes, trimmed to what the case needs. Capture one
from a live issue rather than writing it by hand:

| prefix | captured from |
|---|---|
| `gh_` | `gh issue view <n> --json assignees,author,labels,comments` |
| `glab_issue_` | `glab issue view <n> --output json` |
| `glab_notes_` | `glab api projects/:id/issues/<n>/notes?per_page=100` |

`tests/test_fixtures.py` checks every fixture carries the fields
`guard_gate.py` reads, typed as it reads them: the guard reads with
`.get()` defaults, so a misnamed field (`login` where GitLab says
`username`) would be silently empty and the case would test something
other than its name. Provenance is not checkable — the shape is. A guard
that reads a new field extends that check in the same commit.

## How to add a rule

1. **Start from a measurement or a shipped defect**, never from a worry.
   Rules C, D and E each came from a replay case that was red (B4's
   runaway, E2 at 0/5, D2 at 4/5). A rule either has teeth or is measured;
   prose alone is a hope.
2. **One predicate, shared.** If an eval checker asserts the same thing
   (D2's regexes, E2's heading), the hook carries the checker's literal
   byte for byte, and a lint conformance case holds the two together —
   the checker cannot be honest while the hook lies, or the reverse.
3. **The deny message is the remedy.** Name the file, the action, the
   place the thing belongs, and — for rule E — the escape hatch for a
   stale marker.
4. **Red-proof both directions before it counts**: the live shape that
   motivated the rule must be denied; the legitimate neighbours must pass;
   record both in the commit message. Then the mutation test: remove the
   rule and watch the test go red.
5. **Bump the plugin version** — hook behaviour is behaviour.

Where the code goes: a rule on Bash commands joins `guard-gate`; a new
tool family gets its own pair and a `hooks.json` entry. Widen the `.sh`
prefilter's grep so the call reaches Python at all — a rule the prefilter
never escalates is a rule that never runs — then add the predicate to the
`.py` side: print the remedy to stderr and `sys.exit(2)`. Add the rule's
row to the table above.

## Instrument blindness — the cautionary list

Five times the instrument (hook or checker) was blind to a form the agent
actually used. Audit every new predicate for the class, not the instance:

- **Body by reference** (1.14.0 review, then the replay stub): a comment
  body passed as `--body-file`, `-F body=@file` or `--input` carries the
  marker *outside the command text*. The hook reads the file back and
  parses heredocs; the stub journals the content, never the path.
- **Exclusion syntax** (D2, PR #7): `grep -v '^src/'` and `':!src/**'`
  name `src/` in order to *not* read it. Blank the operand of the
  exclusion operator before the read match.
- **Mention in a string** (D2, 1.16.1 → 1.16.2): `echo "… excluding src/"`
  is not a read — but the first fix blanked `echo` *anywhere* in a
  segment, so `grep echo src/app.txt` passed. A word is a command only in
  command position. The under-block was silent; the over-block had been
  visible. When in doubt, fail toward the visible direction.
- **Block by location** (#94): every loader opened `CLAUDE.md`. A project
  that kept its block in `CLAUDE.local.md` was "not a roz-gate project" to
  four rules — acceptance and D off, A in user mode, E without its suite
  exemption — while the commands, reading the block from Claude Code's
  context where both files land, ran the loop. Read every home the prose
  reads, through one reader (`config_block.py`), and look where the prose
  looks: the main checkout, not only the worktree the hook fired in.
- **Tree by cwd** (#107): rule E's suite exemption resolved the path
  against the toplevel the hook fired in. The dispatch's suite sits in the
  `qa/<n>` worktree (B5b) while the Read tool's paths are absolute and a
  sub-agent's Bash cwd is the session's — the same file, allowed from one
  cwd and denied from another, and the audit that #95 made mandatory could
  not read what it audits. A path belongs to the tree it is in, not the
  tree the hook runs from: resolve against every worktree of the repo.

## The mod

`hooks.json` also names one Claude Code mod (2.1.287 or later),
`config-menu.tsx`: it answers `/roz-gate:config` itself, so a config change
costs no model turn (#164). With arguments it runs `bin/roz-config <key>
<rest>` — the rest as one argument, the tool splits list keys on commas;
without, it opens a pane with a `Select` for the key and an `Input` for the
value; where nothing draws (`claude -p`) it prints the values, and on a
surface with no fields (mobile) the pane lists them. It runs nothing but
`python3 bin/roz-config`, through `$.process.run` with an argument list —
no shell — and never writes a file, reaches the network or a model, or
hooks a tool call (lint L8). Where mods do not load — an older Claude Code,
`--safe-mode`, `disableAllHooks` — `commands/config.md` runs as the
fallback. A Claude Code that predates mods ignores the `modules` key and
still loads the guards (checked on 2.1.200 and 2.1.286).

