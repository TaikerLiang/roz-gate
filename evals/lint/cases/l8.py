"""L8 · /roz-gate:config is answered by a mod that only reads and runs
bin/roz-config, and the prompt stays as the fallback          (#164, 2.3.0)
A Claude Code mod (2.1.287+) takes over the markdown command through
`command.run`, so a config change costs no model turn. The mod is a menu
and nothing else: the tool stays the only writer, so the mod never writes a
file, never reaches the network or a model, never submits a prompt and
never hooks a tool call. Where mods do not load, `commands/config.md`
runs as before — deleting it would leave those sessions with no command.
Red-proofed by adding a `$.fs.write`, matching `config` instead of
`roz-gate:config`, and deleting `commands/config.md`.
"""

import json
import os
import re

from lib.lintkit import R, c, read, src

META = {
    "id": 'L8',
    "title":
        '`/roz-gate:config` is answered by a mod that only reads and runs `bin/roz-config`; '
        '`commands/config.md` stays as the fallback where mods do not load',
    "tier": 'lint (#164, 2.3.0)',
    "ledger": None,
}

_MOD = "hooks/config-menu.tsx"
_mods = json.loads(read("hooks/hooks.json")).get("modules", [])
c.expect("pattern", "L8: hooks/hooks.json names the mod module",
         _mods == ["./config-menu.tsx"])
c.expect("pattern", "L8: hooks/hooks.json keeps the guard hooks beside it",
         "PreToolUse" in json.loads(read("hooks/hooks.json")).get("hooks", {}))
_src = read(_MOD) if os.path.exists(os.path.join(R, _MOD)) else ""
c.expect("pattern", "L8: the mod answers command.run for roz-gate:config, and only it",
         re.findall(r"on\('command\.run', \{ command: ([A-Z_]+|'[^']*') \}", _src) == ["COMMAND"]
         and "const COMMAND = 'roz-gate:config'" in _src)
c.expect("pattern", "L8: the mod runs bin/roz-config through $.process.run, with python3",
         "$.process.run(['python3', path, ...args])" in _src
         and "const path = $.plugin.root + '/bin/roz-config'" in _src)
c.expect("pattern", "L8: the mod runs nothing but the tool (one $.process call)",
         len(re.findall(r"\$\.process\.", _src)) == 1)
_banned = [w for w in ("$.fs.write", "$.http", "$.model", "$.prompt.submit", "$.tool.",
                       "$.store.set", "'tool.call'", "'tool.check'", "'prompt.submit'")
           if w in _src]
c.expect("pattern", "L8: the mod never writes a file, reaches the network or a model, "
         "submits a prompt or hooks a tool call (%s)" % (", ".join(_banned) or "none"),
         _src != "" and not _banned)
c.expect("pattern", "L8: commands/config.md stays as the fallback",
         os.path.exists(os.path.join(R, "commands/config.md")))
if os.path.exists(os.path.join(R, "commands/config.md")):
    src("L8: the fallback prompt names the mod that answers first", "commands/config.md",
        "`hooks/config-menu.tsx` answers this command itself")
    src("L8: the fallback prompt still runs the tool", "commands/config.md",
        'python3 "${CLAUDE_PLUGIN_ROOT}/bin/roz-config"')
