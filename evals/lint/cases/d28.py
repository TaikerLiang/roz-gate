"""D28 · every seat dispatch names the plugin root it reads from          (#358)
`${CLAUDE_PLUGIN_ROOT}` is expanded in a command's own text and nowhere
else: Bash never sets it, and a file read (a brief, a path file, the
adopter's CLAUDE.md pointer) keeps it literal. A seat that met it there ran
`find / -name workflow.md` and read whichever roz-gate copy turned up first
— the operator's checkout or a cached 2.7.1 plugin in 28 runs of the
2026-11-16 sweep; for an adopter with several cached versions, an older
version's rules. The dispatch convention now carries the root: § Seats and
personas defines the `Plugin root: <dir>` line (resolve here, never search),
and every command's Personas line hands it over with `${CLAUDE_PLUGIN_ROOT}`
— the one place the absolute path is in the main agent's view. The replay
half (D28's dir) watches a real dispatch payload.
"""

import glob
import os
import re

from lib.lintkit import R, c, read

META = {"id": "D28"}

WORKFLOW = "references/workflow.md"
LINE = "`Plugin root: <dir> — plugin paths resolve here; never search for plugin files.`"
HANDOVER = "its `Plugin root: ${CLAUDE_PLUGIN_ROOT}` line"


def flat(text):
    return " ".join(text.split())


_w = flat(read(WORKFLOW))
_start, _end = _w.find("**Seats and personas.**"), _w.find("## The loop")
_seats = _w[_start:_end] if 0 <= _start < _end else ""
c.expect(WORKFLOW, "D28: workflow.md has § Seats and personas before § The loop", bool(_seats))
c.expect(WORKFLOW, "D28: the seat's contract carries the `Plugin root:` line, verbatim",
         "the stage's instructions, and the line " + LINE in _seats)
c.expect(WORKFLOW, "D28: `<dir>` is the absolute path the command's ${CLAUDE_PLUGIN_ROOT} "
         "expanded to, and Bash never sets it",
         "`<dir>` being the absolute path the command's `${CLAUDE_PLUGIN_ROOT}` expanded to "
         "(Bash never sets it)" in _seats)

# Every command that dispatches seats through roz-persona hands the root
# over in that same sentence — the sentence ends at its § pointer.
_sites = []
for _path in sorted(glob.glob(os.path.join(R, "commands", "*.md"))):
    _rel = os.path.relpath(_path, R)
    _t = flat(read(_rel))
    for _m in re.finditer(r"dispatch each seat as the `agent_type` it prints", _t):
        _stop = _t.find("§ Seats and personas", _m.end())
        _sites.append(_rel)
        c.expect(_rel, "D28: the Personas line hands over %s" % HANDOVER,
                 _stop > 0 and HANDOVER in _t[_m.end():_stop])
c.expect("commands/*.md", "D28: the six dispatching commands each have a Personas line "
         "(found: %s)" % ", ".join(_sites),
         set(_sites) >= {"commands/%s.md" % n for n in (
             "integrate", "next-stage", "patrol", "review-answers", "spec-answers",
             "to-issues")})
