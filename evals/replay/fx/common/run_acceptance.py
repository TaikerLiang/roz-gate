"""Run the acceptance suite: every dir given, default tests/acceptance.
Walks subdirectories itself (plain discovery skips dirs without an
__init__.py). A test file in a package (its dir has an __init__.py) is
imported by its dotted name with the package root on sys.path, so
`from ._harness import Shop` works; a file in a plain dir is loaded under a
name derived from its path, so two scenario dirs may both hold a
`test_contract.py`. Every module stays registered for its setUpModule /
tearDownModule (codex review, PR #217). Finding no tests is a failure,
never a vacuous OK.
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
        root = os.path.abspath(d)                # the nearest non-package ancestor
        while os.path.isfile(os.path.join(root, "__init__.py")):
            root = os.path.dirname(root)
        if root not in sys.path:
            sys.path.insert(0, root)             # helpers import by name; packages by dots
        for f in tests:
            path = os.path.join(d, f)
            rel = os.path.relpath(os.path.splitext(os.path.abspath(path))[0], root)
            if os.sep in rel:                    # inside a package: a real dotted import
                mod = importlib.import_module(rel.replace(os.sep, "."))
            else:                                # a plain dir: a path-derived unique name
                name = re.sub(r"\W", "_", os.path.splitext(os.path.normpath(path))[0])
                spec = importlib.util.spec_from_file_location(name, path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[name] = mod          # stays: unittest finds setUpModule here
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
