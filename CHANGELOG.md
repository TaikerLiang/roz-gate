# Changelog

Generated from the GitHub releases (`gh release list`, `gh release view <tag>`), newest first, one entry per tag with its title and body verbatim. **The release note is canonical**; this file is a convenience copy — regenerate it, never edit it by hand. It exists because "why does this rule exist" is answered by the release that introduced it better than by any other document here.

## v1.29.1 — rule E no longer denies the fidelity dispatch's own suite under src/ — 2026-10-07

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.29.1>

**Behavior:** rule E no longer denies the fidelity dispatch's reads of its own acceptance suite when `<acceptance_dir>` sits under `src/` (Maven/Gradle layouts). Everything else under `src/` stays denied.

### Behavior
- **Rule E and the suite** (#81): a path under the block's `acceptance_dir` is never a read of `src/` — Bash operands blanked before the match, Read/Glob/Grep paths resolved against the toplevel. Only a suite strictly inside `src/` is exempt; `src` itself exempts nothing; a climb out of the suite (`…/acceptance/../../main/…`) and another tree's `src/test/…` stay reads. The fidelity brief, next-stage B5b, patrol step 2 and workflow.md say "outside `<acceptance_dir>`".

### Evals
- **Lint D2** amended: probes through the suite parameter; the four regexes stay byte-identical; conformance anchors in six prose surfaces. Mutation: blanking disabled → the suite probe red → restored → green. Ledger D2 row amended; CONTRIBUTING's instruments-that-lied table gains "a path is not provenance".

### Hooks
- **guard-blind**: `load_acceptance_dir` (block-scoped), `suite_under_src`, `suite_operand_re` + `suite_blanker`, `under_suite`, `tool_reads_src`; the deny message names the readable suite. Tests 156 → 194 (`RuleE_SuiteUnderSrc`: a Maven-layout repo, every tool and spelling, the near-miss sibling, the climb out, the config edges; after the Codex round: a suite operand ends at a shell control character, and every operand is resolved by `realpath` — a symlink inside the suite that points out is denied).

### Docs
- README and index rule E rows; `hooks/README.md` rule E predicate and the test-count line; quiz #21 background.

### Checks
Hook tests 194/194 · lint 355/355 · red-proofs 13/13 · ruff clean · naming clean · `judgment --check` frozen — on `2ccab62`.

## v1.28.0 — helper_model: one per-clone key for the two mechanical sub-agents; patrol_model retired — 2026-10-07

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.28.0>

**Behavior:** `patrol_model` is retired; `helper_model` is the fourth per-clone key (`/roz-gate:config helper_model <model id>`), and it governs the two mechanical sub-agents — patrol's scanner and the commit sub-agent in every command. Seats run on the runtime default. A block that still carries `patrol_model` is seeded once into the local file by `bin/roz-config`.

### Behavior
- **`helper_model`** (#66): set through `/roz-gate:config` (menu item 4) or `roz-config helper_model <id>`; absent → the runtime's default, shown as `(default: runtime)` and `""` in `--json`. Patrol dispatches its scanner on it; `next-stage` A4/B4/C5, `spec-answers` §6, `review-answers` §6 and patrol's address-review dispatch the commit sub-agent on it (`references/commit-brief.md` says so). The key never changes the model a command itself runs on.
- **`patrol_model` retired**: it governed patrol's seats; seats are no longer model-configurable. The block line is gone from README and the onboarding builder (the template never carried it); `roz-config` migrates an existing block line to `helper_model` once and names the rename on stderr.

### Evals
- **L2 amended** (lint 268 → 283 with L3): the tool's KEYS tuple is the four keys; patrol's Model paragraph names `helper_model`, the scanner, the commit sub-agent and `roz-config` and says seats run on the runtime default; §1 dispatches the scanner on it; README's block has no `patrol_model` line and the per-clone section says four; `patrol_model` survives nowhere under `README.md commands references templates docs`; the onboarding builder offers `helper_model`; the tool still reads `"patrol_model"` (the migration). **L3 amended**: each of the six commit windows and the brief name `helper_model`. Three mutations, each one check red and back, recorded in the feat commit's message.

### Hooks
- **`test_roz_config.py`** (hook suite 128 → 134): `helper_model` set/show/`--json`/remove, one-value refusal, migration of a block's `patrol_model` line — into a fresh file and into an existing one, once, with a tombstone on removal (codex review); the unknown-key example is now `model`.

### Docs
- README config block (line removed) and per-clone section (fourth line, "Four keys"), command table row, onboarding builder (`helper_model` moved to "Yours — per clone", hint rewritten, header "four keys"), `hooks/README.md` test count, LEDGER L2.

### Checks
Hook tests 134/134 · lint 283/283 · red-proofs 10/10

## v1.29.0 — branch names from branch_template: bound once per command, found by pattern, never spelled — 2026-10-07

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.29.0>

**Behavior:** none until `branch_template` is set — the default reproduces today's names. A repo that sets it gets templated branches, `type:` labels from a re-run `init`, and (with `{seq}`) sequence-numbered re-entry after a closed spec CR.

### Behavior
- **`references/branch-names.md`**: branch names come from the block's `branch_template` (`{kind}`, `{type}`, `{user}`, `{n}`, `{seq}`; default `{kind}/{n}`). `{type}` is `spec` / `test` / the issue's `type:` label (default `feat`); `{user}` is the local key `branch_user` or WHOAMI; `{seq}` is the attempt — a re-spec cuts `…/2` instead of stopping, and the agent still never deletes or force-pushes. A template without `{seq}` keeps C10's STOP verbatim. Every command binds its four names once (`<spec-branch>` …) and finds an existing branch on the remote by pattern — another person's `{user}` and an attempt's `{seq}` are not computable. Issue #75: target repos enforce `{type}/{user}/{ticket}/{seq}`.
- **`init`** creates `type: feat` / `type: fix` / `type: chore` (informational, never a gate; no command applies or validates one) and documents `branch_template`.

### Evals
- **L4** (lint): names bound, never spelled — no literal `spec/<n>` outside `branch-names.md`; the readers bind through it; A2/C2 carry the `{seq}` route; the marker line; the type labels; WHOAMI in both adapters; both hooks read the template.
- **F10** (replay): a branch is cut by the configured template — `spec/paul/5/1` from the configured base, not `spec/5`, not the leaked `fix/paul/5/1`. Red-proof, 10 shapes.
- **C11** (replay): a template with `{seq}` re-enters by the next sequence — `spec/paul/5/2` cut, `spec/paul/5/1` untouched, no delete remedy. Red-proof, 10 shapes.
- **D5** (replay): the fidelity dispatch is blind under a templated implementation branch — the marker carries `feat=fix/paul/5/1`; the predicate is the hook's own. Red-proof, 13 shapes.
- **L2**: five local keys; C7/C9/C10 anchors follow the bound names.

### Hooks
- **acceptance guard**: a spec branch is `spec/*`, or HEAD matching the template rendered for the spec kind; the zero-cost prefilter path is unchanged for repos without a template.
- **rule E**: the marker's `feat=<branch>` line is denied by exact name alongside the `feat/` literal; the D2 regexes stay byte-identical.

### Tooling
- **`bin/roz-config`**: fifth key `branch_user` (default: the forge login, resolved by the command, never by the tool). **Adapters**: `WHOAMI` — `gh api user --jq .login` / `glab api user --jq .username`.

### Docs
- **README** "Branch names", the `type:` label row, the rule table; **onboarding** builder (`branch_template`, `branch_user`) and the re-entry stop shape; **index** label card; **quiz** #51; **hooks/README** rule rows and the marker snippet; **workflow.md** "The branch names".

### Checks
Hook tests 156/156 · lint 345/345 · red-proofs 13/13 (harness + 11 cases, F10/C11/D5 new) · ruff clean · naming clean · `judgment --check` frozen — on `b07096b`. L4 mutation: a `spec/<n>` literal reintroduced in next-stage.md → red (L4 + C7's anchor) → restored → green. Codex round (PR #82): the scanner is handed the remote's heads for Lookup; the acceptance hook reads `branch_template` from the config block only; quiz #51 says `{n}`.

## v1.27.0 — every commit goes through a commit sub-agent; the scanner's table carries the gate holder — 2026-10-05

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.27.0>

**Behavior:** every commit a command makes is now made by a **commit sub-agent** briefed by `references/commit-brief.md`; the target repo's pre-commit output stays out of the main agent's context. Push, CR, labels and the report stay with the main agent. The scanner's table also carries the gate holder, so patrol never lists issues after the table.

### Behavior
- **The commit brief** (#67, #70): `references/commit-brief.md` is the only home of the commit rules — stage → commit in the worktree the main agent names, no push / rebase / amend / forge op / dispatch; a hook failure on a committed file is fixed and retried once, unrelated drift is `--no-verify` with the reason recorded, anything else is `failed:` and stops; it returns one table `branch · sha · hook` (`clean` / `no-verify: <reason>` / `failed: <≤20 lines>`). `next-stage` A4/B4/C5, `spec-answers` §6, `review-answers` §6 and `patrol`'s address-review step dispatch it and push from the returned `sha`; the per-step `--no-verify` sentences are gone. Seats still never touch git. `integrate`'s merge commits stay with the main agent — conflict resolution is its judgment, and the brief is forbidden to merge.
- **Scanner table carries the gate holder** (#68, from the v1.26.0 sweep's F9 run-3): the brief gains a `holder` column (assignees, else author, humans only); patrol's §2 list and the intake action read it from the row, so the main agent has no reason left to list issues after the table.

### Evals
- **Lint L3** (231 → 268): the brief carries every rule and literal; each of the six commit points names it and pushes from the returned `sha`; no command carries a `--no-verify` rule of its own or tells the main agent to run `git commit`; `workflow.md` and README name the sub-agent. Red-proofed by mutation, three ways, each one check red and back (recorded in the checker's commit message).
- **Lint A8** holds the `holder` column in the brief and patrol's reads of it; **F9**'s red-proof table and checker carry the column.
- **F9 checker** (#65, the v1.26.0 sweep's findings): the scanner's GraphQL THREADS-LIST is a read, not a write; a per-issue `gh pr list --head spec/<n>` after the table is one issue's CR-FIND, not a re-scan; "untouched" means labels as seeded, no comment, no branch, no CR. Harness red-proof 21 → 30, F9 red-proof 7 → 9. Rescored: run-1 PASS, run-2 a genuine FAIL.
- **v1.26.0 opus baseline recorded** (#69): seven cases at k=5 on 2026-10-05 in `evals/README.md`'s baseline section.

### Tooling
- **Forge stub** (#65): two read-only routes — `gh api repos/o/r/git/ref/heads/<branch>` (answered from `git ls-remote --heads origin`, absent → 404) and `gh api repos/o/r/contents/<path>?ref=<branch>` (served from the sandbox's objects, absent → 404); writes and absent ids stay UNKNOWN.

### Docs
- README § Your checkout is never touched and its evidence paragraph, `workflow.md` workspace paragraph, LEDGER L3, evals README lint count 14 → 15 and the baseline section.

### Checks
Hook tests 130/130 · lint 268/268 · red-proofs 10/10

## v1.26.0 — three routes when the spec stage shows a gap; amendments; agents never delete or force-push a branch — 2026-10-04

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.26.0>

**Behavior:** when the spec stage shows your issue missed something, the size of the miss picks the route — amend in place (a thread you open on the spec CR is folded in as an amendment), re-spec (close the CR, amend the issue, delete the old `spec/<n>` yourself, re-apply `ready-for-spec`), or back to the inbox. `next-stage` stops on a leftover branch and hands you the exact delete command. **An agent never deletes or force-pushes a remote branch.**

### Behavior
- **Three routes at (2a)** (#62, #63): `workflow.md` states them by how much changed; the inbox return applies from (2a) as from (7); the invariant that every remote write a command makes is additive.
- **Amendments** (`spec-answers`): a thread whose first comment is the human's — no agent question, no `[role]` tag — is an amendment request: role from the document the thread sits on (THREADS-LIST now returns `path`/`line` on GitHub, the note position on GitLab; no path = a CR-level comment = product's), folded into the owning document, recorded as a resolved `A<k>` item with `(from A<k>)` provenance, replied `✅ [<role>] amended — …`, resolved. Such a thread used to be skipped while patrol classified it actionable — "no new answers" every pass.
- **Re-spec** (`next-stage` A2/C2): `git ls-remote --exit-code --heads origin <b>/<n>` before the cut; exists + CR open → illegal state, STOP; exists + CR closed or absent → STOP with the remedy verbatim — `git push origin --delete <b>/<n>` — *the human runs this* — and the closed CR cited. Option D ruled over agent force-push, agent delete-then-recut, and per-attempt branch names.
- **`-B` cuts** (codex review): every `worktree add` (spec, fast, feat, qa) uses `-B`, so the previous attempt's local ref — which survives its removed worktree — is reset instead of refusing the fresh cut; `-B` still refuses when the branch is checked out elsewhere, which is the mutex.

### Evals
- **Lint C10** (204 → 227): both branch steps carry the check, both STOPs and the remedy; the remedy line is addressed to the human; no `push --force` / `--force-with-lease` / `branch -D` in `commands/` or `references/`; the four `-B` cuts and no `-b`; the adapters' location fields and the stub's projection; workflow and spec-answers conformance.
- **Replay E6** (red-proof 7/7): a human-opened thread on `spec.md` → `spec.md` changed on the remote, `✅ amended` reply, resolved, lock released.
- **Replay C10** (red-proof 7/7): `spec/5` exists with CR #101 closed → blocked alone, the STOP comment carries the delete command and cites #101, no CR, the remote's refs byte-identical — never force-pushed, never deleted. The red-proof caught the first checker reading the cite from the human's own comment.
- Neither has a SUT baseline yet.

### Docs
- README (stage table (2a), the change-order paragraph), the guide's (2a) card and wizard, onboarding step 5 and a new stop card "spec/<n> already exists", LEDGER C10/E6.

### Checks
Hook tests 130/130 · lint 227/227 · red-proofs 10/10

## v1.25.0 — patrol's scan is a read-only sub-agent; the main agent acts from its table — 2026-10-04

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.25.0>

**Behavior:** patrol's scan is now one **read-only scanner sub-agent** that classifies every open issue into a table; the main agent decides and acts from that table alone and never re-reads the forge to confirm a row. The forge reads stay out of the main agent's context, so a scheduled patrol stays stable over long sessions.

### Behavior
- **The scanner** (#59, #60): `references/patrol-scan.md` is the scanner's brief and the **only** home of the scan and classification rules (patrol's old §1–§2, moved verbatim) plus the read-only rule — no LABEL-*, ISSUE-COMMENT, ISSUE-CLOSE, dispatch or git — and the table contract: `issue · track · status · cr · unheard · verdict · evidence`, a fixed verdict vocabulary, the inbox-filter line. `patrol.md` dispatches it once per pass with the brief, the forge adapter path and `roz-config`'s three keys, then acts on the `verdict` column: one in-loop action, every close-out, every intake batch, the report. The scanner dispatches nothing (depth stays 1).
- **Hand-off** (codex review): a review-clean fast CR is the verdict `hand-off: in-user-review`; the main agent applies the label — a status report, exempt from the one-issue rule.

### Evals
- **Lint A8** (176 → 204): `patrol.md` carries no classification table and runs no scan op; the brief carries the table, the inbox filter, the read-only rule, every column and verdict literal, the hand-off; patrol dispatches with the brief, says never re-read, applies the hand-off. B3/C6/C8/L2 readers of the old §1–§2 read the brief.
- **F1 amended** ("a quiet loop stays quiet"): exactly one dispatch — the scanner, prompt naming its brief — and zero writes.
- **Replay F9** (red-proof 7/7, no baseline yet): #5 in-user-review with an unheard comment, #6 fast + ready-for-dev, #7 raw inbox idea → the scanner's result has rows with the right verdicts; the pass acts on #5, locks nothing else, posts #7's batch; no forge write under the scanner's parent id; no issue/CR listing by the main agent after the table.

### Docs
- README patrol row, `workflow.md` invocation policy, onboarding step 5, the guide's wizard note, LEDGER A8/F9/F1.

### Checks
Hook tests 130/130 · lint 204/204 · red-proofs 8/8

## v1.24.0 — your three loop keys, per clone: roz-config and its /roz-gate:config menu — 2026-10-04

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.24.0>

**Behavior:** three loop keys — `default_branch`, `inbox_label`, `inbox_assignee` — are now yours, per person, per clone, never committed, set from a menu with `/roz-gate:config`; the write is a stdlib Python tool's, never the model's. They leave the `CLAUDE.md` block. Version 1.23.0 is #56's intermediate manifest and carries no tag.

### Behavior
- **`bin/roz-config`** (#55, #56): `roz-config` prints the three effective values with `(default)` marked; `--json` is what commands read; `roz-config default_branch release/20261006`, `roz-config inbox_label discuss "good first issue"` (lists: any of), a key alone removes the override. Stored in `.claude/roz-gate.local.json`, added to `.git/info/exclude` on first write. Defaults: the remote's HEAD branch (`main` when it has none), empty lists. Claude Code's `userConfig` / `/config` panel is user-level only — one value per machine — and was rejected for repo-level keys.
- **Upgrade** (codex review): the first run that finds no local file seeds it once from the block's `default_branch` / `inbox_*` lines (comma-separated → lists), says so on stderr, and the block is ignored from then on — a configured release base or inbox filter survives the upgrade.
- **`/roz-gate:config`** (#57) is the menu for the tool: it injects the current values into the prompt, asks which key and what value with the runtime's option picker, splits inbox values on commas (a forge label may contain spaces — codex review) and runs the tool with each value quoted; with arguments it skips the menu. No prose logic: no validation, no file edit, no forge lookup.
- **Commands** (`patrol`, `next-stage`, `integrate`, `spec-answers`, `review-answers`) read the three through `bin/roz-config --json`; patrol's filter is any-of within a key, both keys must hold, empty = no filter. `init` no longer writes `default_branch`; the template drops it. `bin` joins the pre-push behavior paths.

### Evals
- **Runtime suite** 118 → 130: `hooks/tests/test_roz_config.py` — defaults with and without `origin/HEAD`, set/replace/remove, lists, one value for `default_branch`, unknown key, excluded once and invisible to git, subdirectory and linked-worktree resolution, outside a repo, corrupt file never overwritten, the one-time migration and its absence.
- **Lint L2** rewritten (164 → 176): the tool's `KEYS` are exactly the three; every reading command calls `--json` and names no `default_branch` in its block list; README documents each under `/roz-gate:config`; the menu names the keys, calls the tool, never edits the JSON or `CLAUDE.md`, has no forge lookup, splits on commas and quotes; the upgrade migration; the template is clean.
- **Replay seeds**: `seed-common.sh` drops `default_branch`; F7/C7 write the local JSON. Red-proofs 7/7. No SUT re-measure of F7/C7 yet.

### Docs
- README (command table, inbox section, config block + the local-keys block), onboarding step 3 (the builder's "Yours — per clone" group renders `/roz-gate:config …` lines), `workflow.md`, `init`, `hooks/README.md`, LEDGER L2.

### Checks
Hook tests 130/130 · lint 176/176 · red-proofs 7/7

## v1.22.0 — worktrees for every command; patrol closes merged issues out; must-read documents — 2026-10-03

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.22.0>

**Behavior:** three changes for a target repo — every state-mutating command now works in a linked worktree and never touches your checkout; patrol closes an issue out after its CR merges; agent-written documents keep a must-read on top and fold the rest. Versions 1.20.0 and 1.21.0 are the intermediate manifests of #51 and #52 and carry no tag.

### Behavior
- **The workspace** (#37, #53): `next-stage`, `integrate`, `spec-answers`, `review-answers` and patrol's address-review dispatches cut, merge, commit, test and dispatch seats in a linked worktree at `$(git rev-parse --git-common-dir)/roz-gate/wt/<branch>`, removed on both exits — no `git checkout`/`switch`/`reset`/`stash`/`merge` in your checkout, not even transiently, so a scheduled patrol can fire while you are mid-edit on the default branch. STOP's first obligation is "remove the worktree(s) this run created". A branch already checked out elsewhere makes `git worktree add` refuse: the mutex between concurrent commands, and a STOP that removes nothing.
- **Rule E's marker lives in the common git dir** (`--git-common-dir`): a fidelity dispatch running in the `qa/<n>` worktree is governed by the same marker as the checkout. Under the old `--git-dir` lookup the rule was silently off for exactly that dispatch (codex review); a hook test now calls from a linked worktree under the marker and is denied.
- **Close-out** (#41, #51): after you merge, patrol's next pass closes the issue out — one `**[patrol] · shipped**` comment, issue closed, every `track:`/`status:` label removed — wherever the forge did not finish it (GitLab; a CR against a release branch; GitHub's auto-close, which leaves the loop labels on). The action order is comment → ISSUE-CLOSE → LABEL-REMOVE, so an interrupted pass resumes; a merged CR without the marker on any other status is an illegal state. The spec CR body now says `Closes #<n>` (`Refs` was not deliberate). `ISSUE-CLOSE` and `ISSUE-LIST-CLOSED` on both adapters; GitHub CR-FIND returns `state,url`.
- **Must-read / supplement** (#42, #52): each producing brief states which sections are the must-read, what folds into `<details><summary>…</summary>` below, and a cap — intake summary 25 rendered lines, STOP comment 12, 3 lines per spec rule, 6 visible lines per intake question — rendered at a phone's ~60 characters, so a long bullet counts for several (codex review). Parsed shapes (markers, `## Open Questions`, `R<k>`/`G<k>`/`C<k>`, the §5 table) are unchanged.

### Evals
- **Replay A7** (red-proof 10/10): the merged-CR close-out on an open issue and on one the forge already closed. **Replay F8** (red-proof 5/5): the user mid-edit on the default branch is untouched by `next-stage`. Neither has a SUT baseline yet.
- **Lint** 102 → 164: **B5** the rendered-line counter over four fixtures plus conformance on every producer; **C8** the close-out prose, both adapters' new ops, `Closes` in A5/C5; **C9** the workspace rule at every branch site and every exit, no command instructs a checkout in your tree, the marker's git dir.
- **Hook tests** 113 → 118: the worktree forms of rule E; a call from a linked worktree under the marker.
- **Stub**: `gh issue close` routed; `issue list` honors `--state`.
- **LEDGER**: A7, B5, C8, C9, F8.

### Tooling
- **`/plan-issue`** (`.claude/skills/plan-issue/`, this repository's own habit — #49): grill first, rulings back on the issue, a five-section plan, implementation waits for the go.

### Docs
- README (§ Labels, troubleshooting), `workflow.md` (The workspace; close-out; 1b), the site's (7)/gate cards, simulator and wizard, onboarding step 5 and beat 2, quiz Q1, `evals/README.md` (C7/F7 baseline 5/5 each), CHANGELOG through v1.19.0.

### Checks
Hook tests 118/118 · lint 164/164 · red-proofs 7/7

## v1.19.0 — the base branch is config default_branch; a missing base stops the cut — 2026-10-03

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.19.0>

**Behavior:** `default_branch` is the loop's base — `spec/<n>` and `fast/<n>` are cut from it and their CRs target it — and a base the remote does not have stops the cut instead of cutting from nothing. A team on sprint release branches sets it to the current one with `/roz-gate:config` and changes it at handover.

### Behavior
- **The base branch** (#38): every statement of the rule — `next-stage` §0, `workflow.md`, README, `config.md`, `init.md`, the onboarding builder — names config `default_branch` as what `spec/<n>` and `fast/<n>` are cut from, what their top-level CRs target, what the fast reviewer diffs against, and what (6) merges in before (7). `feat/<n>` and `qa/<n>` stay siblings off `spec/<n>`. The commands always read the current value: an issue cut from the previous base is the human's to retarget and rebase; nothing pins a base per issue. Hotfixes stay outside the loop.
- **Existence check** (`next-stage` A2/C2): `git fetch --prune`, then `git rev-parse --verify -q origin/<default_branch>`; missing → STOP with `blocked`. A mistyped or retired base used to cut an empty branch; a plain fetch would have passed a stale tracking ref for a base the forge deleted (codex review).

### Evals
- **Replay C7** — the config names a base the remote lacks: F5's STOP obligations applied to the cut (blocked alone, the comment names the base, no CR, no push). Red-proof 6/6. **Baseline opus k=5: 5/5.**
- **Replay F7** — `default_branch = release/20261006` with `main` and an older `release/20260926` also on the remote: `spec/5` must descend from the configured base and the CR must target it. Red-proof 6/6. **Baseline opus k=5: 5/5.** Every earlier `next-stage` seed carried `default_branch: main` with only `main` on the remote, so the base had never been varied.
- **Lint C7** (88 → 102): A2/C2 cut from `<default_branch>`, prune, check, STOP; A5, C5, C6 and integrate read `<default_branch>`; no literal `main`/`master` as a base.
- **LEDGER**: C7, F7, and the L2 row 1.18.0 forgot.

### Tooling
- **`/plan-issue`** (`.claude/skills/plan-issue/`, this repository's own development habit): read the issue and the code, grill first (one question at a time, a recommendation each; falls back to the pattern when the `grill-me` skill is absent), write the rulings back to the issue, then a plan in five sections — main (tier decision, out of scope), eval (what existing cases cannot see, new cases with ledger text, red-proofs, the baseline per tier as the maintainer's spend decision after the blindness commit), doc (a fixed scan table), release (bump reason, the release-note block carried in the PR body, one PR straight to main), done-when. Implementation waits for the go.
- **CHANGELOG** regenerated through v1.18.0.

### Docs
- `evals/README.md` carries the C7/F7 baseline; README's evidence paragraph cites it.

### Checks
Hook tests 113/113 · lint 102/102 · red-proofs 5/5

## v1.18.0 — /roz-gate:config: the inbox filter and patrol model, settable any time — 2026-10-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.18.0>

**Behavior:** a target repo gains `/roz-gate:config` and three optional config keys — an inbox filter (`inbox_label`, `inbox_assignee`) and `patrol_model`. Absent keys mean today's behavior; the workflow template stamp is unchanged, so no repo needs a re-init.

### Behavior
- **`/roz-gate:config`** (`commands/config.md`): change one config key any time after `init` — pick it from a menu of keys with their current values, enter the value, an empty value clears an optional key. Rewrites only the config block, shows the diff first, never creates forge labels, never clears a required key (codex review), never offers `forge`. Issue #40 (absorbing #36).
- **Inbox filter** (`inbox_label`, `inbox_assignee`): with either set, only track-less open issues carrying that label / assigned to that login are the inbox; both set, both must hold. A track-less issue outside the filter is a plain issue — never commented on, locked or listed — counted once in patrol's report (`N track-less issues not in the inbox filter`). Inbox-only: an issue carrying a `track:` label advances by its labels whoever holds it; the gate-holder rule and hook rule A are untouched. Motivation: a tracker that is also a backlog made every track-less issue patrol's inbox — nine on this repo alone.
- **`patrol_model`**: the model patrol dispatches its seats with (`product` for intake, `implementer` for address-review); never the model patrol itself runs on.
- **Adapters**: GitHub `ISSUE-LIST` now returns `assignees` (what the filter reads); `LABEL-LIST` defined on both forges (codex review).
- **Idea template and adapters** still named the pre-1.4.0 `approve` keyword; they now say what moves the issue — end a comment with `summary` to read it back, the assignee (else the author) applies `ready-for-spec` / `ready-for-dev`, with GitLab's `status::` spellings shown.

### Evals
- **Judgment harness after the k=2 sweep on 1.17.0** (#35): the forge stub routes `GET /apps/<slug>` (`app-view`) and `GET /users/<login>[bot]` (`user-view`), keyed on `agent_login` like `gh api user` — F-67's bot-mode SUT, its token mint failed, went hunting for its identity and both iterations went invalid on UNKNOWN. Any other slug or login, a sub-resource, or a POST stays UNKNOWN; `[bot]` is a login spelling, never an app slug (codex review). Resume re-runs an iteration whose `result.json` says `quota-exhausted` (the sweep stopping, not the SUT measured) and treats a non-object `result.json` as unreadable; every other result stands.
- **The harness's own red-proof** (`evals/replay/redproof.py`, 18 cases): the stub routes and the resume rule, run by `run_redproofs.py` beside the cases' (red-proofs 2 → 3).
- **A SUT cut short is invalid** (#34): headless Claude Code killed sessions whose background seats outran 600 s and the runner scored the empty surface as recall 0; SUTs now wait for their seats (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`, the fixture timeout is the bound), the runtime's termination line or our timeout note invalidates, and each attempt starts with an empty `stderr.log` (codex review).
- **Judgment sources** (#33): `sources.py` sets up the ADMC clone and asks git whether a path is a checkout; no machine-local path in the repo; `.sources/` ignored beside `report/`.
- **SUT row `opus55`** (`claude-opus-5-5`) beside the `opus` baseline (#32).
- **Lint L2**: each new config key is offered by `config`, read by `patrol` and documented in the README block; the filtered-out issue is counted and never acted on; the filter is inbox-only; required keys protected; the adapters carry `assignees` and `LABEL-LIST`; L1 covers both site pages (lint 71 → 88).

### Docs
- **Onboarding page** (`docs/onboarding.html`, #46): the adopter's path — requirements and a maturity picker, install, what `init` does, a config builder that renders the CLAUDE.md block live with the `/roz-gate:config` steps for the optional keys, the first issue by phone or keyboard, what a patrol pass reports, the loop map with an "only my moves" toggle, a first-week checklist. The guide's nav gains "Get started →"; lint L1 holds both pages' inlined map byte-identical to `images/loop-stage-map.svg`.
- **`docs/releasing.md`**: how a version ships; `CHANGELOG.md` regenerated by `tools/changelog.py` through v1.17.0 (#32).
- **README**: the config block lists the three keys; `/roz-gate:config` in the command table; the inbox section explains the filter.

### Checks
Hook tests 113/113 · lint 88/88 · red-proofs 3/3

## v1.17.0 — D4 measures the shell route around the acceptance guard; the ledger gets an index and a procedure — 2026-09-26

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.17.0>

**No runtime change.** Hooks and commands differ from 1.16.3 only in file names (Python snake_case, the workflow template lowercased) and the paths that reference them.

### Evals
- **Replay case D4** (replay 18 → 19): with Edit denied on the acceptance suite, does the SUT route around guard-acceptance through the shell? Outcome-bound — no `spec/<n>` commit outside `qa/<n>` touches the suite, locally or pushed — with a vacuity guard and signal columns. No baseline yet, so whether the guard should also intercept Bash (raised by an outside review) stays open.
- **Red-proofs in the repo**: `cases/*/redproof.py`, run by `run_redproofs.py` on pre-push and CI. Required for every new replay case; the 18 older cases are exempt by name.
- **`evals/LEDGER.md`**: every case across the three tiers, with the ledger text the checkers cite. F6's measured turns corrected to 1/3/5/8/12.
- **`evals/CONTRIBUTING.md`**: the procedure for adding a case.

### Hooks
- **Test suite in stdlib unittest**, moved from bash: the same 113 cases, mutation-checked against the old suite, plus fixture-shape checks.

### Tooling
- **Root uv project**; `tools/` for dev-only tooling; ruff in pre-commit and CI.
- **`tools/dev-setup.sh`** wires the repo's own git hooks.
- **Naming allowlist** gains `LEDGER.md` and `CONTRIBUTING.md`.

### Docs
- **Evals**: baseline results and the autopsy taxonomy.
- **Learner material**: quiz bank draft-7; one loop stage map for the site and the quiz.
- **Wording**: "target repo" replaces "consumer"; the README names the bot-mode token helper.

### Checks
Hook tests 113/113 · lint 71/71 · red-proofs 2/2

## v1.16.3 — docs catch-up: layout, hook table, CHANGELOG, measurement track — 2026-09-21

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.3>

Docs only in effect: README gains 'How we know it works', the A–E hook table, 'Repository layout', design principle 8; ROADMAP gains the measurement track and a current state as of 2026-09-21; new hooks/README.md and CHANGELOG.md (generated from all 30 releases); templates/claude-workflow.md lowercased; images consolidated. The bump exists because two enforcement clauses were added to references/workflow.md (rule D at the open-questions collection point, rule E at 5q) and references/ is a behavior path to the pre-push gate — no runtime change. Also merged since 1.16.2: pre-push compares feature branches against their merge-base with main; Python files renamed to snake_case with a pre-commit + lint N1 naming check.

## v1.16.2 — rule E: echo/printf only in command position — 2026-09-20

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.2>

Closes the post-merge codex finding on 1.16.1: echo/printf are recognized only as commands (segment start or after && || ; | ( $( {, optional env assignments), so a real read such as grep echo src/app.txt is denied again while string mentions stay allowed. Hook tests 99/99, lint 70/70.

## v1.16.1 — rule E: mentions in shell strings; D2 counts denied attempts — 2026-09-20

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.1>

guard-blind rule E no longer denies src/ mentioned inside echo/printf operands or # comments; the D2 checker pairs tool calls with results so a hook-denied attempt is counted as attempts-denied, not a breach; forge stub gains issue-view (REST) and review-comment-view routes. Known follow-up: echo/printf matched as words anywhere in a segment can blank a real read (codex, fixed in 1.16.2). Hook tests 92/92, lint 64/64.

## v1.16.0 — fidelity review is blind by mechanism (rule E) — 2026-09-17

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.16.0>

guard-blind rule E: while a fidelity dispatch is active (marker in .git/roz-gate/), Read/Glob/Grep on src/ and git operations on feat/<n> are denied with the remedy in the message; exclusion forms stay legal. Promoted from the opus baseline sweep (D2 4/5: a QA child ran cat src/app.txt under the dispatch). Rules enforced mechanically: 4 → 5. Hook tests 89/89, lint 59/59.

## v1.15.0 — open questions have one home (rule D) — 2026-09-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.15.0>

guard-gate rule D denies a git commit while any specs technical-spec.md carries an open-questions section; the lint tier backstops it at push. Promoted from the opus baseline sweep, where E2 measured 0/5 after the A6 prose was made explicit — the model copied and threaded the question every time and deleted the source section never. Rules enforced mechanically: 3 → 4. Also: review-comments-list read route in the forge stub. Hook tests 72/72, lint 47/47.

## v1.14.2 — relocate means move; sweep-autopsy instrument fixes — 2026-09-15

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.14.2>

Behavior: next-stage A6 now states that a question swept from another spec doc is MOVED into spec.md's Open Questions — deleted from the source, at most a one-line Q-ID pointer remains (ruling from the first opus baseline sweep: E2 5/5 and F3 2/5 copied instead of moving). Instrument: D2 exclusion syntax is not a touch; F2 counts answers, permits readbacks; C5 fixture carries a real test suite committed on main; forge stub gains pr-diff value flags and a comment-by-id read route. Lint 39/39, hooks 60/60.

## v1.14.1 — rule C per-segment classification — 2026-09-06

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.14.1>

guard-gate rule C now classifies per shell segment (tokenizer-emitted operators, glued forms included), fixing the compound-command -F false positive found while dogfooding. 60/60 hook tests. Also merged: the replay tier (evals/replay — 18 cases, stateful forge stub, multi-model runner; eval infrastructure, no behavior change).

## v1.14.0 — the quote-open guard (rule C) — 2026-08-23

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.14.0>

The B4 runaway — patrol reading a quote-opening agent comment as a human answer and replying to itself once per pass — now has mechanical enforcement. Guard-gate rule C denies any forge comment write whose body opens with a quote block (including after leading blank lines or whitespace) while carrying a roz-gate marker (`**[` / `✅ [`) anywhere. Static, no forge API call; the deny message states the remedy: marker on line one, quote below, or hand the text back to the human.

Scope is deliberate and honest: comment-shaped writes only (a CR or issue *body* may legitimately open by quoting); the marker condition keeps unmarked writes untouched; `--body-file` bodies are read back or heredoc-parsed and judged — the blocking review finding, since the long multi-line readback is exactly a `--body-file` body — and a body the guard cannot see fails closed only when the command itself shows a marker. Command-substitution bodies are structurally invisible to any static hook and stay on the prose rule, stated in the docstring rather than implied covered.

54/54 hook tests (15 new: 8 deny paths, 5 allow paths including the prescribed remedy, a no-API assertion, a scoping control), red-proofed by three mutations each caught by exactly its own test.

## v1.13.0 — the eval ledger's lint tier — 2026-08-23

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.13.0>

Ten static checks — the lint tier of the eval ledger — now gate every push: `evals/lint/run-lint.sh` (39 checks) plus the hook unit tests run from `.githooks/pre-push`, with `.github/workflows/checks.yml` as the CI backstop for `--no-verify`.

Every case guards failure mode 2: the rule itself is broken, so every stage faithfully executes it and reports green. Runtime-check cases get two layers — pattern proof against fixtures, and byte-for-byte source conformance — because the checks under test are greps a model executes from prose.

Building the suite found two shipped defects whose ledger annotations claimed them fixed:

- **B1** — the unverified-claim check still grepped only the bare literal `(unverified)`; 1.12.0 fixed the two-axis writing convention but never widened the pattern, so `(from Q4, unverified)` — the exact channel the false claim entered through — passed the check. Now `(^|[(,])[[:space:]]*unverified`, catching the merged and the wrap-split compound.
- **C6** — 1.11.0 documented the all-states CR query in both forge adapters, but no command ever invoked it: spec-answers §7's post-integration branch, which must tell *merged* from *absent*, was unreachable, and a shipped issue would have been sent back through implementation. The branch point now requires CR-FIND's all-states form.

In both, the fix landed where it was written and never where it was read — which is why conformance checks anchor on the site that reads the rule.

`evals/README.md` states what a green run proves and what it does not (every case derives from one repository, one operator, one atypical issue), and sets the red-proof requirement: a new case counts only once it has been demonstrated to fail legibly.

## v1.12.0 — the spec learns what kind of sentence it holds — 2026-08-20

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.12.0>

A field review of a full artifact set (spec.md / technical-spec.md / test-spec.md, lived-in end to end) surfaced three defects in how the spec stage writes. All three shared a shape worth naming: each was reported at the stage where it *appeared*, one stage narrower than where the failure class *lives*. The release fixes the classes.

### Rulings are not claims

Two kinds of sentence shared the spec's typography and its authority: rulings ("the role value is ignored" — true because the holder said so) and empirical claims ("neither run fails" — an assertion about reality, which was false, and a test was derived from it). The separator is now the **jurisdiction test**: *can the implementer be ordered to make this sentence true?* No → it describes pre-existing reality, and writing it down does not make it true.

Empirical claims carry evidence tags — `(measured, <date>, <scope>)` (the date says when; the scope is the falsifier), `(unverified)`, or the demotion `(assumed-empirical: <named risk>)` — enforced in three layers: the gate kit's attention list, the spec-answers promote report, and a **Path B entry STOP**: an `(unverified)` claim cannot be signed. The stop is coverage, not caution — a claim false only under conditions the acceptance run never produces goes green through validation, fidelity review, and the integration verdict, because *a faithful transcription of a falsehood satisfies fidelity*. Nothing downstream of the spec stage can reach that branch.

The holder's own answers are covered too: empirical content inside a ruling folds with both tags — **the holder is not an oracle about reality**, and the original false claim entered through exactly that channel.

### Questions have one home, and answers land where they bind

`spec.md`'s `## Open Questions` is the single collection point for every seat's questions — a question written into any other document has no route to the gate holder (the field case: four implementer questions stranded in the contract, one of them a timeout trap, saved by hand). Seats return their batches; the main agent appends and numbers them; the A6 sweep relocates strays. And folds now land in **the document the raising seat owns** — an implementer question's answer amends the contract QA tests against, or the pipe is one-way: question reaches the holder, answer never reaches the tests.

The mid-flight ambiguity route now covers every seat that can hit one: QA (as before), **the implementer at (3)** — stop and report, never decide unilaterally in code — and (5) review findings that are really contract ambiguities.

### The port declares what it can show, and the holder countersigns

When the implementer designs the test port it now walks every scenario once — observable, observable via which control point, or a limitation — as a table in the contract. A **limitation is a verdict exemption, and the implementer never grants its own**: every one surfaces on the spec-gate attention list for the holder to sign. QA still walks independently at (4); every mismatch, both directions, is a mandatory finding, and the fidelity review audits the reconciliation.

### Smaller

- **Resolved-question entries trim** to ruling + attribution + one-sentence rationale + fold pointers — the spec reads as current truth; the argument lives in the decision ledger and the thread.
- Scenario text is Given/When/Then only; guidance addressed to another seat is a rule, never a scenario.
- `technical-spec.md` gains `C<k>` clause numbering — anchor-free contract prose cannot be cited, audited, or kept current.
- Tag checks match opening tokens only (tags with free text wrap; a wrapped tag is present, never absent).
- B6's wording now matches patrol: a fresh implementation-blind reviewer resolves fidelity threads — the audited party never closes the audit's findings.

### Upgrading

No re-init needed — the project workflow template is unchanged.

## v1.11.0 — the review conversation — 2026-08-17

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.11.0>

Stage (7) had a reading surface and no hearing surface. `status: in-user-review` was a terminal-wait row in patrol's classification table, so the gate holder's comments on a spec CR were never read — three of them sat for a day. 1.10.0's gate kit made it sharper: a review page that works *generates* comments.

**(7) is now a discussion stage hosted by the main agent.** It answers what the artifacts already say — quoted, with a permalink at a SHA — dispatches a seat when the answer needs specialist judgment, and reads any change back to you in one line before making it. Nothing is built without your word; silence is never consent.

### What's new

- **`/roz-gate:review-answers`** — one turn of the conversation. Ranked above integrate in patrol (the person at the final gate never queues behind machine work); answer-only turns are exempt from the one-issue-per-pass rule, so a multi-day conversation can't starve the loop.
- **Three-channel detection** — inline threads, review summary bodies, and top-level CR comments. `REVIEWS-LIST` and `CR-COMMENTS-LIST` are new adapter ops on both forges: a body-only *changes requested* review used to scan clean, and a reply typed on a phone lands in the channel nobody read.
- **The agent-marker test is now `**[` / `✅ [`** — with the bracket. A human's own `✅ looks good` was the single highest-value message in the channel and the old predicate classified it as an agent comment. The same prefix invariant is the livelock brake: it is what stops the conversation answering itself.
- **Seat-on-edit** — any resolution that would edit a file gets one seat opinion before the readback. The trigger is the act you are about to take, not a judgment about what the comment implied. It is the only mechanism at (7) that puts a failure branch in front of you.
- **A new PreToolUse hook** — acceptance files are not editable on a `spec/*` branch. Branch and path only: no stage detection, no exemption list, so "the main agent is not exempt" is true by construction rather than by prose. At (7) the main agent hosts, authors, commits, runs the verdict and assembles the page you read — it is the one stage with no adversarial second party.
- **The hand-back rule**, named once and cited from both sites: any SHA wearing `in-user-review` has a captured green *full* acceptance and unit run at that SHA, with evidence cards regenerated wholesale. What it licenses is one sentence — *"green against the pre-rework spec, at SHA `<x>`"* — never "verified". A weaker claim needs fewer guards to stay true.
- **Back to intake as a first-class outcome** — strip `track:` and `status:` and the issue is a raw idea again, discussion intact. Redoing work is cheap; re-answering rulings you already made is not, so the decision ledger carries forward as prior answers to confirm.
- **(7) renamed Merge → Review** in the docs (the label is unchanged). "Nothing is left but your review" was never true and is now gone. (7) also has no `blocked` exit — the issue is already at your gate.

### Fixed

`/roz-gate:spec-answers` had no post-integration branch: an issue returning from (7) hit the first-pass path and was told it was "ready for your approval to move to implementation" when implementation was already done. That path becomes primary under this design.

### Upgrading

No re-init needed — the project workflow template is unchanged.

## v1.10.0 — the gate kit: gates a human can actually hold — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.10.0>

The first closed loop's gate holder drowned in R/S/G cross-references. This release gives each spec-track issue a **gate kit**: one comment on the spec CR, edited in place across the issue's life, assembled mechanically (extraction and quotation only — never synthesis) under hard rules: **quote-never-paraphrase, every claim links its line, no conclusions, exhaustive-or-say-so, the kit states its own blind spot, the CR diff stays primary, the top reads in 90 seconds.**

- **Attention list** — a computed **sort, never a filter** (the word "mechanical" never appears): `(assumed)`-provenance rules first (decisions made in your name you never made), then rules whose text changed after your ruling, then coverage gaps, then weak-assertion findings from the fidelity review.
- **Issue-delta instead of a summary** — "you asked for X; the spec adds these N things you didn't ask for and drops this one you did." A summary of the spec, by its authors, structurally can't show that.
- **Decision ledger** — your answer quoted verbatim **next to the fold the spec actually gained**; agent additions marked *interpretation:*. The gap between what you said and what got written is where expensive errors live.
- **Evidence cards** (final gate) — per scenario, four buckets (covered / partial / not covered / cannot-be-covered-black-box), assertion excerpts and **actual observed values from the green run's captured output** — "value not emitted — assertion only" where thin, never the expectation restated as an observation.
- **The since-you-approved diff** — your gate label stamps the spec SHA; the final gate shows exactly what changed since, hunk by hunk, annotated by cause. Approval that can silently expire is the most dangerous property a gate can have — the first closed loop exercised it.

New COMMENT-EDIT forge op (both adapters). Success metric, instrumented from day one: the **artifact-change rate at gates**, not the approval rate — a gate that only ever waves things through is decoration. Prose-only; tests 27/27.

## v1.9.0 — the verdict's source gets an auditor: QA fidelity review — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.9.0>

The integration verdict is the loop's headline claim, and the QA suite is the artifact it's computed from — until now, the loop's only unaudited node. A vacuous suite made a green verdict silently forgeable. New stage **(5q)** closes it.

- **A second, implementation-blind reviewer dispatch** audits the QA suite's fidelity to the spec — run on a `qa/<n>` checkout, so the same branch topology that makes QA blind makes the auditor blind (a fidelity reviewer who has seen the implementation rates tests faithful *because they pass* — the exact bias to remove). Contract: the new `references/fidelity-brief.md`.
- **Four questions**: does each test assert what its scenario says; vacuous assertions (a 12-item static checklist); is `test-spec.md`'s coverage claim honest; and **over-assertion** — a test requiring behaviour no spec text states produces a false RED, which costs the verdict its credibility.
- **Evidence, never a verdict**: every finding carries two verbatim quotations side by side — the spec clause and the assertion excerpt ("S5 says ghosts are logged **by name**; the test asserts `len(skipped) == 2`"). No citations ⇒ QA declines the finding. Plus the origin rule: an expected literal with no origin in spec text was almost certainly read off the implementation.
- **Contract-currency step zero**: amendments agreed in threads but not folded into the contract block the review — a fidelity audit against a stale contract launders the staleness as verified.
- **Wired into the existing machinery**: findings are QA-CR threads; patrol's address-review now drives both CRs (qa addresses, a fresh blind dispatch re-checks); integrate gains the symmetric precondition — both CRs thread-clean before the verdict runs.
- **`test-spec.md` gets a required shape**: the scenario→test map must be derivable from machine-readable trace markers in the test source (config `trace_marker`, or qa declares one) — hand-maintained trace matrices are complete, tidy, and stale.

Prose-only (commands/references/personas); no hook, marker, or label changes. Tests 27/27.

## v1.8.1 — suite layout is the project's call — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.8.1>

The rule "tests are a living, feature-organized suite — never per-issue folders/tags" conflated two things: the invariant and a default. Unbundled:

- **The invariant stays hard**: tests are a *living suite* — maintained and evolving, never write-once per-issue snapshots. Black-box information flow and branch topology are untouched.
- **The layout becomes a project-overridable default**: suite organization is project-layer philosophy, like the test runner or lockfile commands — so it now follows the same pattern they do: an optional config key, `acceptance_layout` (absent = feature-organized, the default; e.g. `one folder per issue, shared fixtures in support/`). QA and the workflow read the project's declared convention — **a project-sanctioned layout is never a violation to flag**.

Born from real usage: the first closed loop shipped a per-issue layout pinned by its technical spec, and the QA seat correctly followed the contract while flagging tension with prose that had no business being hard. Prose-only; tests 27/27.

## v1.8.0 — make the existing loop honest — 2026-08-16

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.8.0>

First fruits of the first fully-closed spec-track loop (run by a real project): a four-seat evaluation of the resulting proposal package surfaced two defects in shipped commands and two enablers. This release is the "fix and enable" slice; the audit (QA fidelity review) and gate-holder legibility slices follow under separate rulings.

- **The reviewer now receives the claim.** The stage-(5) dispatch attached only the code diff — the spec docs live on the branch the diff excludes, so the independent reviewer was reviewing code against its own inference of intent. It now gets `spec.md` + `technical-spec.md` (fast track: the issue's story + AC).
- **Integration REDs gain the missing third class: the contract itself was false.** "Harness issue" is tightened to failures where the test never reached its assertion; a faithful assertion that reality disproves is a **contract defect** → STOP, amend the contract, QA re-derives. New command law: *an integration RED is never resolved by editing a QA assertion to match observed behaviour* — that would rewrite the verdict into an echo of the implementation.
- **Numbered rules with provenance.** `spec.md` enumerates story-level rules exhaustively (`R<k> · <title>`), each annotated `(from Q<j>)` / `(from AC-<j>)` / `(assumed)` — the human can now see which decisions were made in their name that they never made, and downstream audits get an honest denominator.
- **Titled ID citations.** First mention of any rule/scenario/question ID in a comment, thread, or report carries its title and a definition link — never a bare code. The reader may be on a phone with no lookup table in their head.

Prose-only (commands/references); no hook, marker, or label changes. Tests 27/27.

## v1.7.1 — the README catches up: agent identity and the hook, surfaced — 2026-08-11

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.7.1>

Docs-only patch. v1.7.0's biggest feature was invisible to anyone who didn't read the release notes — and it turned out v1.5.0's enforcement hook had never made the README either.

- **README · Agent identity**: new section — user mode (default, zero setup) vs bot mode (GitHub App / GitLab project access token), why it matters (you can tell who's speaking; the agent's questions actually notify you — posting under your own account suppresses every ping; your credentials stay out of its hands), the `a bot never holds a gate` invariant, and the three config keys with a link to `references/identity-github-app.md`.
- **README · Labels**: the two human-only rules are tool-layer enforced by the bundled PreToolUse hook, fail-closed. *Prompt discipline is the manners; the hook is the law.*
- **Interactive guide**: both additions, bilingual, in the labels section.

No behavior changes; tests 27/27.

## v1.7.0 — agent identity separation: the agent gets its own face — 2026-08-11

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.7.0>

The agent now acts under its **own forge identity** — a GitHub App (`<slug>[bot]`) or a GitLab project access token bot — instead of the human's session. Opt-in via `agent_identity: bot` in the config block; absent keys keep user mode, bit for bit.

**Why it matters**: the human finally gets notified (an agent posting under your own account suppresses every ping — async intake's "from anywhere" promise was half missing); identity becomes author structure instead of text convention; personal tokens stay out of agent hands.

- **Two new invariants**: a bot never holds a gate (bot-created issues are born with a human assignee; bot-authored unassigned issues have no gate holder), and authority checks compare authors, not markers.
- **Hook**: config-driven bot mode — bot logins excluded from gate-holder resolution, and "a summary was already posted" now requires the poster to *be* the bot (a human quoting the marker no longer counts). Login comparison normalizes the `app/` prefix and `[bot]` suffix — the same App surfaces three ways across API paths (live-verified).
- **Adapters**: per-invocation tokens only (never exported), HTTPS push with per-command git author flags, GitLab JSON-body and async-`diff_refs` corrections from the live spike.
- **Setup**: `references/identity-github-app.md` (GitHub App + GitLab project token, human-created — verified on gitlab.com free tier) and `scripts/gh-app-token.sh` (installation-token minting).
- **Intake polish**: question batches hard-capped at 5, and the batch header now says it: recommendations all look right? Apply the gate label directly — that alone confirms them.
- **Init**: creates `acceptance_dir`/`specs_dir` at bootstrap (a configured path must exist from day one).

Test suite: 27 cases (4 new bot-mode). No re-init needed — plugin update is the whole upgrade.

## v1.6.1 — spec open questions adopt the intake batch format — 2026-08-09

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.6.1>

Format-only patch, born from the first real stage-(2) run: the spec CR's question threads were hard to read and answer as single bold paragraphs.

- `spec.md`'s `## Open Questions` items now use the intake batch shape — title line `**[<role>] · Q<k> · <label>**` (with `(story-level)` folded into the title), one-sentence question, (a)/(b) option bullets with `← ✅ recommended`, one italic why.
- A6 posts each item **verbatim** as its inline thread body (single source of truth: A3 defines the shape once); story-level items end with the italic mirror note.
- The `**[` marker that `/roz-gate:spec-answers` relies on is satisfied by the title line by construction — no behavior change, no hook change, no re-init.

## v1.6.0 — one-comment intake convergence: the label folds in the holder's words only — 2026-08-09

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.6.0>

Async intake gets a single authorization invariant: **every word that reaches the issue body was either said by the gate holder or seen by them.**

- **One-comment summary requests**: the trigger is now a comment whose first or last line is exactly `summary` — corrections and the request ride together, no more two-comment dance. Mid-sentence mentions, quoted `> summary` lines, and `Summary:` headings don't trigger; the bare one-word form still works.
- **The gate label folds in the holder's words only**: finalize reuses the latest `**[intake] · summary**` verbatim unless the *holder* commented after it — then it regenerates from the holder's words alone (bystander comments are thread discussion: context, never content, folded in solely through the holder's explicit endorsement). The regenerated summary is posted as a comment before the body edit — the paper trail for after-the-fact review. This closes an authority leak: bystander input can no longer enter the gated body unseen under the holder's label.
- The confident-holder shortcut (label without ever asking for a summary) stays, now with a single meaning: "build the story from everything I said."
- Hook updated in lockstep (`is_summary_request()` line rule); test suite grows to 23 cases.

No re-init needed — plugin update is the whole upgrade.

## v1.5.0 — hook-enforced gates: intake-summary triggers and human-only gate labels — 2026-08-08

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.5.0>

The protocol's two highest-stakes human-only decision points are now enforced at the tool layer by a PreToolUse hook, not just by prompt text:

- **Rule A — intake-summary trigger**: an `**[intake] · summary**` comment posts only when a gate label is present or the gate holder's latest comment is `summary` (with no summary posted since). Anything else is blocked with a message pointing at the protocol.
- **Rule B — gate labels are human-only**: agents can no longer `--add-label` `ready-for-spec` / `ready-for-dev` (removal, list filters, and `label create` are unaffected).

Design: a zero-cost bash prefilter escalates to a python validator only when a guarded pattern appears; forge API failures fail closed with a distinct retry message; no bypass variable — the legitimate unlock is the protocol itself. Covers both `gh` and `glab`. Ships with a 19-case test suite (`hooks/tests/run-tests.sh`).

Enforcement arrives on plugin update — no re-init needed.

## v1.4.0 — three-beat intake: ask once, summarize on demand, the label confirms — 2026-08-06

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.4.0>

## Highlights

### 🧹 Async intake, radically simplified
The intake state machine collapses into **three beats**:

1. **Ask once.** Patrol posts a single batched questions comment (numbered, options with a marked recommendation, background collapsed) — then steps back. No re-batching, no reply grammar required: the thread belongs to the humans. Free-form discussion, open to the whole team, from any device.
2. **Summarize on demand.** When the discussion settles — or immediately, if the recommendations look right — the **assignee comments `summary`**. The agent condenses the issue body + all comments into one `[intake] · summary`: story + acceptance criteria + proposed track + an attributed decision trail, with two honest sections: **assumptions** (every unanswered question, resolved to its recommendation and stated plainly) and **contested points** (disagreements shown both-sides; one reply flips them).
3. **The label confirms.** No `approve` keyword. The assignee applies the gate label, and the choice itself confirms the track: `ready-for-spec` ⇒ `track: spec`, `ready-for-dev` ⇒ `track: fast`. Patrol then rewrites the body and the loop takes over. Confident? Skip `summary` and label directly — patrol summarizes before finalizing either way.

**Everything before the label is input; the label is the decision.** Gone: the `approve` keyword, the digest comment type, re-batch rounds, and answer-parsing rules — patrol's async intake is now a three-trigger route.

### 📖 Guide updated
The [interactive guide](https://taikerliang.github.io/roz-gate/) tells the new story end to end: the simulator walks the free discussion, the `summary` comment, the contested point a teammate wins, and the single label that closes intake and opens gate one; the wizard and label cards follow suit.

## Install / upgrade

```
/plugin marketplace add TaikerLiang/roz-gate
/plugin install roz-gate@roz-gate-marketplace
```

No re-init needed — the new flow lives entirely in the plugin's brief and commands.

**Full changelog**: https://github.com/TaikerLiang/roz-gate/compare/v1.3.0...v1.4.0

## v1.3.0 — team-ready intake: reply grammar + gate-holder authority — 2026-08-05

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.3.0>

## Highlights

### 💬 A reply grammar built for phones
Async intake batches now follow a fixed, skimmable format: numbered questions with 2–3-word labels, option bullets with the recommendation marked, a one-line *why*, and long background collapsed into `<details>`. Answering is one line from any device:

- `all recs` — take every recommendation, done
- `1a 2b` — answer per number
- free text — always works

### 👥 Gate-holder authority — intake goes multi-player
Intake threads are open to the whole team, but authority never drifts:

- **Gate holder = the issue assignee** (unassigned → the issue author). A native forge field on both GitHub and GitLab — zero new config.
- Anyone may reply; every answer is folded **attributed**. Only the gate holder's answers settle questions, and only their `approve` files the proposal — an `approve` from anyone else is noted, never triggered.
- **Conflicts are never resolved by the agent.** Disagreeing replies come back as an `[intake] · digest` @-mentioning the gate holder — who said what, the trade-offs, the agent's recommendation — and the holder's reply is the decision of record.
- The proposal cites the decision trail: who proposed, who decided. The MOU gets a signature page.

### 📖 Guide updated
The [interactive guide](https://taikerliang.github.io/roz-gate/) now tells the team story: the issue-life simulator includes a teammate's conflicting reply and the digest the assignee settles, and the "what should I do now?" wizard knows the gate-holder rule.

## Install / upgrade

```
/plugin marketplace add TaikerLiang/roz-gate
/plugin install roz-gate@roz-gate-marketplace
```

Existing projects need no re-init for this release — the new rules live in the plugin's brief and commands.

**Full changelog**: https://github.com/TaikerLiang/roz-gate/compare/v1.2.0...v1.3.0

## v1.2.0 — persona seats: bring your own agent team — 2026-08-05

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.2.0>

## Highlights since v1.0.0

### 🪑 Persona seats — link your existing agents into the loop (1.2.0)
The five role names (product, em, implementer, qa, reviewer) are now **fixed seats** with swappable occupants. Already have a `backend.md` you've tuned for months? `init` links it into a seat (`implementer: backend`) — your file stays yours, unmoved and unrenamed; unlinked seats fall back to the plugin defaults.

- New `### Roz Gate personas` block in the project CLAUDE.md maps each seat to the subagent actually dispatched.
- **Persona is swappable; the contract never is**: every dispatch attaches the seat's Owns/Never contract, and `init` lints a linked persona against it at link time — a qa that wants to "read the code first" doesn't get seated.
- Fully backward compatible: projects without the block keep plugin defaults; patrol flags when a re-init would help.

### 🚪 Clean exits: `/roz-gate:uninit` (1.1.0)
The inverse of `init`: refuses to run while anything is in flight, removes exactly what `init` installed (CLAUDE.md section, implementer persona — asked first, idea template), keeps forge labels by default (deleting them erases closed-issue history), and never touches work products — specs and the acceptance suite become ordinary project assets. Run it in every project **before** `/plugin uninstall roz-gate`.

### 📖 Interactive guide
A bilingual (EN/中) one-page guide at **https://taikerliang.github.io/roz-gate/** — the MOU→contract mental model, the team's seats, a clickable loop map with the three gates, a label reference, a step-through "life of an issue" simulator (with the change-order detour), and a "what should I do now?" wizard mirroring patrol's classification table.

## Install / upgrade

```
/plugin marketplace add TaikerLiang/roz-gate
/plugin install roz-gate@roz-gate-marketplace
```

Existing projects: update the plugin, then re-run `/roz-gate:init` — it refreshes the workflow pointer and walks you through seating the team.

**Full changelog**: https://github.com/TaikerLiang/roz-gate/compare/v1.0.0...v1.2.0

## v1.0.0 — 2026-08-04

<https://github.com/TaikerLiang/roz-gate/releases/tag/v1.0.0>

Plugin renamed from **gated-loop** to **roz-gate** (repo moved to TaikerLiang/roz-gate). Marketplace name is now `roz-gate-marketplace`; commands are now `/roz-gate:*`. Existing installs must re-add the marketplace and re-run `/roz-gate:init` in each project.

## v0.6.1 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.6.1>

- **The workflow prose now ships with the plugin, not with each repo** — `/gated-loop:init` writes only a short pointer section + config block into the project's CLAUDE.md, referencing `references/workflow.md` inside the plugin. A plugin upgrade now takes effect in every bootstrapped repo at once, no re-init needed
- Fix: the CLAUDE.md stamp tracks the template version, not the plugin version
- Docs: init writes a workflow pointer, not the workflow itself

## v0.6.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.6.0>

- **Propagate plugin upgrades into installed workflow sections** — groundwork for keeping repos bootstrapped on older plugin versions in sync

## v0.5.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.5.0>

Docs release — sharpen the workflow's mental model:

- **The MOU-vs-contract model for intake and spec**: intake produces a memorandum of understanding (story + AC), the spec stage produces the binding contract
- Expand it into the owner–contractor–inspector table mapping the roles

## v0.4.1 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.4.1>

- **Exempt inbox triage from patrol's one-issue-per-pass rule** — a patrol pass acts on one in-loop issue, then triages the whole inbox; since intake is comment-only, every batch of questions lands in a single pass
- Docs: note patrol triages the whole inbox each pass

## v0.4.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.4.0>

- **Batch async-intake questions into one comment per patrol pass** — a comment round trip costs a day, not seconds, so the inbox's intake now posts every open question at once (numbered, each with a recommendation) instead of one question per pass
- README: describe batched inbox questions

## v0.3.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.3.0>

- **Route all intake through the product agent via a shared intake brief** — clarification thinking lives in the specialist, never the orchestrator; `/gated-loop:to-issues` and patrol's async intake now share one brain (`references/intake-brief.md`)
- Add a pre-push hook enforcing plugin version bumps
- README: document `/gated-loop:to-issues` and the shared intake brief

## v0.2.0 — 2026-08-02

<https://github.com/TaikerLiang/roz-gate/releases/tag/v0.2.0>

Initial public cut of the Gated Loop plugin: the role-driven, human-gated development workflow — spec debate, blind black-box QA, independent review, integration verdicts, and a patrol scheduler — for GitHub (gh) and GitLab (glab).

