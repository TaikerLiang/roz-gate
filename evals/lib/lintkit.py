"""The lint tier's kit — the checker and the grep-shaped helpers every case uses.

One case is one file under `evals/lint/cases/` (`b1.py`, `c19.py`, …);
`evals/lint/run_lint.py` imports them in ID order and tallies. The checks
in a case file run at import time against the shared checker `c`, so a
case reads exactly like the block it used to be — the helpers are the
same, only their home moved (issue #131: one shared file made every PR
that added a case collide at the same line).

Stdlib-only; runs on every push. `R` is the repository root, `FX` the
lint fixtures directory.
"""

import os
import re
import sys

from lib.checkkit import Checker

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FX = os.path.join(R, "evals", "lint", "fx")


class Lint(Checker):
    """The lint tier's line format: PASS/FAIL plus a summary count."""

    def ok(self, desc):
        print("PASS %s" % desc)

    def fail(self, desc, detail):
        print("FAIL %s — %s" % (desc, detail))

    def finish(self):
        print()
        print("%d passed, %d failed" % (self.passed, self.fails))
        sys.exit(0 if self.fails == 0 else 1)


c = Lint()


def read(relpath):
    with open(os.path.join(R, relpath), encoding="utf-8") as f:
        return f.read()


def fixture(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return f.read()


def dir_files(*reldirs):
    """Every `.md`, `.html` and `.json` file under the given directories —
    the three types the cases read. Anything else (a PDF dropped under
    `docs/`, an image) is skipped: `dirs_text` decodes what this yields as
    UTF-8, and one stray byte took the whole suite down (#149)."""
    for d in reldirs:
        for base, _, names in os.walk(os.path.join(R, d)):
            for n in sorted(names):
                if n.endswith((".md", ".html", ".json")):
                    yield os.path.join(base, n)


def dirs_text(*reldirs):
    out = []
    for p in dir_files(*reldirs):
        with open(p, encoding="utf-8") as f:
            out.append(f.read())
    return "\n".join(out)


def must_match(name, pattern, text):
    """The pattern (regex, MULTILINE) must occur — grep must succeed."""
    c.expect("pattern", name, re.search(pattern, text, re.M) is not None)


def must_not_match(name, pattern, text):
    """The pattern must NOT occur — the near-miss / anti-pattern layer."""
    c.expect("pattern", name, re.search(pattern, text, re.M) is None)


def src(name, relpath, literal):
    """Source conformance: the file carries the literal byte-for-byte."""
    if literal in read(relpath):
        c.passed += 1
        c.ok(name)
    else:
        c.fails += 1
        c.fail(name, "%s lacks the literal: %s" % (relpath, literal))


def section(text, start_re, end_re):
    """awk '/start/,/end/' — start line through end-marker line inclusive."""
    lines = text.splitlines()
    out, active = [], False
    for ln in lines:
        if not active and re.search(start_re, ln):
            active = True
        if active:
            out.append(ln)
            if out[:-1] and re.search(end_re, ln):
                break
    return "\n".join(out)
