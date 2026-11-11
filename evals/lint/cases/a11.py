"""A11 · a merged CR closes the issue out when the forge deleted its head  (#272)
The replay case measures the pass; these literals hold the prose it reads.
A head the forge deleted on merge is a match marked `deleted` — a CR's name,
never a branch — and a history that was not read to its end is never "no
branch": the scanner has a verdict for it and patrol a report clause.
"""

from lib.lintkit import c, read, src

META = {
    "id": 'A11',
}

src("A11: Lookup names the deleted head", "references/branch-names.md",
    "is on that list but not on the remote is a match marked **`deleted`**")
src("A11: a deleted head is a CR's name, never a branch", "references/branch-names.md",
    "it is **a CR's name, never a branch**")
src("A11: only merged CRs count (re-entry cleanup keeps working)",
    "references/branch-names.md", "only **merged** CRs count")
src("A11: an unread history never proves absence", "references/branch-names.md",
    "with **no** live match is `UNKNOWN`, never `NO_MATCH`")
src("A11: the scanner binds a deleted head for CR-FIND only", "references/patrol-scan.md",
    "bound **for CR-FIND and nothing else** (#272)")
src("A11: the scanner's rule for a branch it could not bind", "references/patrol-scan.md",
    "`waiting on: branches unknown (<reason>)`, skip classification, report it")
c.expect("pattern", "A11: `waiting on: branches unknown` is in the scanner's rule AND its "
         "verdict vocabulary",
         read("references/patrol-scan.md").count("waiting on: branches unknown (<reason>)") == 2)
src("A11: patrol's report has the clause", "commands/patrol.md",
    "· `waits on: branches unknown`")
src("A11: patrol never acts on an unbound row", "commands/patrol.md",
    "never acted on, never\n  read as \"no branch\"")
