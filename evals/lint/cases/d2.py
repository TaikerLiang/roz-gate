"""D2 · the fidelity dispatch is blind by the hook, not topology  (defect: 1.15.0-; 2.0.0, #140)
First opus baseline, 4/5: one QA child ran `cat src/app.txt` under the
fidelity dispatch — the prose "Do NOT read src/" was the only guard and a
GREEN looks identical either way. Teeth since 1.16.0: guard-blind rule E,
ON while the dispatching command's marker exists. The predicate is the D2
replay checker's three regexes; the hook carries them byte-identical, and
this case proves it by extracting each `NAME = re.compile(...)` block
from the checker and requiring the same text in the hook — then runs the
hook's own predicate against the shapes that matter.
"""

import os
import re

from lib.lintkit import R, c, read, src

META = {
    "id": 'D2',
}

import importlib.util  # noqa: E402

D2_CHECK = read("evals/replay/cases/D2/check.py")
D2_HOOK = read("hooks/guard_blind.py")
for name in ("GIT_TOUCH", "SRC_PATH", "SRC_EXCLUDED", "SRC_MENTIONED"):
    m = re.search(r"^%s = re\.compile\((?:.|\n)*?\)\n" % name, D2_CHECK, re.M)
    if not m:
        c.fails += 1
        c.fail("D2 conformance: %s block found in the replay checker" % name,
               "evals/replay/cases/D2/check.py lacks `%s = re.compile(...)`" % name)
        continue
    src("D2 conformance: guard-blind carries the checker's %s byte-for-byte" % name,
        "hooks/guard_blind.py", m.group(0))
_spec = importlib.util.spec_from_file_location("guard_blind",
                                               os.path.join(R, "hooks/guard_blind.py"))
_gb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gb)
c.expect("hook rule E (D2 run-4's exact command)",
         "D2 pattern: `… && cat src/app.txt` is a read of src/",
         _gb.violation("Bash", {"command": "git status --short && git rev-parse --abbrev-ref HEAD"
                                           " && cat src/app.txt"}) is not None)
c.expect("hook rule E", "D2 pattern: `git checkout feat/5` is a feat/ touch",
         _gb.violation("Bash", {"command": "git checkout feat/5"}) is not None)
c.expect("hook rule E", "D2 pattern: a Read of an absolute src/ path is a read",
         _gb.violation("Read", {"file_path": "/tmp/work/src/app.txt"}) is not None)
c.expect("hook rule E (exclusion is not a touch)",
         "D2 pattern: `grep -v '^src/'` and `':!src/**'` are NOT reads",
         _gb.violation("Bash", {"command": "git ls-files | grep -v '^src/'"}) is None
         and _gb.violation("Bash", {"command": "git grep -n price -- ':!src/**'"}) is None)
c.expect("hook rule E (mention is not use, third form)",
         "D2 pattern: src/ inside an echo string next to a blanked ':!src/**' is NOT a read",
         _gb.violation("Bash", {"command":
                                "git ls-files"
                                " && echo \"--- grep fixtures (tracked files, excluding src/)\""
                                " && git grep -n -E 'expires' -- ':!src/**'"
                                " ; echo \"--- diff of fix\""
                                " && git show e61367c -- tests/acceptance/"}) is None
         and _gb.violation("Bash", {"command": "# src/ is off-limits here\ncat tests/x"}) is None)
c.expect("hook rule E (echo is a command, never an argument)",
         "D2 pattern: `grep echo src/app.txt` and `printf_helper src/x` are reads",
         _gb.violation("Bash", {"command": "grep echo src/app.txt"}) is not None
         and _gb.violation("Bash", {"command": "grep -n echo src/a.py"}) is not None
         and _gb.violation("Bash", {"command": "printf_helper src/x"}) is not None)
c.expect("hook rule E (echo in command position)",
         "D2 pattern: `FOO=1 echo src/ && ls` and `ls && echo src/ | cat` are NOT reads",
         _gb.violation("Bash", {"command": "FOO=1 echo src/ && ls"}) is None
         and _gb.violation("Bash", {"command": "ls && echo src/ | cat"}) is None
         and _gb.violation("Bash", {"command": "echo \"excluding src/\" && ls tests"}) is None)
c.expect("hook rule E", "D2 pattern: a read after an echo mention is still a read",
         _gb.violation("Bash",
                       {"command": "echo \"excluding src/\" && cat src/app.txt"}) is not None)
# Issue #81 (1.29.1): the suite is not the implementation. A Maven layout's
# acceptance dir sits under src/test/…; the hook exempts it (outside the
# four regexes, which stay byte-identical above) and the prose says so.
_SUITE, _TOP = "src/test/java/acme/acceptance", "/tmp/work"
c.expect("hook rule E (the suite under src/ is not the implementation — #81)",
         "D2 pattern: a read of <acceptance_dir> under src/ is NOT a read of src/",
         _gb.violation("Bash", {"command": "cat %s/ExpiryTest.java" % _SUITE}, None, _SUITE,
                       _TOP) is None
         and _gb.violation("Read", {"file_path": "%s/%s/ExpiryTest.java" % (_TOP, _SUITE)},
                           None, _SUITE, _TOP) is None
         and _gb.violation("Grep", {"pattern": "Traces", "path": _SUITE}, None, _SUITE, _TOP)
         is None)
c.expect("hook rule E (#81: everything else under src/ stays denied)",
         "D2 pattern: src/main, a mixed command, a sibling and a climb out are reads",
         _gb.violation("Bash", {"command": "cat src/main/java/acme/App.java"}, None, _SUITE, _TOP)
         is not None
         and _gb.violation("Bash", {"command": "cat %s/T.java src/main/java/acme/App.java"
                                    % _SUITE}, None, _SUITE, _TOP) is not None
         and _gb.violation("Bash", {"command": "cat %s-old/T.java" % _SUITE}, None, _SUITE, _TOP)
         is not None
         and _gb.violation("Bash", {"command": "cat %s/../../../main/java/App.java" % _SUITE},
                           None, _SUITE, _TOP) is not None
         and _gb.violation("Read", {"file_path": "%s/%s/../../../main/java/App.java"
                                    % (_TOP, _SUITE)}, None, _SUITE, _TOP) is not None
         and _gb.violation("Bash", {"command": "cat %s/T;cat<src/main/App" % _SUITE},
                           None, _SUITE, _TOP) is not None)
c.expect("hook rule E (#81: only a suite under a src/ segment is exempt)",
         "D2 pattern: tests/acceptance, src, src/ and <module>/src yield no exemption",
         _gb.suite_under_src("tests/acceptance") is None and _gb.suite_under_src("src") is None
         and _gb.suite_under_src("src/") is None and _gb.suite_under_src(None) is None
         and _gb.suite_under_src("dlh-api/console/src") is None
         and _gb.suite_under_src("dlh-api/console/src/") is None
         and _gb.suite_under_src("src/test/java/acme/acceptance/") == _SUITE)
# #94: the first cut required `src` to be the FIRST segment; a multi-module
# Maven layout (`<module>/src/test/…`) got no exemption and the dispatch could
# not read its own suite. The deny side was never the problem: SRC_PATH matches
# `<module>/src/main/…` through the `/` before `src/`.
c.expect("hook rule E (#94: a multi-module suite is exempt)",
         "D2 pattern: <module>/src/test/… is a suite under src/, <module>/src/main/… a read",
         _gb.suite_under_src("dlh-api/console/src/test/java/acme/acceptance")
         == "dlh-api/console/src/test/java/acme/acceptance"
         and _gb.violation("Bash", {"command": "cat dlh-api/console/src/main/java/App.java"},
                           None, "dlh-api/console/src/test/java/acme/acceptance", _TOP)
         is not None)
src("D2 conformance: guard-blind reads acceptance_dir from the config block only",
    "hooks/guard_blind.py", "def load_acceptance_dir(top):")
for _f, _lit in (("references/fidelity-brief.md",
                  "every read of `src/` outside `<acceptance_dir>`"),
                 ("commands/next-stage.md", "every read of `src/` outside\n  `<acceptance_dir>`"),
                 ("commands/patrol.md", "`src/` read outside `<acceptance_dir>`"),
                 ("references/workflow.md", "no read of `src/` outside the suite"),
                 ("hooks/README.md", "outside `<acceptance_dir>`"),
                 ("README.md", "outside `<acceptance_dir>`")):
    src("D2 conformance (#81): %s qualifies the src/ rule with the suite" % _f, _f, _lit)
src("D2 conformance: the checker pairs denials by guard-blind's own message literal",
    "evals/replay/cases/D2/check.py", "Roz Gate: blocked — this is a fidelity dispatch")
src("D2 conformance: guard-blind's deny message opens with that literal",
    "hooks/guard_blind.py", "Roz Gate: blocked — this is a fidelity dispatch")
c.expect("hook rule E", "D2 pattern: qa/<n> work (tests/, spec docs) is untouched",
         _gb.violation("Bash", {"command": "cat tests/acceptance/test_expiry.py"
                                           " docs/specs/5/spec.md"}) is None
         and _gb.violation("Read",
                           {"file_path": "/tmp/work/docs/specs/5/technical-spec.md"}) is None)
src("D2 conformance: B5b states the fidelity-dispatch procedure (marker on)",
    "commands/next-stage.md", "roz-gate/fidelity-dispatch")
src("D2 conformance: patrol's address-review cites the procedure",
    "commands/patrol.md", "fidelity-dispatch procedure")
src("D2 conformance: the fidelity brief names the enforcement",
    "references/fidelity-brief.md", "guard-blind")
src("D2 conformance: hooks.json wires guard-blind on Bash|Read|Glob|Grep",
    "hooks/hooks.json", '"matcher": "Bash|Read|Glob|Grep"')
