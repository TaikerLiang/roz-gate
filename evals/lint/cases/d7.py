"""D7 · the fidelity dispatch reads the test port the marker names  (defect 1.39.0-, #125)
ADMC #11's contract is a test port that lives in an existing unit-test
file under src/test/…, outside acceptance_dir; rule E exempted the suite
alone, so the blind reviewer could not read the port the suite drives.
The port is declared on one fixed line of technical-spec.md, Path B
requires the line, the dispatcher copies its paths into the marker as
read= lines (and names them in the dispatch text), and the hook exempts
a read under them exactly as one under the suite — a file root itself, a
directory root's children, never a sibling or a climb out. Lint holds
every statement of the convention and the hook's predicate with and
without the root; hooks/tests prove the exemption end to end; replay D7
measures a pass. The four D2 regexes are untouched.
"""

import re

from cases.d2 import _SUITE, _TOP, _gb
from lib.lintkit import c, read, src

META = {
    "id": "D7",
}

_PRINTF7 = "printf 'issue=<n>\\nfeat=<feat-branch>\\nread=<path>\\n'"
src("D7: A3 states the test-port line", "commands/next-stage.md",
    "**The test-port line** (#125):")
src("D7: A3 names the API-contract form", "commands/next-stage.md",
    "`**Test port** — none` when the contract")
src("D7: Path B checks the line before anything else", "commands/next-stage.md",
    "grep -nE '^\\*\\*Test port\\*\\* — ' <specs_dir>/<n>/technical-spec.md")
src("D7: Path B stops on zero, two or a malformed value", "commands/next-stage.md",
    "Zero hits, two or more, or a value that is neither →\nthe STOP exit")
src("D7: B3 builds the port at the declared path", "commands/next-stage.md",
    "at\n  the path(s) `technical-spec.md`'s `**Test port**` line names")
src("D7: B5b's marker carries read= lines", "commands/next-stage.md", _PRINTF7)
src("D7: B5b says one read= line per declared path", "commands/next-stage.md",
    "one `read=<path>` line per path the `**Test port**` line\n  of `technical-spec.md` names")
src("D7: B5b names the paths on a line of the dispatch text", "commands/next-stage.md",
    "on a line of\n  its own, `Test port: <path>[, <path>]` or `Test port: none`")
src("D7: patrol's verbatim procedure carries the same marker", "commands/patrol.md", _PRINTF7)
_m7 = [set(re.findall(r"printf 'issue=[^']*'", read(_f)))
       for _f in ("commands/next-stage.md", "commands/patrol.md")]
c.expect("pattern", "D7: next-stage and patrol write the identical marker line",
         len(_m7[0]) == 1 and _m7[0] == _m7[1])
src("D7: patrol names the paths on a line of the dispatch text", "commands/patrol.md",
    "on a line of their own\n   in the dispatch text, `Test port: …`")
src("D7: the brief — the port is the reviewer's to read", "references/fidelity-brief.md",
    "the **test port** the\ndispatch names under `Test port:`")
src("D7: the brief's guard-blind sentence names the port", "references/fidelity-brief.md",
    "so is the test\nport the marker names")
src("D7: workflow § Principles states the fixed line", "references/workflow.md",
    "`**Test port** — <path>[, <path>]`")
src("D7: workflow (5q) names the port as readable", "references/workflow.md",
    "no read of `src/` outside the suite and the declared\n  test port")
src("D7: README's note states the line", "README.md",
    "`**Test port** — <path>`\n> (or `none` for an API contract)")
src("D7: README's rule row E names the port", "README.md",
    "so does the test port the marker's `read=` lines name")
src("D7: hooks/README row E names the port", "hooks/README.md",
    "so is the test port the marker's `read=` lines name")
src("D7: hooks/README's marker paragraph names read=", "hooks/README.md",
    "Its `read=<path>`\nlines (1.40.0, #125)")
src("D7: the index's rule row names the port (en)", "docs/index.html",
    "and so does the test port the marker names")
src("D7: the index's rule row names the port (zh)", "docs/index.html",
    "marker 點名的 test port 也是")
src("D7: the implementer template names the line", "templates/implementer.md",
    "`**Test port** — <path>` line")
src("D7: init's contract note names the line", "commands/init.md",
    "declared on `technical-spec.md`'s\n  `**Test port** — <path>` line")
src("D7: the hook parses read= lines", "hooks/guard_blind.py", "def marker_reads(path):")
src("D7: the hook builds the readable roots", "hooks/guard_blind.py",
    "def readable_roots(suite, reads):")
src("D7: the hook's deny message names the port", "hooks/guard_blind.py",
    "the port it names: `%s`")
_PORT7, _KIT7 = "src/test/java/acme/port/OfferPortTest.java", "src/test/java/acme/portkit"
c.expect("hook rule E (#125: the port the marker names is readable)",
         "D7 pattern: a read of the port with it as a root is NOT a read of src/",
         _gb.violation("Bash", {"command": "cat %s" % _PORT7}, None, [_PORT7], _TOP) is None
         and _gb.violation("Read", {"file_path": "%s/%s" % (_TOP, _PORT7)}, None, [_PORT7],
                           _TOP) is None
         and _gb.violation("Bash", {"command": "cat %s/Kit.java" % _KIT7}, None,
                           [_SUITE, _KIT7], _TOP) is None)
c.expect("hook rule E (#125: without the root the same read is a read)",
         "D7 pattern: the same read without the root IS a read of src/",
         _gb.violation("Bash", {"command": "cat %s" % _PORT7}, None, None, _TOP)
         == "a read of src/"
         and _gb.violation("Bash", {"command": "cat %s" % _PORT7}, None, [_SUITE], _TOP)
         == "a read of src/"
         and _gb.violation("Bash", {"command": "cat %s" % _PORT7}, None, _SUITE, _TOP)
         == "a read of src/")
c.expect("hook rule E (#125: the root exempts itself and its children only)",
         "D7 pattern: a sibling and a climb out stay reads",
         _gb.violation("Bash", {"command": "cat src/test/java/acme/port/OfferPortTestX.java"},
                       None, [_PORT7], _TOP) == "a read of src/"
         and _gb.violation("Bash", {"command": "cat %s/../../../main/java/acme/App.java"
                                    % _KIT7}, None, [_KIT7], _TOP) == "a read of src/")
c.expect("hook rule E (#125: readable_roots mirrors the suite rule)",
         "D7 pattern: no src/ segment or src itself is no root; the suite first, no repeats",
         _gb.readable_roots(_SUITE, ["tests/port.py", "src", "./%s" % _PORT7, _PORT7])
         == [_SUITE, _PORT7]
         and _gb.readable_roots(None, []) == []
         and _gb.readable_roots(None, [_KIT7]) == [_KIT7])
