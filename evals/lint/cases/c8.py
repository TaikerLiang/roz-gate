"""C8 · a merged CR closes the issue out                        (defect: 1.19.0-)
Issue #41: GitLab (and any CR against a release branch) leaves the
issue open wearing in-user-review after the merge; patrol finishes it.
"""

from lib.lintkit import c, read, section, src

META = {
    "id": 'C8',
    "title": 'A merged CR closes the issue out — the prose side',
    "tier": 'lint (defect 1.19.0-)',
    "ledger": None,
}

for _f in ("references/forge-github.md", "references/forge-gitlab.md"):
    src("C8: %s defines ISSUE-CLOSE" % _f, _f, "| ISSUE-CLOSE |")
    src("C8: %s defines ISSUE-LIST-CLOSED (the forge may have closed on merge)" % _f, _f,
        "| ISSUE-LIST-CLOSED |")
c.expect("pattern", "C8: GitHub CR-FIND returns state and url (merged? which CR?)",
         "baseRefName,state,url" in "\n".join(
             line for line in read("references/forge-github.md").splitlines()
             if "CR-FIND" in line))
src("C8: the spec CR body closes the issue", "commands/next-stage.md",
    'Stage (2) spec refinement for #<n>. For review.\nCloses #<n>"')
src("C8: the fast CR body closes the issue", "commands/next-stage.md",
    "body ending `Closes #<n>`")
_iur = "\n".join(line for line in read("references/patrol-scan.md").splitlines()
                 if line.startswith("| `status: in-user-review` |"))
c.expect("pattern", "C8: patrol's in-user-review row routes a merged CR to the close-out",
         "**merged**" in _iur and "close-out" in _iur)
_scan = section(read("references/patrol-scan.md"), r"^- \*\*Close-out scan\.\*\*",
                r"^- Skip any issue")
c.expect("pattern", "C8: the close-out scan looks for the merged CR with the all-states form",
         "all-states form" in _scan and "**merged**" in _scan)
_co = section(read("commands/patrol.md"), r"^### The close-out action",
              r"^### The address-review action")
for _nm, _lit in (("labels off", "LABEL-REMOVE every `track:` and `status:` label"),
                  ("one shipped comment", "**[patrol] · shipped**"),
                  ("issue closed", "ISSUE-CLOSE"),
                  ("never repairs another status", "illegal state")):
    c.expect("pattern", "C8: the close-out action — %s" % _nm, _lit in _co)
src("C8: close-outs are exempt from the one-issue rule like intake",
    "commands/patrol.md", "**close out every** issue whose CR is merged")
c.expect("pattern", "C8: the shipped comment precedes the label removal (resumable)",
         _co.index("ISSUE-COMMENT") < _co.index("ISSUE-CLOSE") < _co.index("LABEL-REMOVE"))
src("C8: the scan includes issues the forge already closed", "references/patrol-scan.md",
    "plus ISSUE-LIST-CLOSED per track label")
src("C8: a part-way close-out is recognized by its marker", "references/patrol-scan.md",
    "already carries a `**[patrol] · shipped**`")
