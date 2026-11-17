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
#361 (2026-11-16 sweep, C11/F3/F7): seats took the STOP for checkout and
payment code the widened spec asked issue #5 itself to build — "lacks code
the issue needs" and "which branch holds it if known" let "no branch"
pass. A dependency is code another issue delivers or another branch holds;
code the spec asks this issue to build is a scope question, never the STOP.
"""

import re

from lib.lintkit import NEXT_STAGE, c, dirs_text, read

META = {
    "id": "C29",
    "title": "A missing dependency in the base is a STOP, never an option",
    "tier": "lint (#213)",
    "ledger": "`workflow.md` states the policy and the shape (resume line: sync "
              "`<default_branch>`); `next-stage.md` and `spec-answers.md` carry the named STOP; "
              "`agents/product.md`, `agents/em.md` and the implementer dispatch say a seat "
              "reports the gap and never proposes a merge; `merge origin/master` appears in no "
              "brief or command (rule K denies the act — C28). A dependency is code another "
              "issue delivers; code the spec asks this issue to build is a scope question, "
              "never this STOP (#361).",
}



def flat(path):
    """One line, one space, lower case: a phrase may wrap or open a bullet."""
    return " ".join(read(path).split()).lower()


_wf, _ns, _sa = read("references/workflow.md"), read("commands/next-stage.md"), \
    read("commands/spec-answers.md")

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
             "the base lacks a dependency" in flat(_f) and "sync `<default_branch>`" in _t)
    c.expect("pattern", "C29: %s — the STOP's title is the command's" % _f,
             "**[%s] · blocked**" % _title in _t)
_a3 = read("references/next-stage-path-a.md")
c.expect("pattern", "C29: next-stage.md — a seat reports the gap; the command STOPs, never merges",
         "reports it" in _a3 and "never proposes a merge" in " ".join(_a3.split()))
for _f in ("agents/product.md", "agents/em.md"):
    c.expect("pattern", "C29: %s — never offers another branch's commits as an option" % _f,
             "never offer merging, rebasing onto or cherry-picking from another branch"
             in flat(_f))
_banned = re.compile(r"merge (origin/)?master\b|merge `origin/master`|merge master into", re.I)
for _f in ("agents/product.md", "agents/em.md", "agents/qa.md", "agents/reviewer.md",
           "commands/next-stage.md", "commands/spec-answers.md", "commands/integrate.md",
           "commands/review-answers.md", "commands/patrol.md", "references/workflow.md",
           "references/intake-brief.md", "references/qa-brief.md", "references/fidelity-brief.md",
           "references/commit-brief.md", "README.md") + NEXT_STAGE[1:]:
    c.expect("pattern", "C29: %s never says to merge master" % _f,
             _banned.search(read(_f)) is None)

# #361: what a dependency is — at the policy, at every site that restates it.
_wff = " ".join(_wf.split()).lower()
c.expect("pattern", "C29: workflow.md — a dependency is code another issue delivers (#361)",
         "a dependency is code another issue delivers" in _wff)
c.expect("pattern", "C29: workflow.md — the issue's own scope is a scope question, never this STOP",
         "scope question on the spec cr, never this stop" in _wff)
_a3f = " ".join(_a3.split()).lower()
c.expect("pattern", "C29: next-stage.md A3 — the spec's own code is an Open Question, not the STOP",
         "another issue delivers" in _a3f and "build is an open question, never this stop" in _a3f)
for _f in ("commands/next-stage.md", "commands/spec-answers.md", "agents/product.md",
           "agents/em.md"):
    c.expect("pattern", "C29: %s — the base lacks code another issue delivers (#361)" % _f,
             "lacks code another issue delivers" in flat(_f))
for _f in ("agents/product.md", "agents/em.md"):
    c.expect("pattern", "C29: %s — the issue's own spec is a scope question (#361)" % _f,
             "code this issue's spec builds is a scope question" in flat(_f))
_runtime = " ".join((dirs_text("agents", "commands", "references")
                     + read("templates/implementer.md")).split()).lower()
for _old in ("lacks code the issue needs", "lacks code this issue needs",
             "lacks code the spec needs", "holds it if known"):
    c.expect("pattern", "C29: no runtime prose says the retired '%s' (#361)" % _old,
             _old not in _runtime)
