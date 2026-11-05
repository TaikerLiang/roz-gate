"""C26 · a pass acts on up to N issues and queues the rest with their wait   (#204, 2.9.0)
Under an hourly cadence the one-issue rule starved every gated issue
below the top priority: each pass's follow-ups outranked the issue the
human had already approved (ConsoleAPI, 2026-11-05: #29 ready-for-dev
skipped four passes). Since #204 a pass acts on up to
`patrol_issues_per_pass` in-loop issues (default 1), in priority order,
from the one scan table, each issue at most once; the exemptions stay
outside the N. A gated row the pass did not reach shows its wait —
`queued: <action> · <gate label> <age>` — from the `labeled` event the
scanner already carries in `evidence`. Every surface that states the rule
says "up to". The replay half (evals/replay/cases/C26) seeds N=2.
"""

import re

from lib.lintkit import c, read, section

META = {
    "id": "C26",   # the row lives in evals/replay/cases/C26/case.json (lint + replay)
}

_pm = read("commands/patrol.md")
_act = section(_pm, r"^## 3\. Act", r"^## 4\. ")
_rep = section(_pm, r"^## 4\. Report", r"^## 5\. ")

c.expect("pattern", "C26: patrol §3's heading says up to N loop issues per pass",
         re.search(r"^## 3\. Act — up to N loop issues per pass", _pm, re.M) is not None)
c.expect("pattern", "C26: patrol §3 names the key and its default",
         "`patrol_issues_per_pass`" in _act and "default 1" in _act)
c.expect("pattern", "C26: patrol §3 — each issue at most once per pass",
         "each issue at most once" in " ".join(_act.split()))
c.expect("pattern", "C26: patrol §3 — the N come from the one table, no re-scan",
         re.search(r"one table|the table of this pass|never re-scan", _act) is not None)
c.expect("pattern", "C26: patrol §3 — priority order is unchanged and still decides the N",
         "`/roz-gate:review-answers` > `/roz-gate:integrate` > address-review >" in _act
         and "in priority order" in _act)
c.expect("pattern", "C26: patrol §3 — the exemptions are outside the N, not 'the one-issue rule'",
         _act.count("outside the N") >= 4 and "one-issue rule" not in _act)
c.expect("pattern", "C26: patrol §4 — the queued clause carries the gate label and its age",
         "`queued: <action> · <gate label> <age>`" in _rep)
c.expect("pattern", "C26: patrol §4 — the age comes from the scanner's evidence, no new read",
         "`labeled` event" in _rep and "evidence" in _rep)
c.expect("pattern", "C26: patrol §4 — the age's unit rule is stated (h under a day, else d)",
         re.search(r"`<n>h`.*`<n>d`", _rep, re.S) is not None)
for _f, _needle in (("README.md", "up to `patrol_issues_per_pass` in-loop issues"),
                    ("references/workflow.md", "up to `patrol_issues_per_pass` in-loop issues"),
                    ("docs/protocol.md", "up to N issues per pass")):
    c.expect("pattern", "C26: %s says a pass acts on up to N, not one" % _f,
             _needle in read(_f))
_retired = ("one-issue rule", "one loop issue per pass", "acts on one in-loop issue",
            "acts on one issue per pass")
for _f in ("README.md", "commands/patrol.md", "references/workflow.md", "docs/protocol.md"):
    _t = " ".join(read(_f).split())
    c.expect("pattern", "C26: %s has retired the one-issue vocabulary" % _f,
             not any(w in _t for w in _retired))
