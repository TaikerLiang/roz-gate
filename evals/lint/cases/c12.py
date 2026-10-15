"""C12 · A merged CR is never re-merged — integrate validates the spec tip
(defect: 1.29.1-, #77) — step 3 said "merge both"; on an issue whose
feat/qa CRs were already merged and whose spec branch had moved, that
re-merged two stale tips and stopped on a two-line conflict. The
replay case measures the model; these anchors hold the sentences it
follows, on every surface that states the rule.
"""

import re

from lib.lintkit import c, must_match, read, section, src

META = {
    "id": 'C12',
}

inflight = "\n".join(line for line in read("references/patrol-scan.md").splitlines()
                     if "no `status:`, `track: spec`" in line)
_flat = re.sub(r"\s+", " ", read("commands/integrate.md"))
_ig3 = re.sub(r"\s+", " ", section(read("commands/integrate.md"), r"^## 3\. ", r"^## 4\. "))
c.expect("pattern", "C12: integrate step 3 merges what is open, never what is merged",
         "**merge what is open, never what is merged**" in _ig3)
c.expect("pattern", "C12: integrate step 3 — both merged → nothing is merged, a re-verdict",
         "**Both merged → nothing is merged**" in _ig3 and "a **re-verdict**" in _ig3)
c.expect("pattern", "C12: integrate step 3 states the rule",
         "validates the current `<spec-branch>` tip; it never reconstructs it from stale "
         "`feat`/`qa` branch tips" in _ig3)
c.expect("pattern", "C12: integrate step 1 binds each CR's state, closed-unmerged is absent",
         "Bind each CR's state, `open` / `draft` / `merged`; a closed-unmerged CR counts as "
         "absent" in _flat)
c.expect("pattern", "C12: integrate's legal entries are no status and in-user-review",
         "`status: in-spec-review` → stop" in _flat
         and "`status: ready-for-spec` / `ready-for-dev` → stop" in _flat
         and "**`status: in-user-review`**" in _flat)
c.expect("pattern", "C12: the finalize regenerates the cards wholesale on a re-verdict",
         "On a re-verdict the cards are regenerated **wholesale**" in _flat)
c.expect("pattern", "C12: the report names what step 3 merged",
         "*re-verdict at SHA `<x>`, nothing merged" in _flat)
# codex review, PR #86: four holes a re-verdict opens in the first-pass prose.
c.expect("pattern", "C12: the worktree starts at the remote's tip (ff-only), never a stale ref",
         "`git merge --ff-only origin/<spec-branch>`" in _ig3
         and "cannot fast-forward" in _ig3)
c.expect("pattern", "C12: a re-verdict runs the full acceptance suite",
         "**On a re-verdict run the full acceptance suite**"
         in re.sub(r"\s+", " ", section(read("commands/integrate.md"), r"^## 4\. ", r"^## 5\. ")))
c.expect("pattern", "C12: after a re-verdict RED the fix rides the spec branch or a merge-back",
         "**After a re-verdict RED**" in _flat
         and "**on `<spec-branch>` in the worktree**" in _flat
         and "**merge `origin/<qa-branch>` back**" in _flat)
c.expect("pattern", "C12: the STOP exit strips the phase label the run entered from",
         "**and the phase label the run entered from**"
         in re.sub(r"\s+", " ", section(read("commands/integrate.md"), r"^## 6\. ", r"^## 7\. ")))
must_match("C12: the in-flight row reads a merged CR as present",
           r"shows as \*\*merged\*\* exists for this row", inflight)
must_match("C12: the in-flight row routes both-merged to integrate",
           r"both merged, or merged \+ open-ready, included", inflight)
c.expect("pattern", "C12: workflow.md (6) states the rule",
         "**validates the current `spec/{n}` tip and merges nothing**"
         in re.sub(r"\s+", " ", read("references/workflow.md")))
src("C12: README's (6) row states the rule", "README.md",
    "a later run validates the current spec tip and merges nothing")
src("C12: README's command row says merge what is open", "README.md",
    "merge what is open (never what is merged)")
