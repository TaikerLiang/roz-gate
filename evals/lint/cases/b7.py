"""B7 · the patrol report is one fixed table                 (defect: 1.37.0-, #124)
patrol.md §4 said "a short table … the user's queue … with links" and
nothing pinned the shape: an adopter's pass printed three key/value lines
per issue, folded seven issues into "unchanged — same as previous pass"
(patrol has no memory; the reader has no previous report), queued items
without links beside "nothing further needed", and buried a scan-to-scan
flip-flop under Details. The template is literal here, in F11's checker
and in the onboarding mock, and the cap is one number shared with F11.
"""

from lib.lintkit import must_not_match, read, src

META = {
    "id": 'B7',
    "title":
        'the patrol report is one fixed table — `\\| issue \\| state \\| this pass \\| needs you '
        '\\|`, one row per scanned issue, one clause per cell, no row citing another pass; the '
        'queue is exactly the `needs you` rows with links; `## Details` trails and never hides '
        'what needs the human',
    "tier": 'lint (defect 1.37.0-, #124)',
    "ledger": None,
}

REPORT_HEADER = "| issue | state | this pass | needs you |"
REPORT_CELL_CAP = 12
_pt = read("commands/patrol.md")
src("B7: patrol.md §4 carries the template header", "commands/patrol.md",
    "`%s`" % REPORT_HEADER)
src("B7: one row per issue the scanner listed", "commands/patrol.md",
    "one row per issue the scanner listed")
src("B7: no row cites another pass", "commands/patrol.md",
    "no row cites another pass — \"unchanged\",\n\"same as previous pass\"")
src("B7: this pass is one clause within the cap", "commands/patrol.md",
    "**one clause, at most %d words**" % REPORT_CELL_CAP)
src("B7: needs you is yes whenever the next move is a human's", "commands/patrol.md",
    "`yes` whenever the next move is a human's")
src("B7: the queue is exactly the needs-you rows", "commands/patrol.md",
    "exactly the `needs you` rows")
src("B7: a queue item carries its link", "commands/patrol.md",
    "`- #n — <verb phrase> — <link>`")
src("B7: a loop-level flag is a queue item too (codex, PR #128)", "commands/patrol.md",
    "`- loop — re-run /roz-gate:init — <why>`")
src("B7: §4 lists the `this pass` vocabulary", "commands/patrol.md",
    "`acted: <action> — <outcome>` · `queued: <action>` · `waits on you: <what>`\n"
    "  · `blocked: <the STOP comment's title>` · `locked: <phase> · <age>` ·\n"
    "  `illegal: <why>` · `shipped` · `in progress`")
src("B7: a row the pass cannot act on is illegal, needs you, queued", "commands/patrol.md",
    "is `illegal: <why>` with `needs you: yes` and a queue item")
src("B7: Details never hides what needs the human", "commands/patrol.md",
    "Nothing that\nneeds the human is ever only in Details")
must_not_match("B7: the unpinned phrasing does not return", r"A short table", _pt)
src("B7: F11's checker asserts the same header", "evals/replay/cases/F11/check.py",
    'HEADER = "%s"' % REPORT_HEADER)
src("B7: F11's checker holds the same cap", "evals/replay/cases/F11/check.py",
    "CELL_CAP = %d" % REPORT_CELL_CAP)
src("B7: F11's checker holds the same vocabulary (codex, PR #128)",
    "evals/replay/cases/F11/check.py",
    "VOCAB = (\"acted:\", \"queued:\", \"waits on you:\", \"blocked:\", \"locked:\", "
    "\"illegal:\",\n         \"shipped\", \"in progress\")")
src("B7: F11's checker admits a loop-level item (codex, PR #128)",
    "evals/replay/cases/F11/check.py", "loop_items = ")
src("B7: the onboarding mock shows the needs-you column", "docs/onboarding.html",
    "needs you</span>")
src("B7: the onboarding mock queues linked items", "docs/onboarding.html",
    "Your queue:</span>\n- #9 — answer the threads — ")
