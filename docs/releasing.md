# Releasing

How a roz-gate version ships — for the maintainer, and for an agent
preparing one. An agent may prepare every step. The two that publish —
merging the release PR, and pushing "Publish" on the release — belong to
the maintainer.

## Minor or patch

The pre-push gate demands a version bump whenever a behavior path changes
(`agents/`, `commands/`, `references/`, `templates/`). Beyond that it is a
judgment, and the release history is the guide:

- **minor** — a new hook rule (1.14.0 rule C, 1.15.0 rule D, 1.16.0 rule
  E), a new command, or a body of work worth its own line (1.17.0: D4, the
  red-proof requirement, the ledger index — no runtime change);
- **patch** — fixes and clarifications (1.16.1, 1.16.2), docs catch-up
  (1.16.3).

## Steps

1. **See what is in it.** Everything merged since the last tag, and
   whether any of it changes what a target repo runs:

   ```sh
   git fetch origin --tags
   git log --merges --format='%s' v<prev>..origin/main
   git diff --stat v<prev> origin/main -- agents commands references templates hooks scripts .claude-plugin
   ```

2. **Bump.** Branch `release/<x.y.z>` from `origin/main`, change only
   `.claude-plugin/plugin.json`'s `version`, and commit `release: <x.y.z>`
   with one paragraph saying why minor or patch. Open the PR; the
   maintainer merges it.

3. **Draft the release** against the release PR's merge commit. Take the
   SHA from the PR itself, not from `origin/main`: a local `origin/main`
   fetched before the merge still points at the pre-bump commit, and the
   tag would be created there, without the bump (codex review, PR #32).
   Check the version at that commit before drafting. The SHA must be the
   full one; the API rejects a short one.

   ```sh
   SHA=$(gh pr view <release-pr> --json mergeCommit --jq .mergeCommit.oid)
   git fetch origin && git show "$SHA:.claude-plugin/plugin.json" | grep '"version"'   # must say <x.y.z>
   gh release create v<x.y.z> --draft --target "$SHA" \
     --title "v<x.y.z> — <what it is, in one line>" --notes-file notes.md
   ```

   A draft is private and has no tag yet.

4. **Publish.** The maintainer reads the draft on GitHub and publishes
   it; publishing creates the tag.

5. **Regenerate the changelog** and open a PR with it:

   ```sh
   python3 tools/changelog.py           # rewrites CHANGELOG.md from the releases
   python3 tools/changelog.py --check   # exit 1 while CHANGELOG.md is stale
   ```

   Never edit `CHANGELOG.md` by hand. To fix a note, `gh release edit`
   it, then rerun.

## The release note

Bullets, never one dense paragraph. Every release since 1.17.0 uses this
layout; the older ones stay as written.

```markdown
**No runtime change.** <why the version moved anyway>
— or —
**Behavior:** <what changes for a target repo, in one sentence>

### Behavior
- **<subject>**: <what changed, and the measurement or defect behind it>

### Evals
- **<subject>**: …

### Hooks
### Tooling
### Docs

### Checks
Hook tests N/N · lint N/N · red-proofs N/N
```

- **The first line is the runtime impact**, bold, before any section: it
  is what a target repo's operator needs to know first.
- **Sections in this order** — Behavior, Evals, Hooks, Tooling, Docs,
  Checks — and any empty one left out.
- **Each bullet opens with a bold subject.** Where a change was promoted
  from a measurement, say which (*"D2 measured 4/5 on prose"*): the
  release is where "why does this rule exist" gets answered.
- **Code formatting for every path, command and placeholder.** GitHub
  swallows a bare `<n>` as an HTML tag: v1.17.0's first draft rendered
  `spec/<n>` as "spec/".
- **Checks** is one line: the counts from `hooks/tests/run_tests.py`,
  `evals/lint/run_lint.py` and `evals/replay/run_redproofs.py` on the
  released commit.
