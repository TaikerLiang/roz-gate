---
name: release
description: Ship a roz-gate version on Haiku — `prepare <x.y.z>` assembles the release note from the merged PRs' `## Release note` sections, bumps the version, writes the pending CHANGELOG entry and opens the release PR; `publish <release-pr>` creates the GitHub release on the merge commit, verifies the changelog, comments "Shipped in" on the issues and cleans up. Use when the maintainer says a release is due or that the release PR is merged.
argument-hint: "prepare <x.y.z> | publish <release-pr-number>"
model: haiku
allowed-tools: Bash(git *) Bash(gh *) Bash(python3 tools/changelog.py *) Bash(python3 hooks/tests/run_tests.py) Bash(python3 evals/lint/run_lint.py) Bash(python3 evals/replay/run_redproofs.py) Bash(sed *) Read Write
---

# /release — the release flow, mechanical, on Haiku

`docs/releasing.md` is the procedure; this skill runs it. Two modes, from
`$ARGUMENTS`: `prepare <x.y.z>` and `publish <n>`. Anything else: print
this usage and stop. Never merge a PR — the maintainer merges. Never edit
`CHANGELOG.md` by hand — `tools/changelog.py` writes it.

Paths: the main checkout is `/Users/taiker/dev/roz-gate`; worktrees and
scratch files go under the session scratchpad directory named in the
system prompt (never the main checkout, never `/tmp`).

Commit trailer: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
(the trailer stays as the session's attribution line says, whatever model
runs this skill). PR bodies end with
`🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

The gate and the push: `.githooks/pre-push` runs the full gate (hook
tests, lint, ledger `--check`, red-proofs) and GitHub closes the SSH
connection before it finishes ("Connection to github.com closed by remote
host", nothing pushed). The pre-commit hook runs only naming + ruff. So
run the gate yourself, in the worktree, and only when all four are green
push with `git push --no-verify`. **The full gate runs once per release**
(prepare step 3, on the released tree, ~3–4 min); the bump commit changes
only `plugin.json` and `CHANGELOG.md`, which no suite reads, so step 4
proves that instead of re-running it:
```sh
python3 hooks/tests/run_tests.py && python3 evals/lint/run_lint.py && python3 tools/ledger.py --check && python3 evals/replay/run_redproofs.py
```
Confirm with `git ls-remote --heads origin <branch>` before `gh pr create`.
CI re-runs the same suites; a red there is a stop, never a merge.

## prepare <x.y.z>

1. **What is in it.**
   ```sh
   cd /Users/taiker/dev/roz-gate && git fetch -q origin --tags
   PREV=$(git describe --tags --abbrev=0 origin/main)
   git log --merges --format='%s' $PREV..origin/main        # "Merge pull request #N …"
   git diff --stat $PREV origin/main -- agents bin commands references templates hooks scripts
   git show origin/main:.claude-plugin/plugin.json | grep '"version"'   # must equal $PREV without the v
   ```
   If the version on `origin/main` is not `$PREV`, stop and report: a
   release PR is already open or something is off. Then the worktree —
   every command from here on runs inside it, so the checks and the
   commit describe the released commit, never the main checkout:
   ```sh
   git worktree add -q -b release/<x.y.z> <scratchpad>/wt-rel-<x.y.z> origin/main
   cd <scratchpad>/wt-rel-<x.y.z>
   ```

2. **Minor or patch** — by `docs/releasing.md` § Minor or patch. A
   hook rule, a new command, or a target repo's behaviour changing is
   minor; fixes, docs, evals-only is patch. If `<x.y.z>` the maintainer
   gave disagrees with that reading, say so in one line in the PR body
   and use the maintainer's number.

3. **The release note.** For every merged PR number from step 1:
   `gh pr view <N> --json body,title -q .body` and take the text from
   `## Release note` to the next `## ` heading (or the attribution line).
   Assemble one note in the layout of `docs/releasing.md` § The release
   note:
   - first line: the runtime impact in bold — `**Behavior:** …` when any
     PR changed a behaviour path, else `**No runtime change.** <why the
     version moved>`;
   - then `### Behavior`, `### Evals`, `### Hooks`, `### Tooling`,
     `### Docs` — merge the PRs' bullets under their sections, keep each
     bullet's bold subject and issue/PR references, drop empty sections;
   - `### Checks` is one line with the counts from the gate run in the
     release worktree (step 1's `origin/main`, which is the released
     tree minus the bump):
     ```sh
     python3 hooks/tests/run_tests.py 2>&1 | tail -1
     python3 evals/lint/run_lint.py 2>&1 | tail -1
     python3 tools/ledger.py --check
     python3 evals/replay/run_redproofs.py 2>&1 | tail -1
     ```
     written as `Hook tests N/N · lint N/N · red-proofs N/N · ruff ·
     judgment `--check` · ledger `--check` current`. A red here stops the
     release: report it, open no PR.
   A PR that changed a behaviour path and has no `## Release note` section
   is a defect: stop and report it, do not invent the note.
   Write the note to `<scratchpad>/notes-<x.y.z>.md`. Title:
   `v<x.y.z> — <three to six words naming the headline change>`, taken
   from the first Behavior bullet's subject (or the first bullet overall).

4. **Bump + pending changelog, one commit.**
   ```sh
   set -e; cd <scratchpad>/wt-rel-<x.y.z>
   sed -i '' 's/"version": "<prev>"/"version": "<x.y.z>"/' .claude-plugin/plugin.json
   python3 tools/changelog.py --pending v<x.y.z> <scratchpad>/notes-<x.y.z>.md "<title>"
   git add .claude-plugin/plugin.json CHANGELOG.md
   git commit -q -F <scratchpad>/rel-commit.txt      # "release: <x.y.z>", blank line, one paragraph why minor/patch, blank line, the trailer
   ```
   Do **not** re-run the full gate: step 3 ran it on this tree minus the
   bump. Prove the commit is only the bump, then the two fast checks:
   ```sh
   test "$(git diff --name-only HEAD^ HEAD | LC_ALL=C sort | tr '\n' ' ')" = ".claude-plugin/plugin.json CHANGELOG.md " \
     && python3 evals/lint/run_lint.py >/dev/null && python3 tools/ledger.py --check
   ```
   Any other file in the diff, or a red, is a stop. Green →
   `git push --no-verify -u origin release/<x.y.z>`, confirm with
   `ls-remote`, and open the PR from inside the worktree:
   ```sh
   gh pr create --base main --head release/<x.y.z> --title "release: <x.y.z> — <headline>" --body-file <scratchpad>/rel-pr.md
   ```
   PR body: one line saying what it bumps; **Carries** — one bullet per
   merged PR (`#N — <title>`); the minor/patch sentence; "After merge:
   `/release publish <this pr>`"; a `## Release note` heading saying the
   entry is in `CHANGELOG.md` § v<x.y.z> of this PR; the attribution line.

5. **Codex.** Wait for the automatic review (poll `gh pr view <n> --json
   comments` every 20 s, up to 8 minutes, for a `codex-review-state`
   comment with `"status":"completed"`). `has_any_findings:false` → done.
   Findings → fix each in the worktree, commit, push `--no-verify`, reply
   in each thread "Fixed in <short sha>" only after `gh pr view --json
   headRefOid` shows the new SHA, post `@codex review`, repeat. Do not
   argue niche edge cases on a release PR — the release PR is a bump and a
   generated file.

6. **Report**: the PR URL, the title, minor/patch, the carried PRs, Codex
   state. Stop. The maintainer merges.

## publish <n>

1. **The merge commit.**
   ```sh
   cd /Users/taiker/dev/roz-gate && git fetch -q origin
   gh pr view <n> --json state,mergeCommit,headRefName -q '"\(.state) \(.mergeCommit.oid) \(.headRefName)"'
   ```
   Not `MERGED` → report and stop. `<x.y.z>` is the branch name after
   `release/`. Check the version at the SHA:
   `git show <sha>:.claude-plugin/plugin.json | grep '"version"'`.

2. **Title and body from the merged changelog entry** — never from a
   scratch file (it may belong to another session):
   ```sh
   git show <sha>:CHANGELOG.md | python3 -c "
   import sys, re; s = sys.stdin.read()
   m = re.search(r'^## v<x\.y\.z> .*?\n(.*?)(?=^## v|\Z)', s, re.S | re.M)
   sys.stdout.write(re.sub(r'\A\s*<https?://[^>]*>\s*', '', m.group(1)).strip() + '\n')" > <scratchpad>/notes-<x.y.z>.md
   git show <sha>:CHANGELOG.md | grep -m1 '^## v<x.y.z> ' | sed -E 's/^## (v[^—]*— .*) — [0-9]{4}-[0-9]{2}-[0-9]{2}$/\1/'   # the title
   ```
   (Checked on v2.11.0: the extracted body equals the published release
   body byte for byte.)
   Open the notes file and confirm it starts with the bold runtime-impact
   line and ends with the Checks line.

3. **Publish** (the maintainer delegated publishing on 2026-10-11 — not a
   draft):
   ```sh
   gh release create v<x.y.z> --target <sha> --title "<title>" --notes-file <scratchpad>/notes-<x.y.z>.md
   git pull -q --ff-only origin main
   python3 tools/changelog.py --check          # must print "CHANGELOG.md is current"
   ```
   A stale changelog here means the published note differs from the
   pending entry: `gh release view v<x.y.z>` and report the difference;
   do not edit the file.

4. **Shipped in.** For every PR the release carried (the `Carries` list in
   the release PR body, else `git log --merges v<prev>..<sha>`), read its
   body for `Closes #N` / `Fixes #N` / `(#N)` issue references, and on
   each issue that is a real issue (not a PR):
   `gh issue comment N --body "Shipped in [v<x.y.z>](https://github.com/TaikerLiang/roz-gate/releases/tag/v<x.y.z>) (PR #M)."`
   Close it if still open and the PR body said it closes it. Skip issues
   already carrying a "Shipped in" comment.

5. **Clean up.** `git worktree remove` every worktree under the scratchpad
   whose branch is now merged; `git branch -D` those branches;
   `git push --no-verify --delete origin <branch>` for each remote branch
   still present (`git ls-remote --heads origin`). Leave worktrees of
   unmerged branches alone.

6. **Report**: the release URL, the changelog check result, the issues
   commented, what was removed. Stop.
