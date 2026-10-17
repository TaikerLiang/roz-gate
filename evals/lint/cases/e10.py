"""E10 · the implementation CR declares its contract deviations   (#140 ruling 2, 2.0.0)
The implementer corrects technical-spec.md on its branch as it builds; QA
tests the contract as built. A correction nobody declared reaches QA, the
(5) reviewer and the fidelity dispatch as a silent edit, so the CR body
carries `## Contract deviations` and guard-gate rule H denies a CR-OPEN
whose diff touches technical-spec.md without it. The static layer holds the
section's name on every surface that reads it, the hook's predicate and
prefilter, and proves the heading pattern against positive and negative
fixtures.
"""

import re

from lib.lintkit import c, read, src

META = {
    "id": 'E10',
    "title": 'the implementation CR declares its contract deviations',
    "tier": 'hook (guard-gate rule H) + lint (#140, 2.0.0)',
    "ledger": None,
}

_SEC = "## Contract deviations"
src("E10: B4 names the section", "commands/next-stage.md",
    "The body carries a fixed section **`%s`**" % _SEC)
src("E10: B4 names the hook", "commands/next-stage.md",
    "Guard-gate rule H\n  denies a CR-OPEN whose diff touches `<specs_dir>/*/technical-spec.md`")
src("E10: B3 returns the deviations list", "commands/next-stage.md",
    "return the list of every change (clause, what changed, why) for\n  the CR's `%s` section"
    % _SEC)
src("E10: B5 attaches the deviations", "commands/next-stage.md",
    "and the CR's `%s`: the reviewer checks every deviation\n  against `spec.md`'s rules" % _SEC)
src("E10: B2.4 copies the section into the QA dispatch text", "commands/next-stage.md",
    "implementation CR's `%s` section, copied **verbatim**" % _SEC)
src("E10: the fidelity brief receives the deviations", "references/fidelity-brief.md",
    "under\nthe heading `Contract deviations:`")
src("E10: the QA brief receives the deviations", "references/qa-brief.md",
    "`Contract deviations:` (the implementation CR's section, copied verbatim by\nthe main agent")
src("E10: patrol's fidelity-audit copies the section", "commands/patrol.md",
    "the implementation CR's `%s`\n   (copied verbatim under `Contract deviations:`)" % _SEC)
src("E10: workflow's implementer row names the section", "references/workflow.md",
    "each declared under the implementation CR's `%s`" % _SEC)
src("E10: the implementer template names the section", "templates/implementer.md",
    "CR's `%s` (clause, what changed, why)" % _SEC)
src("E10: hooks/README carries row H", "hooks/README.md",
    "| **H** a CR declares its contract deviations |")
src("E10: README carries row H", "README.md", "| **H** | a CR-OPEN")
src("E10: the index carries row H", "docs/index.html", "<tr><td><b>H</b></td>")
src("E10: the hook has the predicate", "hooks/guard_gate.py", "def check_cr_open(cmd, toks):")
src("E10: the hook reads the body in rule C's shapes", "hooks/guard_gate.py",
    "def cr_body(cmd, toks, gh_pr):")
src("E10: the hook fails closed on an uncomputable diff", "hooks/guard_gate.py",
    "DIFF_FAILED_MSG = (")
src("E10: the prefilter escalates on pr create / mr create", "hooks/guard-gate.sh",
    "|pr create|mr create'")
src("E10: the hook suite carries the rule H class", "hooks/tests/test_guard_gate.py",
    "class RuleH_CrOpenDeclaresDeviations(HookTest):")
# Pattern proof: the heading regex, extracted from the hook, against fixtures.
_m = re.search(r"^DEVIATIONS_HEADING = re\.compile\((r\"[^\"]+\"), (re\.I \| re\.M)\)$",
               read("hooks/guard_gate.py"), re.M)
c.expect("pattern", "E10: the hook's heading regex is one compile() line", _m is not None)
if _m:
    _rx = re.compile(eval(_m.group(1)), re.I | re.M)   # noqa: S307 — the hook's own literal
    c.expect("pattern", "E10 pattern: the section heading matches — any level, a trailing note",
             all(_rx.search(t) for t in ("## Contract deviations\n\n- none",
                                         "Closes #5\n\n### Contract deviations — none\n",
                                         "## contract deviations\n- C2 …")))
    c.expect("pattern", "E10 pattern: the words in prose are not the section",
             not any(_rx.search(t) for t in ("Closes #5. Contract deviations: none.",
                                             "see the contract deviations below\n- C2",
                                             "## Contract\n- deviations: none")))
