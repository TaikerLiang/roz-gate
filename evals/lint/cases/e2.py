"""E2 · a question left behind in the source document        (defect: 1.14.2-)
The first opus baseline: A6 said "relocate it verbatim", 5/5 runs copied;
the prose was made explicit ("move … delete it from the source document"),
5/5 runs still left the section behind (F3 the same). Teeth since 1.15.0:
guard-gate rule D denies the commit. Three holders of ONE predicate — the
hook, the E2 replay checker, and this proof — kept byte-identical here;
then the repo's own specs tree is swept as the push-time backstop
(web-UI edits, --no-verify, a hook-less client — a client-side hook binds
this agent, this lint binds this push; neither binds the repository).
Heading-only by design: "TBD"/"open:" items are ordinary prose too often
to deny on (see the e2_clean fixture); the section heading is the shape
every observed miss took.
"""

import os
import re

from lib.lintkit import R, c, fixture, must_match, must_not_match, read, src

META = {
    "id": 'E2',
}

OPEN_Q = "^#+ .*open questions"
must_match("E2 pattern: an open-questions section heading is detected",
           "(?i)" + OPEN_Q, fixture("e2_section.md"))
must_match("E2 pattern: a heading kept as a pointer-only section still counts",
           "(?i)" + OPEN_Q, fixture("e2_pointer_section.md"))
must_not_match("E2 pattern: a pointer line under another heading / prose mention NOT flagged",
               "(?i)" + OPEN_Q, fixture("e2_clean.md"))
src("E2 conformance: guard-gate rule D carries the predicate literal",
    "hooks/guard_gate.py", OPEN_Q)
src("E2 conformance: the E2 replay checker carries the same literal",
    "evals/replay/cases/E2/check.py", OPEN_Q)
src("E2 conformance: A6 prose states the move AND names the enforcement",
    "commands/next-stage.md", "delete it from the source document")
src("E2 conformance: A6 prose names guard-gate as the enforcement",
    "commands/next-stage.md", "guard-gate denies the commit")


def specs_dir():
    """This repo's specs_dir: from its CLAUDE.md config block, else the
    documented default — the same resolution the hook applies."""
    try:
        text = read("CLAUDE.md")
    except OSError:
        return "docs/specs"
    m = re.search(r"^-\s*specs_dir:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip("`") if m else "docs/specs"


left_behind = []
for base, _, names in os.walk(os.path.join(R, specs_dir())):
    if "technical-spec.md" in names:
        with open(os.path.join(base, "technical-spec.md"), encoding="utf-8") as f:
            if re.search("(?i)" + OPEN_Q, f.read(), re.M):
                left_behind.append(os.path.relpath(base, R))
c.expect("hook rule D, push-time backstop",
         "E2 backstop: no technical-spec.md under %s carries an open-questions "
         "section%s" % (specs_dir(), "" if not left_behind
                        else " — left behind in: " + ", ".join(left_behind)),
         not left_behind)
