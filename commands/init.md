---
description: One-time bootstrap of the Roz Gate in the current repo — detect the forge, create labels, write the workflow + config into CLAUDE.md, instantiate the implementer persona, add the idea issue template
---

Bootstrap the Roz Gate in the current repository. Idempotent: every step
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
- After confirming: `mkdir -p` the configured `acceptance_dir` and
  `specs_dir` — a configured path must exist from day one, not first
  materialize at stage (6).
- Contract style: does this project expose an HTTP API (contract = API doc) or
  not (contract must include a test port)? — recorded as a note in the
  implementer persona, not in the config block.
- **Agent identity** — one question: does the agent act as the human
  (`user`, default) or as its own bot identity (`bot` — GitHub App /
  GitLab project access token)? `user` → write nothing (absent keys mean
  user mode). `bot` → point the user at
  `${CLAUDE_PLUGIN_ROOT}/references/identity-github-app.md` for the
  one-time setup (credential creation is theirs, never automated here),
  then add to the config block:
  - `agent_identity: bot`
  - `bot_login: <app slug / project-bot username>` (comma-separated if
    several)
  - `operator: <the human's forge username>` — the default assignee for
    bot-created issues, nothing more; reassigning an issue moves the gate
    as usual.

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
upgrades propagate without touching CLAUDE.md. The template's
`workflow-template vN` stamp is copied verbatim — it versions the template
itself, not the plugin, so routine plugin upgrades never demand a re-init.
- If the project's CLAUDE.md has no `## Development Workflow (Roz Gate)`
  section: append `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE-workflow.md`,
  substituting the config values from step 2 into its
  `### Roz Gate config` block. Create CLAUDE.md if the project has none.
- If the section exists — including a fat pre-0.6 copy of the whole workflow,
  or a legacy section titled `## Development Workflow (Gated Loop)` with a
  `### Gated Loop config` block (the plugin's pre-1.0 name) — **replace the
  entire section with the current template**, carrying over the existing
  config values, reconciled with step 2's answers (show the diff first).

## 5. Seat the team (personas)
The five role seats are fixed — product, em, implementer, qa, reviewer; who
sits in each is per-project configuration, written into the
`### Roz Gate personas` block (step 4's template).
- Scan the project's `.claude/agents/` and the user's `~/.claude/agents/` for
  existing agents. For any whose description plausibly covers a seat, propose
  linking it — show each proposed match and why, one compact confirmation,
  not five questions.
- **Linked seat** → write the agent's dispatch name as the seat's value
  (e.g. `implementer: backend`). Never copy, move, or rename the user's file.
  Then **contract-check it**: read the linked file against the seat's R&R row
  (Owns / Never) in `${CLAUDE_PLUGIN_ROOT}/references/workflow.md`. Text that
  fights the Never column — a qa persona that reads implementation code, a
  reviewer that edits code — → show the violating lines; the user amends
  their file or falls back to the default. Never link a failing persona
  silently.
- **Unlinked seat** → the plugin default `roz-gate:<role>`. For an unlinked
  **implementer**: copy `${CLAUDE_PLUGIN_ROOT}/templates/implementer.md` to
  `.claude/agents/implementer.md` (if absent) and fill its `## Stack` section
  with the project's language/framework/store and their known anti-patterns —
  draft from the codebase, show the user, iterate once; seat value
  `implementer`.

## 6. Idea issue template
Write the async-intake capture template to the adapter's ISSUE-TEMPLATE-PATH
(`.github/ISSUE_TEMPLATE/idea.md` or `.gitlab/issue_templates/idea.md`) from
`${CLAUDE_PLUGIN_ROOT}/templates/idea.md`, if not present.

## 7. Report + first steps
Summarize what was created vs. already present. Then print the getting-started
map:
1. File a story: `/roz-gate:to-issues` in conversation, or from your phone —
   an issue with no `track:` label lands in the inbox and patrol will triage it
   in comments ((1b)).
2. You apply the gate label (`status: ready-for-spec` / `ready-for-dev`).
3. Run `/roz-gate:patrol` (manually, on a loop, or scheduled) — it advances
   whatever the labels authorize and reports what waits on you.

Nothing in this command applies a gate label, and it never edits an existing
CLAUDE.md section without showing the change first.
