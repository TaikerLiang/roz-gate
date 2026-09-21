# Hooks — the rules with teeth

Bundled `PreToolUse` hooks (`hooks.json`) run before a tool call in every
repo where the plugin is enabled. Exit 0 allows the call; **exit 2 blocks it
and feeds stderr to the model** — every deny message states the remedy, not
just the reason, because the agent is the reader. A repo with no Roz Gate
config block in `CLAUDE.md` is not a roz-gate project: the guards allow
everything there.

Each hook is two layers: a shell prefilter that costs nothing on the
overwhelming majority of calls (a grep of the raw input, one git call, one
stat), and a Python judge that runs only when the prefilter says so.

| rule | file · matcher | predicate | deny says | fail direction |
|---|---|---|---|---|
| **A** intake-summary trigger | `guard-gate` · Bash | an `**[intake] · summary**` write is allowed only if the gate holder's latest comment requests `summary` (first or last line) or a gate label is present, and no summary was posted after that request | wait for the gate holder; do not retry or work around | forge API failure fails **closed**, with a message that says it is an API failure, not a protocol block |
| **B** human-only gate labels | `guard-gate` · Bash | `--add-label` (gh) / `issue update --label` (glab) naming `ready-for-spec` or `ready-for-dev` | the gate holder applies the label themselves | static, no API |
| **C** quote-open guard | `guard-gate` · Bash | a comment-shaped forge write whose body carries a roz-gate marker and opens with `>` (per shell segment; `--body-file` read back, heredoc parsed) | put the marker on line one | an unreadable marker-carrying `--body-file` fails **closed** |
| **D** open questions have one home | `guard-gate` · Bash | a `git commit` while any `<specs_dir>/*/technical-spec.md` — working tree **or** index — carries a heading matching `^#+ .*open questions` | move it to `spec.md`'s Open Questions, delete it here, `git add`, commit | index checked too: a fixed file never re-staged would commit the stale section |
| **E** fidelity dispatch is blind | `guard-blind` · Bash, Read, Glob, Grep | while the marker exists: a Read/Glob/Grep path under `src/`; in Bash, a git checkout/switch/diff/show/log/merge/restore/worktree on a `feat/` ref, or a read of `src/` after blanking exclusion operands (`grep -v`, `:!`, `--exclude`, `-not -path`) and echo/printf operands and comments | what you need is on `qa/<n>`; a required read is a **finding**, not an action | a **stale marker keeps the rule ON** — over-blocking is visible, under-blocking is not |
| **acceptance** | `guard-acceptance` · Edit, Write, MultiEdit | on a `spec/<n>` branch, a write under `<acceptance_dir>` | make the change on `qa/<n>`, merge it in | branch-and-path only; no exemption list |

## The fidelity-dispatch marker (rule E)

Subagents share the session; a hook cannot tell *which* dispatch it is
inside (the fidelity review and the stage-(5) code review are the same
`reviewer` seat). So the **dispatching command** says so:

```sh
mkdir -p "$(git rev-parse --git-dir)/roz-gate" && printf 'issue=<n>\n' > "$(git rev-parse --git-dir)/roz-gate/fidelity-dispatch"
# … Task/Agent dispatch …
rm -f "$(git rev-parse --git-dir)/roz-gate/fidelity-dispatch"
```

Written immediately before the dispatch, removed immediately after it
returns (next-stage B5b, patrol's address-review steps 2 and 3). It lives
under the git dir — per worktree, never tracked, never in `git status`.
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
tests and the lint tier and refuses a behaviour change without a version
bump.

## Running the tests

```sh
bash hooks/tests/run-tests.sh     # 99 cases; forge CLIs stubbed via PATH
```

Synthetic `PreToolUse` JSON is piped into each hook; the exit code and a
stderr substring are asserted. The release gate (`.githooks/pre-push`, CI)
runs this suite and the eval ledger's lint tier on every push.

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

## Instrument blindness — the cautionary list

Three times the instrument (hook or checker) was blind to a form the agent
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
