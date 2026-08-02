---
description: One-time bootstrap of the Gated Loop in the current repo — detect the forge, create labels, write the workflow + config into CLAUDE.md, instantiate the implementer persona, add the idea issue template
---

Bootstrap the Gated Loop in the current repository. Idempotent: every step
checks what already exists and completes only the remainder. Interactive: this
command is always run by the user, in conversation — confirm each inference
before writing it.

## 1. Detect the forge
- `git remote get-url origin` → `github.com` → **github**; a GitLab host
  (gitlab.com or self-hosted) → **gitlab**. Confirm with the user; on gitlab,
  verify `glab auth status` for that host (on github, `gh auth status`).
- Load `${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` — it defines the
  label scheme and LABEL-CREATE / ISSUE-TEMPLATE-PATH used below.

## 2. Detect the stack, confirm the config
Infer from the repo (lockfiles, manifests, CI config) and confirm with the
user, one compact block, not twenty questions:
- `default_branch` (from the remote HEAD)
- `test` — command that runs the full suite (e.g. `uv run pytest`, `npm test`)
- `acceptance_dir` (default `tests/acceptance`) and `acceptance_test` — command
  for one feature's acceptance dir
- `env_sync` — dependency install/sync command (e.g. `uv sync`, `npm ci`)
- `lockfile` + `lockfile_regen` (e.g. `uv.lock` / `uv lock`;
  `package-lock.json` / `npm install --package-lock-only`)
- `specs_dir` (default `docs/specs`)
- Contract style: does this project expose an HTTP API (contract = API doc) or
  not (contract must include a test port)? — recorded as a note in the
  implementer persona, not in the config block.

## 3. Create the labels
LABEL-CREATE per the adapter's scheme:
- github: `track: spec`, `track: fast`, `status: ready-for-spec`,
  `status: ready-for-dev`, `status: in-spec-review`, `status: in-user-review`,
  `status: processing`, `status: blocked`.
- gitlab: scoped `track::spec`, `track::fast`, `status::ready-for-spec`,
  `status::ready-for-dev`, `status::in-spec-review`, `status::in-user-review`,
  `status::blocked` + the **plain** `processing` (the lock must coexist with a
  phase label — never scope it).
Skip labels that already exist.

## 4. Write the workflow pointer into CLAUDE.md
The section is a **pointer + config block only** — the workflow prose lives in
the plugin (`references/workflow.md`) and is never copied into the project, so
upgrades propagate without touching CLAUDE.md. Read the plugin version from
`${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`; it fills
`{{PLUGIN_VERSION}}` in the template's version stamp.
- If the project's CLAUDE.md has no `## Development Workflow (Gated Loop)`
  section: append `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE-workflow.md`,
  substituting the config values from step 2 into its
  `### Gated Loop config` block. Create CLAUDE.md if the project has none.
- If the section exists — including a fat pre-0.6 copy of the whole workflow —
  **replace the entire section with the current template**, carrying over the
  existing `### Gated Loop config` values, reconciled with step 2's answers
  (show the diff first).

## 5. Instantiate the implementer persona
- If `.claude/agents/implementer.md` does not exist: copy
  `${CLAUDE_PLUGIN_ROOT}/templates/implementer.md` and fill its
  `## Stack` section with the project's language/framework/store and their
  known anti-patterns — draft it from the codebase, show the user, iterate
  once. The em/product/qa/reviewer agents ship with the plugin and need no
  per-project copy.

## 6. Idea issue template
Write the async-intake capture template to the adapter's ISSUE-TEMPLATE-PATH
(`.github/ISSUE_TEMPLATE/idea.md` or `.gitlab/issue_templates/idea.md`) from
`${CLAUDE_PLUGIN_ROOT}/templates/idea.md`, if not present.

## 7. Report + first steps
Summarize what was created vs. already present. Then print the getting-started
map:
1. File a story: `/gated-loop:to-issues` in conversation, or from your phone —
   an issue with no `track:` label lands in the inbox and patrol will triage it
   in comments ((1b)).
2. You apply the gate label (`status: ready-for-spec` / `ready-for-dev`).
3. Run `/gated-loop:patrol` (manually, on a loop, or scheduled) — it advances
   whatever the labels authorize and reports what waits on you.

Nothing in this command applies a gate label, and it never edits an existing
CLAUDE.md section without showing the change first.
