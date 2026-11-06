"""C29 · a missing dependency in the base is a STOP, never an option   (#213)
ConsoleAPI #1: the base lacked audit logging the spec needed; the loop
asked the human whether to merge `origin/master` into the spec branch and,
told yes, brought 79 foreign commits and 104 files into the CR. #28/#29 hit
the same gap and STOPped — two answers to one situation. Since #213 there
is one: a seat that finds the base lacks code the issue needs reports it,
and the command takes the STOP exit with a named shape whose resume line
is *sync `<default_branch>`*; no seat offers merging, rebasing onto or
cherry-picking from another branch as a question option. Rule K
(`hooks/guard_gate.py`, C28) denies the merge mechanically; this lint keeps
the prose from proposing it.
"""

import re

from lib.lintkit import c, read

META = {
    "id": "C29",
    "title": "A missing dependency in the base is a STOP, never an option",
    "tier": "lint (#213)",
    "ledger": "`workflow.md` states the policy and the shape (resume line: sync "
              "`<default_branch>`); `next-stage.md` and `spec-answers.md` carry the named STOP; "
              "`agents/product.md`, `agents/em.md` and the implementer dispatch say a seat "
              "reports the gap and never proposes a merge; `merge origin/master` appears in no "
              "brief or command (rule K denies the act — C28).",
}

_wf = read("references/workflow.md")
_ns = read("commands/next-stage.md")
_sa = read("commands/spec-answers.md")
_pr = read("agents/product.md")
_em = read("agents/em.md")

c.expect("pattern",
         "C29: workflow.md — a missing dependency in the base is a STOP, never an option",
         "**A missing dependency in the base is a STOP, never an option" in _wf)
c.expect("pattern", "C29: workflow.md — the shape's resume line says sync the base",
         re.search(r"sync `<default_branch>`", _wf) is not None)
c.expect("pattern", "C29: workflow.md — after the sync the loop merges the base as always",
         "merges the base as it always does" in " ".join(_wf.split()))
for _f, _t, _title in (("commands/next-stage.md", _ns, "next-stage"),
                       ("commands/spec-answers.md", _sa, "spec-answers")):
    c.expect("pattern", "C29: %s carries the named STOP — the base lacks a dependency" % _f,
             "the base lacks a dependency" in _t and "sync `<default_branch>`" in _t)
    c.expect("pattern", "C29: %s — the STOP's title is the command's" % _f,
             "**[%s] · blocked**" % _title in _t)
c.expect("pattern", "C29: next-stage.md — a seat reports the gap; the command STOPs, never merges",
         "reports it" in _ns and "never proposes a merge" in " ".join(_ns.split()))
for _f, _t in (("agents/product.md", _pr), ("agents/em.md", _em)):
    c.expect("pattern", "C29: %s — never offers another branch's commits as an option" % _f,
             "never offer merging, rebasing onto or cherry-picking from another branch"
             in " ".join(_t.split()))
_banned = re.compile(r"merge (origin/)?master\b|merge `origin/master`|merge master into", re.I)
for _f in ("agents/product.md", "agents/em.md", "agents/qa.md", "agents/reviewer.md",
           "commands/next-stage.md", "commands/spec-answers.md", "commands/integrate.md",
           "commands/review-answers.md", "commands/patrol.md", "references/workflow.md",
           "references/intake-brief.md", "references/qa-brief.md", "references/fidelity-brief.md",
           "references/commit-brief.md", "README.md"):
    c.expect("pattern", "C29: %s never says to merge master" % _f,
             _banned.search(read(_f)) is None)
