"""C9 · a command's git work lives in a worktree it removes on every exit
(defect: 1.19.0-) Issue #37: a scheduled patrol fires while the user is
mid-edit on the checkout; commands used to checkout/merge/reset there.
"""

import re

from lib.lintkit import c, read, section, src

META = {
    "id": 'C9',
    "title": "A command's git work lives in a worktree it removes on every exit",
    "tier": 'lint (defect 1.19.0-) + hook (rule E worktree forms)',
    "ledger": None,
}

_wt = "roz-gate/wt/"
_wf = read("references/workflow.md")
c.expect("pattern", "C9: workflow.md states the workspace rule (the worktree is the surface)",
         "entire\nworking surface is a linked worktree" in _wf and _wt in _wf)
c.expect("pattern", "C9: workflow.md names scheduled patrol as the motivating case",
         "scheduled patrol fires" in _wf)
c.expect("pattern", "C9: the STOP protocol's first obligation is removing the worktree",
         "(1) remove the command's worktree(s)" in _wf)
_ns = read("commands/next-stage.md")
for _nm, _s, _e in (("A2", r"^### A2\. Branch", r"^### A3\. "),
                    ("B2", r"^### B2\. ", r"^### B3\. "),
                    ("C2", r"^### C2\. Branch", r"^### C3\. ")):
    c.expect("pattern", "C9: next-stage %s cuts into a worktree under %s" % (_nm, _wt),
             "git worktree add" in section(_ns, _s, _e) and _wt in section(_ns, _s, _e))
for _nm, _s, _e in (("A6c", r"^### A6c\. ", r"^### A7\. "),
                    ("B6", r"^### B6\. ", r"^---$"),
                    ("C7", r"^### C7\. ", r"^---$")):
    c.expect("pattern", "C9: next-stage %s (Done) removes the worktree" % _nm,
             "git worktree remove --force" in section(_ns, _s, _e))
src("C9: next-stage's STOP removes every worktree the run created",
    "commands/next-stage.md", "`git worktree remove --force` every\nworktree this run created")
_ig = read("commands/integrate.md")
c.expect("pattern", "C9: integrate merges in a <spec-branch> worktree",
         "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> "
         "<spec-branch>" in _ig)
c.expect("pattern", "C9: integrate removes the worktree on green and on STOP",
         _ig.count("git worktree remove --force") >= 2)
src("C9: integrate's safety invariant: the user's checkout is untouchable",
    "commands/integrate.md", "the user's checkout is **untouchable**")
src("C9: spec-answers folds in a worktree", "commands/spec-answers.md",
    "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> <spec-branch>")
src("C9: spec-answers' STOP removes the worktree", "commands/spec-answers.md",
    "`git worktree remove --force` the `<spec-branch>` worktree")
_sa = read("commands/spec-answers.md")
c.expect("pattern", "C9: spec-answers keeps the worktree through step 7's hand-back run",
         "Keep the worktree" in section(_sa, r"^## 6\. ", r"^## 6b\. ")
         and "git worktree remove --force" in section(_sa, r"^## 7\. ", r"^## 8\. "))
for _f in ("commands/integrate.md", "commands/spec-answers.md"):
    c.expect("pattern", "C9: %s's STOP removes only a worktree this run created" % _f,
             re.search(r"[Ii]f this run created", read(_f)) is not None)
src("C9: review-answers commits in a worktree of the CR's branch", "commands/review-answers.md",
    "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> <branch>")
src("C9: patrol's address-review dispatches work in worktrees", "commands/patrol.md",
    "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<branch> <branch>")
c.expect("pattern", "C9: patrol runs no git that touches the checkout (its scan is forge "
         "calls plus one ls-remote of the remote's heads)",
         re.search(r"`git (checkout|switch|reset|stash|merge|fetch) ",
                   read("commands/patrol.md")) is None)
for _f in ("commands/next-stage.md", "commands/integrate.md", "commands/spec-answers.md",
           "commands/review-answers.md", "commands/patrol.md"):
    c.expect("pattern", "C9: %s never instructs a checkout/switch/reset/stash in the user's tree"
             % _f,
             re.search(r"git (checkout|switch|reset|stash|merge --abort)\b|^- Checkout `",
                       read(_f), re.M) is None)
src("C9: hooks/README says which git dir the marker uses", "hooks/README.md",
    "`git rev-parse --git-common-dir`")
