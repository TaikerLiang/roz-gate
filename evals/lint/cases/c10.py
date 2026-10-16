"""C10 · re-entering the spec stage after a closed CR is the human's door
(defect: 1.25.0-, #62) — and agents never delete or force-push a
remote branch anywhere in the prose.
"""

import re

from lib.lintkit import c, dir_files, read, section, src

META = {
    "id": 'C10',
}

_ns10 = read("commands/next-stage.md")
_a2 = section(_ns10, r"^### A2\. Branch", r"^### A3\. ")
_c2 = section(_ns10, r"^### C2\. Branch", r"^### C3\. ")
for _nm, _blk, _b in (("A2", _a2, "spec"), ("C2", _c2, "fast")):
    c.expect("pattern", "C10: %s looks the %s kind up on the remote first (1.29.0: Lookup, "
             "by template — references/branch-names.md)" % (_nm, _b),
             "**Lookup** the %s kind of #<n>" % _b in _blk
             and "git ls-remote --heads origin" in _blk)
    c.expect("pattern", "C10: %s — an open CR on the existing branch is an illegal state" % _nm,
             "**open** → illegal state, **STOP**" in _blk)
    c.expect("pattern", "C10: %s — closed CR: STOP with the delete remedy for the human" % _nm,
             "git push origin --delete <%s-branch>" % _b in _blk and "the human\nruns this" in _blk
             and "cite it" in _blk)
_prose = {f: read(f) for f in dir_files("commands", "references") if f.endswith(".md")}
_bad = [f for f, t in _prose.items()
        if re.search(r"git push[^\n`]*(--force\b|-f\b|--force-with-lease)|git branch -D", t)]
c.expect("pattern", "C10: no command or reference instructs a force-push or a remote branch -D",
         _bad == [])
_del_lines = [(f, ln) for f, t in _prose.items() for ln in t.splitlines()
              if "push origin --delete" in ln or "push --delete" in ln]
c.expect("pattern", "C10: every `push --delete` in the prose is addressed to the human",
         _del_lines != [] and all(any(w in ln for w in ("human", "yours", "the agent never"))
                                  for _, ln in _del_lines))
for _b, _base in (("spec", "<default_branch>"), ("fast", "<default_branch>"),
                  ("feat", "<spec-branch>"), ("qa", "<spec-branch>")):
    src("C10: the <%s-branch> cut uses -B (a stale local ref after a re-spec cannot block it)" % _b,
        "commands/next-stage.md",
        "roz-gate/wt/<%s-branch> -B <%s-branch> origin/%s" % (_b, _b, _base))
c.expect("pattern", "C10: no cut uses -b any more",
         not any(" -b <%s-branch>" % _b in _ns10 for _b in ("spec", "fast", "feat", "qa")))
src("C10: GitHub THREADS-LIST returns the thread's path and line", "references/forge-github.md",
    "id isResolved path line")
src("C10: GitLab THREADS-LIST names the note position", "references/forge-gitlab.md",
    "`position.new_path`")
src("C10: the forge stub serves path and line on threads", "evals/replay/forge-stub/gh",
    '"path": t.get("path"), "line": t.get("line"),')
src("C10: workflow.md states the invariant", "references/workflow.md",
    "**An agent never\ndeletes or force-pushes a remote branch**")
src("C10: workflow.md gives the three routes at (2a)", "references/workflow.md",
    "three routes, by how\nmuch changed")
src("C10: the inbox return applies from (2a) too", "references/workflow.md",
    "**returns to the inbox from (2a) or (7)**")
src("C10: spec-answers treats a human-opened thread as an amendment", "commands/spec-answers.md",
    "**an amendment request**: its **first** comment does NOT start with `**[`")
src("C10: an amendment's role comes from the document", "commands/spec-answers.md",
    "`technical-spec.md` →\n  `implementer`; `spec.md` → `product`")
src("C10: an amendment leaves a resolved A<k> entry", "commands/spec-answers.md",
    "`**[<role>] · A<k> · <2–4-word title>**`")
src("C10: the amendment reply marker", "commands/spec-answers.md",
    "`✅ [<role>] amended — <what changed>, folded into <document>.`")
