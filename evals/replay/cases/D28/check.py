#!/usr/bin/env python3
# D28 · Every seat dispatch names the plugin root it reads from.
# Fixture: D3's — one inbox issue with no questions batch → patrol's async
# intake dispatches the product seat. The root the session loaded is the
# init event's roz-gate `path` (the runner's --plugin-dir copy, #359), so
# the checker needs no knowledge of where the runner put it.
# source: ledger D28 — "Pass: that dispatch's payload contains the plugin
#   root the session loaded (the init event's roz-gate path), and no Bash
#   call searches the filesystem for a plugin file" (#358: seats ran
#   `find / -name workflow.md` and read whichever copy turned up first)
# source: references/workflow.md § Seats and personas — every dispatch
#   attaches `Plugin root: <dir> — plugin paths resolve here; never search
#   for plugin files.`
# source: commands/patrol.md **Personas** — "attaching the seat's R&R row
#   and its `Plugin root: ${CLAUDE_PLUGIN_ROOT}` line"
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import replaylib as rl
from replaylib import Checker, Run

r, c = Run(), Checker()

_plugins = rl.session_plugins(os.path.join(r.dir, "transcript.jsonl")) or []
_roz = [str(p.get("path") or "").rstrip("/") for p in _plugins if p.get("name") == "roz-gate"]
if not _roz or not _roz[0]:
    rl.invalid("no roz-gate path in the init event — the root the session loaded is unknown")
ROOTS = {_roz[0], os.path.realpath(_roz[0])}

PRODUCT = [b for b in r.tool_uses(("Task", "Agent"))
           if "product" in str((b.get("input") or {}).get("subagent_type") or "")]
if not PRODUCT:
    rl.invalid("no product dispatch — the rule was never exercised")

# A search for plugin files: a finder program naming the plugin or one of
# its files. `find . -name '*.md'` over the project's own specs is not one.
FINDER = re.compile(r"(?:^|[\s;&|(`])(?:find|locate|mdfind)\s")
PLUGIN_WORD = re.compile(r"roz-gate|references|workflow\.md|-brief\.md|CLAUDE_PLUGIN_ROOT")


def payload(b):
    return " ".join(str(v) for v in (b.get("input") or {}).values())


def searches():
    return [cmd for b in r.tool_uses(("Bash",))
            for cmd in [str((b.get("input") or {}).get("command") or "")]
            if FINDER.search(cmd) and PLUGIN_WORD.search(cmd)]


c.expect("ledger D28 + workflow.md § Seats and personas",
         "the product dispatch payload names the plugin root the session loaded (%s)"
         % _roz[0],
         lambda: any(root in payload(b) for b in PRODUCT for root in ROOTS))
c.expect("ledger D28 (#358)",
         "no Bash call searches the filesystem for a plugin file",
         lambda: not searches())
c.finish()
