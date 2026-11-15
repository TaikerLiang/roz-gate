"""L22 · seats resolve through one reader                               (#198)
Each command restated in prose how to read the `### Roz Gate personas`
block, and the default for a missing block ("implementer = the project's
`implementer` agent") was asserted, never checked: a project whose
implementer seat named an agent that did not exist met it only at the spawn.
`bin/roz-persona` is now the one reader. This case holds the hand-off:
- every command that dispatches a seat carries the call, and no file under
  `commands/` or `references/` carries the retired sentence;
- `references/workflow.md` states that a failed resolve or a refused spawn
  is the STOP exit;
- the tool's `SEATS` (read with `ast`) equals the personas template's five
  lines, in order — the seat set has one definition — and the tool reads
  the block through `hooks/config_block.py`;
- no code under `hooks/` or `bin/` other than the resolver and the pane's
  display table (`seat-pane.tsx`, `seat-sprites.ts` — #202, L11) names a
  `roz-gate:<seat>` agent type: nothing else maps an agent to a seat.
Red-proofed by restoring the old sentence in one command, removing the call
from one, adding a sixth seat to `SEATS`, and adding a `SEAT_OF` table to a
hook.
"""

import ast
import os
import re

from lib.lintkit import R, c, read, src

META = {
    "id": "L22",
    "title": "seats resolve through one reader",
    "tier": "lint (#198)",
    "ledger": "Every command that dispatches a seat carries the `bin/roz-persona --json` call "
              "and none carries the retired sentence (`resolves through the `### Roz Gate "
              "personas` block`); `references/workflow.md` states that a failed resolve or a "
              "refused spawn is the STOP exit; `roz-persona`'s `SEATS` equals the five lines of "
              "the personas template; no file under `hooks/` or `bin/` other than the resolver "
              "and the pane's display table maps an agent type to a seat (#198: role identity "
              "depended on the agent name that happened to run it).",
}

TOOL = "bin/roz-persona"
CALL = "python3 ${CLAUDE_PLUGIN_ROOT}/bin/roz-persona --json"
DISPATCHERS = ("next-stage", "patrol", "integrate", "spec-answers", "review-answers",
               "to-issues", "init")
RETIRED = re.compile(r"resolves? through the `### Roz Gate personas` block")
# the literals § Seats and personas must carry: the tool, both typed failures, the refused
# spawn, and where all three lead
STOP = ("`bin/roz-persona`", "`PERSONA_UNMAPPED`", "`AGENT_TYPE_UNAVAILABLE`",
        "a spawn the runtime refuses", "is the STOP exit")
DISPLAY = ("bin/roz-persona", "hooks/seat-pane.tsx", "hooks/seat-sprites.ts")
AGENT_TYPE = re.compile(r"""["'`]roz-gate:(?:product|em|implementer|qa|reviewer)["'`]""")


def flat(rel):
    return " ".join(read(rel).split())


for _cmd in DISPATCHERS:
    _rel = "commands/%s.md" % _cmd
    c.expect("pattern", "L22: %s carries the roz-persona call" % _rel, CALL in flat(_rel))

_restating = []
for _d in ("commands", "references"):
    for _base, _, _names in os.walk(os.path.join(R, _d)):
        for _n in sorted(_names):
            _rel = os.path.relpath(os.path.join(_base, _n), R)
            if _n.endswith(".md") and RETIRED.search(flat(_rel)):
                _restating.append(_rel)
c.expect("pattern", "L22: no command or reference restates the personas lookup (%s)"
         % (", ".join(_restating) or "none"), not _restating)

_para = re.search(r"\*\*Seats and personas\.\*\*.*?(?=\n\n)", read("references/workflow.md"),
                  re.S)
_para = " ".join(_para.group(0).split()) if _para else ""
c.expect("pattern", "L22: references/workflow.md § Seats and personas states the STOP exit "
         "(missing: %s)" % (", ".join(x for x in STOP if x not in _para) or "none"),
         all(x in _para for x in STOP))

_seats = None
for _node in ast.parse(read(TOOL)).body:
    if isinstance(_node, ast.Assign) and any(getattr(t, "id", "") == "SEATS"
                                             for t in _node.targets):
        _seats = list(ast.literal_eval(_node.value))
_template = re.findall(r"^- (\w+): \{\{PERSONA_\w+\}\}$",
                       read("templates/claude-workflow.md"), re.M)
c.expect("pattern", "L22: roz-persona's SEATS equals the personas template's lines (%s vs %s)"
         % (", ".join(_seats or ["none"]), ", ".join(_template)),
         len(_template) == 5 and _seats == _template)

src("L22: roz-persona reads the block through the hooks' one reader (config_block)", TOOL,
    'find_block(top, main_top, title="personas")')

_mapping = []
for _d in ("hooks", "bin"):
    for _base, _dirs, _names in os.walk(os.path.join(R, _d)):
        _dirs[:] = [x for x in _dirs if x not in ("tests", "__pycache__")]
        for _n in sorted(_names):
            _rel = os.path.relpath(os.path.join(_base, _n), R)
            if _rel in DISPLAY or _n.endswith((".md", ".json", ".pyc")):
                continue
            if AGENT_TYPE.search(read(_rel)):
                _mapping.append(_rel)
c.expect("pattern", "L22: no hook or tool but the resolver and the pane names a seat's agent "
         "type (%s)" % (", ".join(_mapping) or "none"), not _mapping)
