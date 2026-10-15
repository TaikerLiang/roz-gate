"""C15 · the default branch is read from the remote at every git site
(defect: 1.31.0-, #90)
integrate 5.2 merged the local `<default_branch>` and the fast-track
reviewer diffed against it. The loop never moves that ref, and in a
dedicated clone (#76) nobody does: a green verdict merged an
ever-older trunk, and the reviewer saw the trunk's own commits as the
change. Every replay seed has local = remote main, so only the source
shows it — and C7's anchors pinned the local-ref spelling.
"""

import os
import re

from lib.lintkit import R, c, dir_files, must_not_match, read, section, src

META = {
    "id": 'C15',
    "title": 'The default branch is read from the remote at every git site',
    "tier": 'lint (defect 1.31.0-, #90)',
    "ledger":
        '"integrate 5.2 merges `origin/<default_branch>` and next-stage C6 diffs '
        '`origin/<default_branch>...<fast-branch>`; no command spells the bare `git merge '
        '--no-edit <default_branch>` or `git diff <default_branch>...`; workflow.md states the '
        'rule." (the loop never moves the local ref — in a dedicated clone, nobody does — so a '
        "green verdict merged an ever-older trunk and the fast reviewer diffed the trunk's own "
        'commits as the change; every replay seed has local = remote main, so only the source '
        'shows it — issue #90)',
}

_ig = read("commands/integrate.md")
_ns = read("commands/next-stage.md")
_ig5 = re.sub(r"\s+", " ", section(_ig, r"^## 5\. ", r"^## 6\. "))
_c6 = re.sub(r"\s+", " ", section(_ns, r"^### C6\. ", r"^### C7\. "))
# codex review, PR #91: fix rounds run long — the step-3 fetch is stale by then.
c.expect("pattern", "C15: integrate 5.2 fetches, merges the remote tip, and says why",
         "`git fetch`, then `git merge --no-edit origin/<default_branch>` — the remote's tip as "
         "of now, not as of step 3" in _ig5
         and "this command never moves the local ref, and in a dedicated clone nobody does"
         in _ig5)
c.expect("pattern", "C15: the fast-track reviewer diffs against the remote tip",
         "git diff origin/<default_branch>...<fast-branch>" in _c6)
for _f in sorted(dir_files("commands")):
    must_not_match("C15: %s never merges or diffs the local default branch"
                   % os.path.relpath(_f, R),
                   r"merge --no-edit <default_branch>|(?<!origin/)<default_branch>\.\.\.",
                   read(_f))
src("C15: the workflow states the rule once", "references/workflow.md",
    "A command's git reference to it is always `origin/<default_branch>`")
