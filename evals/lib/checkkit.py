"""Shared check/report kit for the eval tiers — thin by design.

The lint tier's checks are grep-shaped and must not inherit replay's
Run/artifact machinery; what the tiers genuinely share is the tally, the
probe-error guard (a broken probe is a failed check, never a crash), the
citation guard, and the exit contract. Nothing else lives here.
"""

import sys


class Checker:
    """Named expectations; one line per check; exit 0 iff all held.

    `expect(source, desc, cond)`: cond may be a bool or a callable probe.
    Line format is overridable per tier (replay prints ok/FAIL with the
    source cited on failure; lint prints PASS/FAIL with a summary line).
    """

    def __init__(self):
        self.passed = 0
        self.fails = 0

    def ok(self, desc):
        print("ok   %s" % desc)

    def fail(self, desc, detail):
        print("FAIL %s  [%s]" % (desc, detail))

    def expect(self, source, desc, cond):
        if callable(cond):
            try:
                cond = bool(cond())
            except Exception as exc:  # a broken probe is a failed check
                self.fails += 1
                self.fail(desc, "probe error: %s] [source: %s" % (exc, source))
                return
        if cond:
            self.passed += 1
            self.ok(desc)
        else:
            self.fails += 1
            self.fail(desc, "source: %s" % source)

    def finish(self):
        sys.exit(0 if self.fails == 0 else 1)


def has_citation(path):
    """The blindness guard's predicate: a checker must cite the prose it
    derives from (`# source:`) or the runner refuses to run it."""
    with open(path, encoding="utf-8") as f:
        return "# source:" in f.read()
