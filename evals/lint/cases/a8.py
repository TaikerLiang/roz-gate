"""A8 · the scan is one read-only sub-agent and the rules exist once
(defect: 1.24.0-, #59) — patrol.md used to carry §1–§2 itself and read
every channel into the main agent's context; the rules now live in the
scanner's brief and patrol acts from its table.
"""

import re

from lib.lintkit import c, read, src

META = {
    "id": 'A8',
    "title": 'The scan is one read-only sub-agent and the rules exist once',
    "tier": 'lint (defect 1.24.0-)',
    "ledger": None,
}

_pat8 = read("commands/patrol.md")
_brf = read("references/patrol-scan.md")
c.expect("pattern", "A8: patrol.md carries no classification table (the brief does)",
         "| State | Meaning |" not in _pat8 and "| State | Meaning |" in _brf)
c.expect("pattern", "A8: patrol.md runs no scan op itself",
         not re.search(r"^- ISSUE-LIST", _pat8, re.M) and "Close-out scan." not in _pat8)
src("A8: patrol dispatches the scanner with the brief", "commands/patrol.md",
    "${CLAUDE_PLUGIN_ROOT}/references/patrol-scan.md")
src("A8: patrol never re-reads the forge to confirm a row", "commands/patrol.md",
    "**Never re-read the forge to confirm a row**")
src("A8: the scanner is read-only", "references/patrol-scan.md", "## You write nothing")
for _op in ("LABEL-ADD", "ISSUE-COMMENT", "ISSUE-CLOSE", "no dispatch, no git"):
    c.expect("pattern", "A8: the brief forbids %s" % _op, _op in _brf.split("## Scan")[0])
for _col in ("`issue`", "`track`", "`status`", "`holder`", "`cr`", "`unheard`", "`verdict`",
             "`evidence`"):
    src("A8: the brief's table contract names column %s" % _col, "references/patrol-scan.md",
        "| %s |" % _col)
src("A8: patrol names the same columns", "commands/patrol.md",
    "`issue · track · status · holder · cr · unheard ·\nverdict · evidence`")
src("A8: the scanner is handed the bot logins so `holder` is humans only (codex review)",
    "commands/patrol.md", "`bot_login` list (normalized")
src("A8: the holder falls back to the author, never a bot", "references/patrol-scan.md",
    "else its `author` when that is not a bot")
src("A8: intake reads the gate holder from the row, never re-lists (F9 run-3)",
    "commands/patrol.md", "read from the table, never re-listed")
for _v in ("actionable: review-answers", "actionable: fidelity-audit", "close-out",
           "hand-off: in-user-review", "intake: questions", "waiting on user", "illegal state",
           "locked:"):
    src("A8: the verdict vocabulary carries `%s`" % _v, "references/patrol-scan.md", "`%s" % _v)
src("A8: the inbox filter lives in the brief", "references/patrol-scan.md",
    "**subject to the inbox filter**")
c.expect("pattern", "A8: the brief's fast-track row hands off instead of writing (codex review)",
         "LABEL-ADD `status: in-user-review`" not in _brf
         and "verdict `hand-off: in-user-review`" in _brf)
src("A8: patrol applies the hand-off label for every hand-off row", "commands/patrol.md",
    "verdict `hand-off: in-user-review`")
c.expect("pattern", "A8: the scanner dispatches nothing (depth stays 1)",
         "it\ndispatches nothing itself" in _pat8 or "dispatches nothing itself" in _pat8)
