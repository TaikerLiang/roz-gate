#!/usr/bin/env python3
"""Run the hook suite: one PASS/FAIL line per case, then `N passed, M failed`.

    python3 hooks/tests/run_tests.py

Plain `python3 -m unittest discover -s hooks/tests` runs the same tests with
unittest's own output.
"""

import sys
import unittest
from pathlib import Path


class Report(unittest.TextTestResult):
    passed = failed = 0

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        ok = err is None
        Report.passed += ok
        Report.failed += not ok
        self.stream.writeln("%s %s" % ("PASS" if ok else "FAIL", subtest._message))

    def addError(self, test, err):  # a crash outside any case
        super().addError(test, err)
        Report.failed += 1
        self.stream.writeln("FAIL %s: error outside a case" % test.id())


def main():
    here = Path(__file__).resolve().parent
    suite = unittest.TestLoader().discover(str(here), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=0,
                                     resultclass=Report).run(suite)
    print("\n%d passed, %d failed" % (Report.passed, Report.failed))
    return 0 if result.wasSuccessful() and Report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
