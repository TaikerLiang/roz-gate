"""Run the acceptance suite: every dir given, default tests/acceptance.
Walks subdirectories itself (plain discovery skips dirs without an
__init__.py) and loads every `test_*.py` under a module name derived from
its path — so two scenario dirs may both hold a `test_contract.py`, and
each module stays registered for its setUpModule / tearDownModule (codex
review, PR #217) — and finding no tests is a failure, never a vacuous OK.
The LAST line, on stdout, is one verdict line naming every failing test:
unittest's report goes to stderr, so the line survives `| tail -1`,
`2>/dev/null` and `2>&1 | tail -n`, the shapes an integrator uses to
read a long run."""
import importlib.util
import os
import re
import sys
import unittest

suite = unittest.TestSuite()
for start in sys.argv[1:] or ["tests/acceptance"]:
    for d, _, files in sorted(os.walk(start)):
        tests = sorted(f for f in files if f.startswith("test_") and f.endswith(".py"))
        if not tests:
            continue
        sys.path.insert(0, os.path.abspath(d))   # a test's sibling helpers import by name
        for f in tests:
            path = os.path.join(d, f)
            name = re.sub(r"\W", "_", os.path.splitext(os.path.normpath(path))[0])
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod       # stays: unittest finds setUpModule here
            spec.loader.exec_module(mod)
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
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
