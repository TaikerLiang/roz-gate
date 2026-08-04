---
description: Retire the Roz Gate from the current repo — verify the loop is quiet, remove the scaffolding init installed, keep every work product; run this in each project BEFORE /plugin uninstall
---

Retire the Roz Gate from the current repository — the inverse of
`/roz-gate:init`. Interactive, like init: always run by the user, and no
existing file is edited or deleted without showing the change first.
**Scaffolding goes, work products stay.** Follow these steps; do nothing
beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (a legacy
`### Gated Loop config` block counts), then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the CAPITALIZED-OPs.
No config block → still proceed: steps 2–3 clean whatever is present.

## 1. Pre-flight: the loop must be quiet

- ISSUE-LIST: any **open** issue carrying a `track:` or `status:` label →
  stop and list them. The user finishes them through the loop, or strips the
  labels to declare them abandoned. Label-less open issues (the inbox) are
  plain issues — they stay and don't block retirement.
- CR-FIND for open CRs on `spec/*`, `feat/*`, `qa/*`, `fast/*` branches →
  stop and list them; merge or close first.

Retirement happens at a quiet point, never mid-flight.

## 2. Remove the scaffolding

Each with the change shown first:
- **CLAUDE.md**: delete the whole `## Development Workflow (Roz Gate)`
  section (or the legacy `## Development Workflow (Gated Loop)` one) —
  heading, pointer, config block. Touch nothing else in the file.
- **`.claude/agents/implementer.md`**: it carries hand-tuned stack knowledge —
  confirm before deleting; the user may keep it as a plain project agent.
- **Idea issue template** at the adapter's ISSUE-TEMPLATE-PATH: delete if it
  is the plugin's template (matches `templates/idea.md` in shape); leave a
  user-customized one and say so.

## 3. Labels — kept by default

Deleting a forge label erases it from **closed** issues too — that history
("this shipped through the spec track") is the project's, not the plugin's.
Default: keep all `track:`/`status:` labels and say they were kept. Only on
the user's explicit request: LABEL-DELETE each of the scheme's labels, after
repeating the history warning once.

## 4. What stays — always

`<specs_dir>` contents (spec.md, technical-spec.md), the acceptance suite in
`<acceptance_dir>`, and all issue/CR history. These are work products — from
today they are ordinary project assets. Never delete them.

## 5. Report

What was removed, what was kept, and the closing reminder: repeat
`/roz-gate:uninit` in every other adopted project **first** — then, when all
are clean, run `/plugin uninstall roz-gate` (a plugin command cannot
uninstall its own plugin; uninstalling first deletes this command with it).
