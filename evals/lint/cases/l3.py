"""L3 · every commit a command makes goes through the commit sub-agent's brief
(preventive, #67) — the five commit points used to run `git commit`
in the main agent and carry their own `--no-verify` sentence; a target
repo's pre-commit output landed in the main agent's context. The rules
live once, in references/commit-brief.md; the commands dispatch it and
push from the sha it returns.
"""

import re

from lib.lintkit import c, read, src

META = {
    "id": 'L3',
    "title": "every commit a command makes goes through the commit sub-agent's brief",
    "tier": 'lint (preventive)',
    "ledger": None,
}

_cb = read("references/commit-brief.md")
for _lit in ("No push, no rebase, no amend, no force", "**No dispatch.**", "`helper_model`",
             "retry **once**", "--no-verify", "`clean`", "`no-verify: <one\nline>`",
             "`failed: <≤20-line excerpt", "| branch | sha | hook |",
             "the main agent pushes"):
    c.expect("pattern", "L3: the brief carries: %s" % _lit.replace("\n", " "), _lit in _cb)
_commit_points = (
    ("commands/next-stage.md", "### A4. Commit + push\n"),
    ("commands/next-stage.md", "### B4. Commit + push + open both CRs"),
    ("commands/next-stage.md", "### C5. Commit + push + open the CR"),
    ("commands/spec-answers.md", "## 6. Commit the spec edits"),
    ("commands/review-answers.md", "One commit per turn"),
    ("commands/patrol.md", "2. Spec track: implementation CR threads"),
)
_BRIEF = "${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md"
for _f, _hdr in _commit_points:
    _txt = read(_f)
    _i = _txt.find(_hdr)
    _win = _txt[_i:_i + 1200] if _i >= 0 else ""
    c.expect("pattern", "L3: %s · %s dispatches the commit brief" % (_f, _hdr.strip()),
             _BRIEF in _win)
    c.expect("pattern", "L3: %s · %s pushes from the returned sha" % (_f, _hdr.strip()),
             "returned\n`sha`" in _win or "returned `sha`" in _win or "returned\nsha" in _win)
    c.expect("pattern", "L3: %s · %s dispatches on helper_model when set" % (_f, _hdr.strip()),
             "helper_model" in _win)
_no_commit = sorted(set(f for f, _ in _commit_points)
                    | {"commands/integrate.md", "commands/init.md", "commands/to-issues.md"})
for _f in _no_commit:
    _txt = read(_f)
    c.expect("pattern", "L3: %s carries no --no-verify rule of its own (the brief does)" % _f,
             "--no-verify" not in _txt)
    c.expect("pattern", "L3: %s never tells the main agent to run git commit itself" % _f,
             re.search(r"`git commit", _txt) is None)
src("L3: workflow.md's workspace paragraph names the commit sub-agent",
    "references/workflow.md", "made by the **commit sub-agent** (`references/commit-brief.md`)")
src("L3: README says the commit is a sub-agent's", "README.md",
    "made by a **commit sub-agent** (`references/commit-brief.md`)")
