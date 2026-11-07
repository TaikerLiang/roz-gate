"""Run the acceptance suite: every dir given, default tests/acceptance.
Walks subdirectories itself (plain discovery skips dirs without an
__init__.py), and finding no tests is a failure, never a vacuous OK.
The LAST line, on stdout, is one verdict line naming every failing test:
unittest's report goes to stderr, so the line survives `| tail -1`,
`2>/dev/null` and `2>&1 | tail -n`, the shapes an integrator uses to
read a long run."""
import os
import sys
import unittest

suite = unittest.TestSuite()
for start in sys.argv[1:] or ["tests/acceptance"]:
    for d, _, files in os.walk(start):
        if any(f.startswith("test_") and f.endswith(".py") for f in files):
            suite.addTests(unittest.defaultTestLoader.discover(d, top_level_dir=d))
if suite.countTestCases() == 0:
    sys.exit("run_acceptance: no tests found under %s" % (sys.argv[1:] or "tests/acceptance"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
failed = [t._testMethodName for t, _ in result.failures + result.errors]
if failed:
    print("ACCEPTANCE: RED — %d failed: %s" % (len(failed), ", ".join(failed)))
else:
    print("ACCEPTANCE: GREEN — %d passed" % result.testsRun)
sys.exit(0 if result.wasSuccessful() else 1)
