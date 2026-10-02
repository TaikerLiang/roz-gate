---
description: Change one Roz Gate config key in this repo's CLAUDE.md — pick the key from a menu, enter the value (empty clears it); runnable any time after init
---

Adjust the `### Roz Gate config` block in the project's CLAUDE.md, one key per
run. Interactive: always run by the user, in conversation — the key is chosen
from a menu, the value is confirmed, and the change is shown before the file
is written. Nothing else in CLAUDE.md is touched.

## 0. Load the block & forge adapter
Read the `### Roz Gate config` block (a legacy `### Gated Loop config` block
counts), then `${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the
CAPITALIZED-OPs used below (LABEL-LIST, ISSUE-LIST). Missing config → stop;
tell the user to run `/roz-gate:init`.

## 1. Pick the key
Present the keys as a single choice (the way this runtime offers options —
AskUserQuestion when available, a numbered list otherwise), each with its
current value or `(unset)`. Required keys as written by init
(`default_branch`, `test`, `acceptance_dir`, `acceptance_test`, `env_sync`,
`lockfile`, `lockfile_regen`, `specs_dir`) and the optional ones:

| key | meaning | absent means |
|---|---|---|
| `acceptance_layout` | how the acceptance suite is organized | one folder per feature |
| `trace_marker` | QA's scenario-trace marker on tests | qa declares one |
| `agent_identity` | `user` or `bot` — see README § Agent identity | `user` |
| `bot_login` | the bot's app slug / username | — |
| `operator` | default assignee for bot-created issues | — |
| `inbox_label` | **inbox filter**: only track-less open issues carrying this label are the inbox ((1b)) | every track-less open issue |
| `inbox_assignee` | **inbox filter**: only track-less open issues assigned to this forge login are the inbox | no assignee filter |
| `patrol_model` | the model patrol dispatches its seats with (`product` for intake, `implementer` for address-review) | the runtime's default |

`forge` is not offered — the forge is detected by init from the remote and
changing it mid-loop breaks every open issue.

## 2. Enter the value
Ask for the new value, showing the current one. For an **optional** key an
**empty value removes the key's line** (the key falls back to its "absent
means" column). A **required** key has no fallback — other commands read it
directly — so an empty value is refused: say so and ask again, or keep the
current value. Confirm the pair back in one line: `inbox_label: discuss` /
`inbox_label: (removed)`.

Validate only what is cheap and local:
- `agent_identity` must be `user` or `bot`; `bot` with no `bot_login`
  present → say so, write anyway (the identity reference tells the user what
  else to set up).
- `inbox_label`: if the label does not exist on the forge (LABEL-LIST), say
  so — do **not** create it; patrol will simply see an empty
  inbox until it exists.
- Paths (`acceptance_dir`, `specs_dir`) that do not exist → `mkdir -p`, as
  init does.

## 3. Write
Show the diff of the config block — the one changed, added or removed line —
then rewrite **only that block** in CLAUDE.md: the line for the key is
replaced in place, appended at the block's end when new, or deleted when
cleared. Heading, pointer prose, the personas block and everything outside
the section stay byte-identical.

## 4. Report
One line: what changed, and when it takes effect — the next command run reads
the block fresh; a running patrol is unaffected. For `inbox_label` /
`inbox_assignee`, add how many track-less open issues the new filter admits
(ISSUE-LIST; count only), so a filter that admits nothing is noticed now, not
after a silent week.

Hard rules: never apply a gate label; never create forge labels; never clear
a required key; never edit a line outside the config block.
