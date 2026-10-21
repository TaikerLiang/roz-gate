"""L11 · the seat pane is a mod that only watches                  (#172, 2.7.0)
A Claude Code mod (2.1.287+) draws the seats running now in a side pane,
each an animated 8-bit Roz. It recognises a seat by its default agent type
alone, so the README says a seat linked to your own agent is not shown. It
watches and nothing else: it never writes a file, runs a process, reaches
the network or a model, or refuses a spawn. Claude Code names one hooks
module per plugin, so the entry `hooks/mods.tsx` registers it. Red-proofed
by dropping its call from the entry, adding a sixth seat to the sprites,
adding a `$.process.run` to the mod, and deleting the README sentence.
"""

import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "L11",
    "title": "the seat pane is a mod that only watches: the entry module registers "
             "`seat-pane.tsx`; `seat-sprites.ts` draws exactly the five seats the personas "
             "template names, no more; the mod never writes, runs a process or denies a spawn; "
             "README says a seat linked to your own agent is not shown",
    "tier": "lint (#172, 2.7.0)",
    "ledger": None,
}


def text(relpath):
    return read(relpath) if os.path.exists(os.path.join(R, relpath)) else ""


_entry = text("hooks/mods.tsx")
c.expect("pattern", "L11: the entry module imports and calls the seat pane's register",
         "import { register as seats } from './seat-pane'" in _entry
         and "  seats(on, options)\n" in _entry)

_personas = re.findall(r"^- (\w+): \{\{PERSONA_\w+\}\}$",
                       read("templates/claude-workflow.md"), re.M)
_sprites = text("hooks/seat-sprites.ts")
_block = re.search(r"^export const SEATS[^{]*\{\n(.*?)^\}", _sprites, re.M | re.S)
_drawn = re.findall(r"^  (\w+): \[", _block.group(1), re.M) if _block else []
c.expect("pattern", "L11: seat-sprites.ts draws exactly the personas template's seats "
         "(%s vs %s)" % (", ".join(_drawn) or "none", ", ".join(_personas)),
         len(_personas) == 5 and sorted(_drawn) == sorted(_personas))

_mod = text("hooks/seat-pane.tsx")
_banned = [w for w in ("$.fs.", "$.process.", "$.http", "$.model", "$.prompt.submit", "$.tool.",
                       "$.store.set", "deny", "'tool.call'", "'tool.check'")
           if w in _mod]
c.expect("pattern", "L11: the mod never writes, runs a process, reaches the network or a "
         "model, or refuses a spawn (%s)" % (", ".join(_banned) or "none"),
         _mod != "" and not _banned)

c.expect("pattern", "L11: README says a seat linked to your own agent is not shown",
         "a seat linked to your own agent is not shown" in " ".join(read("README.md").split()))
