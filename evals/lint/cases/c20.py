"""C20 · (4) launches only after the implementation lands on the spec branch  (#140, 2.0.0)
The parallel (3)‖(4) launch retires: QA wrote its suite against the contract
as drafted and met the contract as built only at (6), where the time saved
was spent (DLH-Console #7: four harness rounds). next-stage Path B runs
(3)+(5); Path B2 lands the review-clean implementation on <spec-branch>,
cuts <qa-branch> off the new tip and dispatches QA. Replay C20 measures the
run; this case holds every surface that states the order, and sweeps the
retired vocabulary.
"""

import os
import re

from lib.lintkit import R, c, dir_files, read, section, src

META = {
    "id": 'C20',
}

_ns = read("commands/next-stage.md")
src("C20: the route table has Path B2, read from CR state", "commands/next-stage.md",
    "| **B2 — validation (4)+(5q)** — the one route read from CR state")
src("C20: Path B is implementation + review", "commands/next-stage.md",
    "## Path B — implementation + review (3)+(5)")
src("C20: Path B2 exists", "commands/next-stage.md",
    "## Path B2 — validation (4)+(5q), once the implementation has landed")
_b2 = section(_ns, r"^## Path B2 ", r"^## Path C ")
c.expect("pattern", "C20: B2.2 merges the implementation into the spec branch and pushes",
         "git merge --no-edit origin/<feat-branch>" in _b2 and "push `<spec-branch>`" in _b2)
c.expect("pattern", "C20: B2.3 cuts the QA branch off the merged tip",
         "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<qa-branch> -B "
         "<qa-branch> origin/<spec-branch>" in _b2)
c.expect("pattern", "C20: B2.2 names the conflict as a STOP",
         "**STOP exit**: the conflicting files in the\nmust-read, nothing pushed" in _b2)
c.expect("pattern", "C20: B2 adds no gate label",
         "No gate label sits\n  here" in read("references/workflow.md")
         and "no new gate label" in read("README.md").lower()
         or "No gate label" in read("references/workflow.md"))
c.expect("pattern", "C20: Path B cuts no QA branch",
         "No `<qa-branch>` is cut here" in section(_ns, r"^### B2\. ", r"^### B3\. "))
src("C20: the scanner routes a review-clean implementation CR with no QA CR to B2",
    "references/patrol-scan.md",
    "**review-clean or merged**, and **no QA CR** → actionable → `/roz-gate:next-stage <n>`")
src("C20: the verdict vocabulary carries next-stage (qa)", "references/patrol-scan.md",
    "`actionable: next-stage (qa)`")
src("C20: patrol ranks the B2 launch", "commands/patrol.md",
    "`/roz-gate:next-stage` (`qa` — Path B2)")
src("C20: tip has the B2 row", "commands/tip.md",
    "runs Path B2: lands the implementation on `<spec-branch>` and launches (4)+(5q)")
src("C20: workflow.md states the order", "references/workflow.md",
    "**(3) Implementation — then (4) Validation**")
src("C20: workflow.md's owner table has the landing", "references/workflow.md",
    "| review-clean implementation CR → merged into `spec/{n}`, (4) launched |")
src("C20: integrate says it merges the QA branch alone in the 2.0 flow", "commands/integrate.md",
    "this step merges `<qa-branch>` alone")
src("C20: spec-answers' mid-flight re-entry knows the merged implementation CR",
    "commands/spec-answers.md",
    "an open `<feat-branch>` or `<qa-branch>` CR exists")
src("C20: README's stage table orders (3), (5), (4)", "README.md",
    "then the implementation lands on `spec/{n}` |\n| (4) Black-box QA |")
src("C20: the index's gate g2 says QA follows the landing", "docs/index.html",
    "blind QA follows once the implementation has landed")
src("C20: the quiz's stage 4 says QA starts after the landing", "docs/learn/quiz.json",
    "實作落到 spec/{n} 之後才開工")
# The retired vocabulary: none of it survives outside the history files.
RETIRED = re.compile(r"IN PARALLEL|launch together|never see each other|in parallel with the build"
                     r"|chase green|independent siblings|\(3\)\+\(4\)\+\(5\)|blind by topology"
                     r"|∥|meet for the first time|互相看不見")
for _f in sorted(dir_files("commands", "references", "templates", "agents", "docs")) + [
        os.path.join(R, "README.md")]:
    _rel = os.path.relpath(_f, R)
    if _rel.endswith("ROADMAP.md") or not _rel.endswith((".md", ".html", ".json")):
        continue
    c.expect("pattern", "C20: %s carries none of the retired parallel vocabulary" % _rel,
             RETIRED.search(read(_rel)) is None)
