---
description: Set one of your seven loop keys — default_branch, inbox_label, inbox_assignee, helper_model, branch_user, branch_template, worktree_copy — from a menu; the write is done by bin/roz-config, never by this prompt
argument-hint: "[key [value …]]"
---

Your seven loop keys are per person, per clone, never committed
(`.claude/roz-gate.local.json`). This command is only the menu: the
reading and the writing are done by `${CLAUDE_PLUGIN_ROOT}/bin/roz-config`,
and nothing here validates, edits a file, or looks anything up on the forge.

Where this plugin's mod loads (Claude Code 2.1.287 or later), the mod
`hooks/config-menu.tsx` answers this command itself, with no model turn,
and this prompt never runs; it is the fallback where the mod does not load.

Current values (the tool's own output, resolved with defaults):

```
!`python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config"`
```

## Values — comma-separated, because a label may contain spaces
For the inbox keys and `worktree_copy` the values are **comma-separated**
(`discuss, good first issue` is two labels); split on commas, trim each,
and pass **each value as its own quoted argument** to the tool —
never split on spaces.
`default_branch`, `helper_model`, `branch_user` and `branch_template` are one
value each.

## With arguments — no menu
`/roz-gate:config <key> [values]` → split as above and run
`python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config" <key> "<v1>" "<v2>" …`; print
its output line. A key with no value removes the override (back to the
default). An unknown key is the tool's error to print.

## Without arguments — the menu
1. Ask **which key**, as a single choice (AskUserQuestion when available,
   a numbered list otherwise), each option showing the current value from
   the block above:
   - `default_branch` — the loop's base; default = the remote's HEAD branch
   - `inbox_label` — inbox filter: any of these labels; default = no filter
   - `inbox_assignee` — inbox filter: any of these logins; default = no filter
   - `helper_model` — the model patrol's scanner and every command's commit
     sub-agent run on; default = the runtime's (seats are never configured)
   - `branch_user` — the `{user}` slot of your `branch_template`; default =
     your forge login
   - `branch_template` — your branch names, one template over `{kind}`,
     `{type}`, `{user}`, `{n}`, `{seq}` (`references/branch-names.md`);
     default = `{kind}/{n}`; the tool refuses an invalid one
   - `worktree_copy` — your gitignored files the plugin's `sync-worktree`
     hook copies from your checkout into each worktree the loop creates;
     default = `.env`; `""` = none; the tool refuses a path outside the repo
2. Ask **the value**: one branch name for `default_branch`; one model id for
   `helper_model`; one forge login for `branch_user`; one template for
   `branch_template`; one or more labels / logins, comma-separated, for the
   inbox keys; one or more repo-relative paths, comma-separated, for
   `worktree_copy` (`""` = none); empty = remove the override.
3. Split on commas, quote each, run
   `python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config" <key> "<v1>" "<v2>" …` and
   print its output line verbatim. That line is the report; the next
   command run reads the new value.

Hard rules: never edit `.claude/roz-gate.local.json`, `CLAUDE.md` or `CLAUDE.local.md`
yourself; never apply a gate label; never create forge labels.
