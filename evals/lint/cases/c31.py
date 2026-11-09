"""C31 · the next sequence is one past the highest; a branch is found, never guessed   (#135)
`1 + the Lookup count` collided on a gapped remote: `spec/paul/73/1` and
`/3` count two, so the "next" attempt was `/3` — an existing ref. The
rule is now `1 + max({seq})`, and the creator checks the expanded name
against the remote before the cut. Lookup's outcomes have names — NO_MATCH
· ONE · MULTIPLE_SEQ · MULTIPLE_SAME_SEQ · UNKNOWN — and a remote that could
not be read is *unknown*, never "no branch". Patrol's scanner no longer
matches templates by hand: the agent hands it `bin/roz-branch snapshot`'s
file and it binds through `roz-branch match`. `hooks/branch_names.py` is
the one implementation (bin/roz-branch, guard-acceptance, guard-gate,
roz-config); test_branch_names.py proves it.
"""

import re

from lib.lintkit import c, read

META = {
    "id": "C31",
    "title": "The next sequence is one past the highest; a branch is found, never guessed",
    "tier": "lint (#135)",
    "ledger": "`branch-names.md` says `1 + max({seq})`, names the five Lookup outcomes and "
              "\"unknown, never absent\"; `next-stage` A2/C2 check the expanded name before the "
              "cut; `patrol.md` hands over `roz-branch snapshot`'s file and `patrol-scan.md` binds "
              "through `roz-branch match`; `1 + the Lookup count` appears nowhere.",
}


def flat(path):
    return " ".join(read(path).split())


_bn = read("references/branch-names.md")
_pt, _sc = read("commands/patrol.md"), read("references/patrol-scan.md")
_tip = read("commands/tip.md")

c.expect("pattern", "C31: branch-names.md — the next sequence is 1 + max({seq})",
         "1 + max" in flat("references/branch-names.md"))
c.expect("pattern", "C31: branch-names.md — the five Lookup outcomes are named",
         all(o in _bn for o in ("NO_MATCH", "ONE", "MULTIPLE_SEQ", "MULTIPLE_SAME_SEQ", "UNKNOWN")))
c.expect("pattern", "C31: branch-names.md — a remote that cannot be read is unknown, never absent",
         re.search(r"unknown.{0,40}never", flat("references/branch-names.md"), re.I) is not None)
c.expect("pattern", "C31: branch-names.md — the creator checks the expanded name before the cut",
         re.search(r"(present|exists|already).{0,60}STOP", flat("references/branch-names.md"))
         is not None and "collision" in flat("references/branch-names.md").lower())
c.expect("pattern", "C31: branch-names.md — § The resolver names bin/roz-branch",
         "## The resolver" in _bn and "bin/roz-branch" in _bn)
c.expect("pattern", "C31: next-stage A2/C2 — the cut checks the expanded name against the remote",
         flat("commands/next-stage.md").count("1 + max") >= 1
         and re.search(r"expanded name.{0,80}(present|exists|already).{0,40}STOP",
                       flat("commands/next-stage.md")) is not None)
c.expect("pattern", "C31: patrol §1 — the agent runs `bin/roz-branch snapshot`, hands it over",
         "bin/roz-branch snapshot" in _pt)
c.expect("pattern", "C31: patrol §1 — a snapshot that is unknown stops the pass",
         re.search(r"status.{0,20}unknown.{0,120}STOP", flat("commands/patrol.md")) is not None)
c.expect("pattern", "C31: patrol-scan — the scanner binds through `roz-branch match`",
         "roz-branch match" in _sc)
c.expect("pattern", "C31: patrol-scan — the scanner no longer matches the template by hand",
         "matches the same way" not in _sc and "highest `{seq}` winning" not in _sc)
c.expect("pattern", "C31: patrol-scan — the one match covers ISSUE-LIST-CLOSED's close-out "
         "candidates too (codex review, PR #254)",
         re.search(r"ISSUE-LIST-CLOSED.{0,240}roz-branch match|roz-branch match.{0,400}"
                   r"ISSUE-LIST-CLOSED", flat("references/patrol-scan.md")) is not None
         and "bound from the same match" in flat("references/patrol-scan.md"))
c.expect("pattern", "C31: patrol-scan — MULTIPLE_SAME_SEQ is illegal, UNKNOWN never reaches it",
         "MULTIPLE_SAME_SEQ" in _sc and "UNKNOWN" in _sc)
c.expect("pattern", "C31: tip names the resolver as the read-only way to answer a branch question",
         "bin/roz-branch" in _tip)
_retired = ("1 + the number of branches", "1 + the lookup count", "matches the same way")
for _f in ("README.md", "commands/patrol.md", "commands/next-stage.md", "commands/tip.md",
           "references/branch-names.md", "references/patrol-scan.md", "references/workflow.md",
           "hooks/README.md"):
    c.expect("pattern", "C31: %s has retired the count rule and hand-matching" % _f,
             not any(w in flat(_f).lower() for w in _retired))
c.expect("pattern", "C31: hooks/README names the shared module",
         "hooks/branch_names.py" in read("hooks/README.md"))
