#!/usr/bin/env python3
"""The file-naming convention, one predicate for two gates.

    naming.py --staged     # pre-commit: the files staged for this commit
    naming.py [paths...]   # the given paths (lint: every tracked file)

Rules (README § Repository layout):
  Python   snake_case  ^[a-z0-9_]+\\.py$      — importable
  shell    kebab-case  ^[a-z0-9-]+\\.sh$
  markdown lowercase kebab ^[a-z0-9.-]+\\.md$  — except the ecosystem caps
           (README, CHANGELOG, ROADMAP, CLAUDE, CLAUDE.local, SKILL, MEMORY,
           LICENSE) and the eval fixtures, which are DATA keyed by ledger
           case id (`F-63.md`, `b1_compound.md`): evals/**/fx/,
           evals/judgment/cases/, evals/judgment/redproof/.

Exit 0 when every name conforms; exit 1 listing each offender with the
rule it broke. Called by .githooks/pre-commit and imported by the lint
tier (so CI catches what a --no-verify commit slipped past).
"""

import os
import re
import subprocess
import sys

PY = re.compile(r"^[a-z0-9_]+\.py$")
SH = re.compile(r"^[a-z0-9-]+\.sh$")
MD = re.compile(r"^[a-z0-9.-]+\.md$")
MD_ALLOW = {"README.md", "CHANGELOG.md", "ROADMAP.md", "CLAUDE.md",
            "CLAUDE.local.md", "SKILL.md", "MEMORY.md", "LICENSE.md"}
FIXTURE_DIRS = re.compile(r"(^|/)(fx|evals/judgment/cases|evals/judgment/redproof)(/|$)")


def offence(path):
    """The rule `path` breaks, or None."""
    base = os.path.basename(path)
    if base.endswith(".py") and not PY.match(base):
        return "python files are snake_case (^[a-z0-9_]+\\.py$)"
    if base.endswith(".sh") and not SH.match(base):
        return "shell files are kebab-case (^[a-z0-9-]+\\.sh$)"
    if base.endswith(".md") and base not in MD_ALLOW and not MD.match(base) \
            and not FIXTURE_DIRS.search(path.replace(os.sep, "/")):
        return ("markdown files are lowercase-kebab (^[a-z0-9.-]+\\.md$) except "
                "README/CHANGELOG/ROADMAP/CLAUDE/SKILL and fixture data")
    return None


def check(paths):
    return [(p, offence(p)) for p in paths if offence(p)]


def main(argv):
    if argv[:1] == ["--staged"]:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=AR"],
                             capture_output=True, text=True)
        paths = out.stdout.split()
    else:
        paths = argv
    bad = check(paths)
    for p, why in bad:
        print("naming: %s — %s" % (p, why), file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
