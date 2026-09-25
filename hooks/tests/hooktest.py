"""HookTest — the shared base class for the hook suite.

Every case pipes a synthetic PreToolUse payload into a guard's `.sh` shim --
the real entry point, prefilter included -- and reads back the exit code and
stderr. Never import the guards' Python directly: a rule the prefilter never
escalates would then pass here and never run in production.

Stdlib only, Python 3.9-compatible: pre-push and CI run this on the plain
`python3` the hooks themselves run on.
"""

import json
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

TESTS = Path(__file__).resolve().parent
HOOKS = TESTS.parent
FX = TESTS / "fx"


def config_block(**keys):
    """A CLAUDE.md carrying a Roz Gate config block."""
    lines = "".join("- %s: %s\n" % kv for kv in keys.items())
    return "### Roz Gate config\n\n" + lines


class Result:
    def __init__(self, rc, stderr):
        self.rc, self.stderr = rc, stderr


class HookTest(unittest.TestCase):
    guard = None  # "guard-gate", "guard-blind" or "guard-acceptance"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.stub_log = self.tmp / "stub.log"
        # tests/bin/gh and tests/bin/glab replace the forge CLIs: they log each
        # call to STUB_LOG and print the fixture the env var points at.
        self.env = dict(
            os.environ,
            PATH="%s:%s" % (TESTS / "bin", os.environ["PATH"]),
            STUB_LOG=str(self.stub_log),
            GH_FIXTURE=str(FX / "gh_no_trigger.json"),
            GLAB_ISSUE_FIXTURE=str(FX / "glab_issue_ok.json"),
            GLAB_NOTES_FIXTURE=str(FX / "glab_notes_ok.json"),
        )
        self.env.pop("STUB_FAIL", None)
        # Default cwd: no git, no CLAUDE.md -- user identity mode.
        self.cwd = self.new_dir()

    # --- cases ---------------------------------------------------------

    def case(self, name):
        """One named case; run_tests.py prints a PASS/FAIL line per case."""
        return self.subTest(name)

    def assertDenied(self, result, says):
        self.assertEqual(result.rc, 2, "want deny (exit 2); stderr: %s" % result.stderr)
        self.assertIn(says, result.stderr)

    def assertAllowed(self, result):
        self.assertEqual(result.rc, 0, "want allow (exit 0); stderr: %s" % result.stderr)

    # --- calling a guard -----------------------------------------------

    def call(self, tool, tool_input, cwd=None, **extra):
        payload = dict({"tool_name": tool, "tool_input": tool_input}, **extra)
        self.stub_log.write_text("")
        proc = subprocess.run(
            [str(HOOKS / ("%s.sh" % self.guard))],
            input=json.dumps(payload),
            cwd=str(cwd or self.cwd),
            env=self.env,
            capture_output=True,
            text=True,
        )
        return Result(proc.returncode, proc.stderr)

    def bash(self, command, cwd=None):
        return self.call("Bash", {"command": command}, cwd)

    def api_calls(self):
        """Forge CLI calls the last guard run made."""
        return self.stub_log.read_text().splitlines()

    @contextmanager
    def fixture(self, gh=None, fail=False):
        """Point the fake gh at fx/<gh>; fail=True makes every forge call fail."""
        saved = dict(self.env)
        if gh:
            self.env["GH_FIXTURE"] = str(FX / gh)
        if fail:
            self.env["STUB_FAIL"] = "1"
        try:
            yield
        finally:
            self.env = saved

    # --- scratch directories and repos ---------------------------------

    def new_dir(self):
        return Path(tempfile.mkdtemp(dir=str(self.tmp)))

    def new_repo(self, files=None, commit=False, branch=None):
        """A throwaway git repo: write files, optionally commit, optionally
        switch to a new branch."""
        repo = self.new_dir()
        self.git(repo, "init", "-q", "-b", "main")
        for rel, text in (files or {}).items():
            self.write(repo / rel, text)
        if commit:
            self.git(repo, "add", "-A")
            self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t",
                     "commit", "-q", "--allow-empty", "-m", "init")
        if branch:
            self.git(repo, "checkout", "-q", "-b", branch)
        return repo

    @staticmethod
    def git(repo, *args):
        subprocess.run(["git", "-C", str(repo)] + list(args), check=True,
                       capture_output=True)

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
