"""L4 · branch names are bound once, never spelled           (preventive, #75)
1.29.0: the four loop branches are named by the block's
branch_template (references/branch-names.md), default `{kind}/{n}`.
A literal `spec/<n>` left in a command is a name the template cannot
rename — exactly the hardcode this replaces (62 of them in next-stage
alone). Lookup over Expand: another person's {user} and the attempt's
{seq} are not computable from the config, so an existing branch is
found on the remote, never guessed. The hooks read the same template.
"""

import os
import re

from lib.lintkit import R, c, dir_files, read, section, src

META = {
    "id": 'L4',
    "title":
        'branch names are bound once, never spelled — every command resolves `<spec-branch>` / '
        '`<feat-branch>` / `<qa-branch>` / `<fast-branch>` through '
        '`references/branch-names.md`; no literal `spec/<n>` outside it; `init` creates the '
        '`type:` labels; both adapters carry WHOAMI; the hooks read the template',
    "tier": 'lint (preventive, #75)',
    "ledger": None,
}

_bn = read("references/branch-names.md")
for _lit in ("Absent or `\"\"` → `{kind}/{n}`", "| `{kind}` |", "| `{type}` |", "| `{user}` |",
             "| `{n}` |",
             "| `{seq}` |", "qa branch → `test`", "no `type:` label → `feat`", "`branch_user`",
             "WHOAMI", "git ls-remote --heads origin", "highest `{seq}`",
             "git push origin --delete <branch>",
             "contains `{n}` and at least one of `{kind}`\n/ `{type}`",
             "the human runs this; the agent\n    never does"):
    c.expect("pattern", "L4: branch-names.md carries: %s" % _lit.replace("\n", " "), _lit in _bn)
_LIT = re.compile(r"\b(spec|feat|qa|fast)/<n>")
for _f in sorted(dir_files("commands", "references")):
    _rel = os.path.relpath(_f, R)
    if not _rel.endswith(".md") or _rel.endswith("branch-names.md"):
        continue
    c.expect("pattern", "L4: %s spells no branch name (bound names only)" % _rel,
             _LIT.search(read(_rel)) is None)
_readers = ("commands/patrol.md", "commands/next-stage.md", "commands/integrate.md",
            "commands/spec-answers.md", "commands/review-answers.md")
for _f in _readers:
    src("L4: %s binds the names through branch-names.md" % _f, _f, "references/branch-names.md")
_ns4 = read("commands/next-stage.md")
for _nm, _s, _e in (("A2", r"^### A2\. Branch", r"^### A3\. "),
                    ("C2", r"^### C2\. Branch", r"^### C3\. ")):
    _blk = section(_ns4, _s, _e)
    c.expect("pattern",
             "L4: %s re-enters by the next sequence when the template carries {seq}" % _nm,
             "It carries **`{seq}`**" in _blk and "next sequence" in _blk)
    c.expect("pattern", "L4: %s STOPs with the delete remedy only without {seq}" % _nm,
             "It carries **no\n`{seq}`**" in _blk and "git push origin --delete" in _blk)
src("L4: B2 binds feat and qa by Lookup, else Expand", "commands/next-stage.md",
    "Lookup — a previous B run's\nbranch is reused — else Expand")
src("L4: the dispatch marker carries the bound implementation branch", "commands/next-stage.md",
    "printf 'issue=<n>\\nfeat=<feat-branch>\\nread=<path>\\nseat=<seat>\\n'")
src("L4: patrol's fidelity dispatch names the same marker line", "commands/patrol.md",
    "feat=<feat-branch>")
src("L4: patrol hands the scanner the remote's heads (the scanner may not run git — codex, PR #82)",
    "commands/patrol.md", "`git ls-remote --heads origin`, run by you")
src("L4: the scanner binds names by Lookup over the handed list, never a git call",
    "references/patrol-scan.md", "never by a git call of your own")
src("L4: Lookup is one ls-remote, no fetch", "references/branch-names.md",
    "`git ls-remote --heads origin` (a query of the remote — no fetch, no local\nref touched)")
src("L4: init creates the three type labels", "commands/init.md",
    "`type: feat`, `type: fix`, `type: chore`")
src("L4: init never applies a type label", "commands/init.md",
    "no command ever\napplies, removes or validates one")
src("L4: init writes no branch_template — it is the developer's local key (#165)",
    "commands/init.md", "- (not in the block) `branch_template` — your branch-naming convention")
for _f in ("references/forge-github.md", "references/forge-gitlab.md"):
    src("L4: %s carries WHOAMI" % _f, _f, "| WHOAMI |")
src("L4: guard-blind reads the marker's feat= line", "hooks/guard_blind.py",
    'line.startswith("feat=")')
src("L4: guard-acceptance renders the template for the spec kind", "hooks/guard_acceptance.py",
    "def spec_branch_re(template):")
src("L4: guard-acceptance's prefilter escalates every branch under a local template",
    "hooks/guard-acceptance.sh", "grep -qs '\"branch_template\" *: *\"[^\"]'")
src("L4: guard-acceptance reads the template from the local file, here or in the main "
    "checkout (#165)", "hooks/guard_acceptance.py", "for root in (top, main_checkout()):")
src("L4: hooks/README's rule E names the marker's ref", "hooks/README.md", "marker's `feat=` line")
src("L4: README sets the template with /roz-gate:config", "README.md",
    "/roz-gate:config branch_template ")
c.expect("pattern", "L4: README's block example carries no branch_template line (#165)",
         "- branch_template:" not in read("README.md"))
src("L4: branch-names.md: the template is a local key, yours per clone (#165)",
    "references/branch-names.md", "`branch_template` is a **local key — yours, per clone**")
for _f in ("commands/next-stage.md", "commands/integrate.md", "commands/spec-answers.md",
           "commands/review-answers.md", "commands/patrol.md", "commands/tip.md"):
    _s = re.sub(r"\s+", " ", read(_f))
    c.expect("pattern", "L4: %s binds names from the local key, never the block's (#165)" % _f,
             "the local key `branch_template`" in _s and "block's `branch_template`" not in _s)
    c.expect("pattern", "L4: %s lists branch_template among the local keys (#165)" % _f,
             re.search(r"`branch_user`, `branch_template`(,| are per person)", _s) is not None)
src("L4: workflow.md states the names are the template's", "references/workflow.md",
    "**The branch names.**")
src("L4: the onboarding builder offers branch_template", "docs/onboarding.html", "branch_template")
_ob = read("docs/onboarding.html")
_loc = _ob[_ob.find("const LOCAL = ["):_ob.find("];", _ob.find("const LOCAL = ["))]
_opt = _ob[_ob.find("const OPT = ["):_ob.find("];", _ob.find("const OPT = ["))]
c.expect("pattern", "L4: the onboarding builder renders branch_template as a /roz-gate:config "
         "line, not a block line (#165)",
         "'branch_template'" in _loc and "'branch_template'" not in _opt)
