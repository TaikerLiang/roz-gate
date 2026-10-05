---
description: Set one of your four loop keys — default_branch, inbox_label, inbox_assignee, helper_model — from a menu; the write is done by bin/roz-config, never by this prompt
argument-hint: "[key [value …]]"
---

Your four loop keys are per person, per clone, never committed
(`.claude/roz-gate.local.json`). This command is only the menu: the
reading and the writing are done by `${CLAUDE_PLUGIN_ROOT}/bin/roz-config`,
and nothing here validates, edits a file, or looks anything up on the forge.

Current values (the tool's own output, resolved with defaults):

```
!`python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config"`
```

## Values — comma-separated, because a label may contain spaces
For the inbox keys the values are **comma-separated** (`discuss, good first
issue` is two labels); split on commas, trim each, and pass **each value as
its own quoted argument** to the tool — never split on spaces.
`default_branch` and `helper_model` are one value each.

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
2. Ask **the value**: one branch name for `default_branch`; one model id for
   `helper_model`; one or more labels / logins, comma-separated, for the
   inbox keys; empty = remove the override.
3. Split on commas, quote each, run
   `python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config" <key> "<v1>" "<v2>" …` and
   print its output line verbatim. That line is the report; the next
   command run reads the new value.

Hard rules: never edit `.claude/roz-gate.local.json` or `CLAUDE.md`
yourself; never apply a gate label; never create forge labels.
