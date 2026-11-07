"""Run the acceptance suite: every dir given, default tests/acceptance.
Walks subdirectories itself (plain discovery skips dirs without an
__init__.py) — each directory in its own module namespace, so two
scenario dirs may both hold a `test_contract.py` (codex review, PR #217) —
and finding no tests is a failure, never a vacuous OK.
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
            before = set(sys.modules)
            suite.addTests(unittest.defaultTestLoader.discover(d, top_level_dir=d))
            # forget this dir's modules so a sibling dir's same-named file is
            # imported afresh (the loaded TestCase classes keep their objects)
            top = os.path.abspath(d) + os.sep
            for name in set(sys.modules) - before:
                path = getattr(sys.modules[name], "__file__", None) or ""
                if os.path.abspath(path).startswith(top):
                    del sys.modules[name]
if suite.countTestCases() == 0:
    sys.exit("run_acceptance: no tests found under %s" % (sys.argv[1:] or "tests/acceptance"))
result = unittest.TextTestRunner(verbosity=2).run(suite)
# a setUpClass/setUpModule failure is an _ErrorHolder with no method name:
# its id() names the fixture (codex review, PR #217) — the verdict still prints
failed = [getattr(t, "_testMethodName", None) or t.id()
          for t, _ in result.failures + result.errors]
if failed:
    print("ACCEPTANCE: RED — %d failed: %s" % (len(failed), ", ".join(failed)))
else:
    print("ACCEPTANCE: GREEN — %d passed" % result.testsRun)
sys.exit(0 if result.wasSuccessful() else 1)
