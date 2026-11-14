"""A guard that cannot finish its check blocks the call (#281).

Claude Code reads every exit but 2 as "allow": before #281 a missing python3
(127), an interpreter that could not start (126) or an uncaught exception (1)
let the call through. Every case runs a guard's `.sh` entry — prefilter
included — under one of four conditions: python3 off PATH, a python3 that
cannot start, an exception injected into the guard (a `json` module on
PYTHONPATH that raises on import), or nothing wrong. A prefilter allow stays
an allow without Python; a protocol deny keeps its own message."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from hooktest import HOOKS, HookTest, Result, config_block

FAILED = "tool failure, not a protocol block"
ADD_LABEL = 'gh issue edit 5 --add-label "status: ready-for-spec"'
SUMMARY = 'gh issue comment 54 --body "**[intake] · summary** ..."'
ADD = "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/spec/5 -B spec/5 main"


class GuardFailure(HookTest):
    """Helpers: the three broken environments, applied to self.env."""

    def no_python(self):
        """PATH holds only what the shims call besides python3."""
        bindir = self.new_dir()
        for tool in ("bash", "git", "grep", "cat"):
            os.symlink(shutil.which(tool), str(bindir / tool))
        self.env["PATH"] = str(bindir)

    def broken_python(self):
        """A python3 on PATH whose interpreter line names nothing: it cannot start."""
        bindir = self.new_dir()
        self.write(bindir / "python3", "#!/nonexistent/roz-gate-test/python\n")
        (bindir / "python3").chmod(0o755)
        self.env["PATH"] = "%s:%s" % (bindir, self.env["PATH"])

    def crashing_guard(self):
        """Every guard imports json first: a json on PYTHONPATH that raises."""
        libdir = self.new_dir()
        self.write(libdir / "json.py", "raise RuntimeError('injected by test_guard_failure')\n")
        self.env["PYTHONPATH"] = str(libdir)

    def broken(self):
        """(label, setter) for each way the Python side can fail to decide."""
        return [("python3 missing", self.no_python, "python3 not found"),
                ("python3 cannot start", self.broken_python, "could not start"),
                ("an exception in the guard", self.crashing_guard, "did not finish")]

    def assertToolFailure(self, result, name, says):
        self.assertDenied(result, says)
        self.assertIn("roz-gate %s:" % name, result.stderr)
        self.assertIn(FAILED, result.stderr)


class GateFailsClosed(GuardFailure):
    guard = "guard-gate"

    def test_gate(self):
        for label, setter, says in self.broken():
            saved = dict(self.env)
            setter()
            with self.case("guard-gate, %s: a call the prefilter escalates is denied as a tool "
                           "failure" % label):
                self.assertToolFailure(self.bash(ADD_LABEL), "guard-gate", says)
            with self.case("guard-gate, %s: a call the prefilter lets through stays allowed"
                           % label):
                self.assertAllowed(self.bash("ls -la && git status"))
            self.env = saved
        with self.case("guard-gate: a forge answer of the wrong shape (a list, not the issue "
                       "object) crashes the guard and is denied, not allowed"):
            wrong = self.tmp / "gh_list.json"
            wrong.write_text("[]\n")
            self.env["GH_FIXTURE"] = str(wrong)
            r = self.bash(SUMMARY)
            self.assertToolFailure(r, "guard-gate", "did not finish")
            self.assertIn("AttributeError", r.stderr)
        with self.case("guard-gate: a protocol deny keeps its own message, not a tool failure"):
            r = self.bash(ADD_LABEL)
            self.assertDenied(r, "gate labels")
            self.assertNotIn(FAILED, r.stderr)


class BlindFailsClosed(GuardFailure):
    guard = "guard-blind"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo({"src/app.txt": "demo\n"}, commit=True, branch="qa/5")
        self.marker = self.repo / ".git/roz-gate/fidelity-dispatch"

    def test_blind(self):
        for label, setter, says in self.broken():
            saved = dict(self.env)
            setter()
            with self.case("guard-blind, %s: no dispatch marker — allowed" % label):
                self.assertAllowed(self.bash("cat src/app.txt", cwd=self.repo))
            self.write(self.marker, "issue=5\nseat=qa\n")
            with self.case("guard-blind, %s: under a dispatch marker even a harmless read is "
                           "denied as a tool failure" % label):
                self.assertToolFailure(self.bash("ls", cwd=self.repo), "guard-blind", says)
            self.marker.unlink()
            self.env = saved
        self.write(self.marker, "issue=5\nseat=qa\n")
        with self.case("guard-blind: a protocol deny keeps its own message"):
            r = self.bash("cat src/app.txt", cwd=self.repo)
            self.assertDenied(r, "src/")
            self.assertNotIn(FAILED, r.stderr)
        with self.case("guard-blind: a harmless read under the marker is still allowed"):
            self.assertAllowed(self.bash("ls", cwd=self.repo))


class AcceptanceFailsClosed(GuardFailure):
    """No prefilter since #277: every edit reaches Python, so a broken Python
    denies every edit — ruled on #281, the visible direction."""

    guard = "guard-acceptance"
    SUITE = "tests/acceptance/test_x.py"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance")},
            commit=True, branch="spec/63")

    def edit(self, path, cwd=None):
        return self.call("Edit", {"file_path": str(path)}, cwd or self.repo)

    def test_acceptance(self):
        plain = self.new_repo(commit=True)
        # #277's layout: the session in the main checkout, the edit in a loop
        # worktree on the spec branch, by absolute path.
        main = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance")},
            commit=True)
        wt = Path(main) / ".git" / "roz-gate" / "wt" / "spec" / "5"
        self.git(main, "worktree", "add", "-q", "-b", "spec/5", str(wt))
        for label, setter, says in self.broken():
            saved = dict(self.env)
            setter()
            with self.case("guard-acceptance, %s: a suite edit on the spec branch is denied as "
                           "a tool failure" % label):
                self.assertToolFailure(self.edit(self.repo / self.SUITE), "guard-acceptance",
                                       says)
            with self.case("guard-acceptance, %s: cwd the main checkout, the edit in a linked "
                           "worktree — denied as a tool failure" % label):
                self.assertToolFailure(self.edit(wt / self.SUITE, cwd=main), "guard-acceptance",
                                       says)
            with self.case("guard-acceptance, %s: an edit in a repo with no Roz Gate config is "
                           "denied too (no prefilter; ruled on #281)" % label):
                self.assertToolFailure(self.edit(plain / "a.txt", cwd=plain), "guard-acceptance",
                                       says)
            self.env = saved
        with self.case("guard-acceptance: a protocol deny keeps its own message"):
            r = self.edit(self.repo / self.SUITE)
            self.assertDenied(r, "acceptance suite")
            self.assertNotIn(FAILED, r.stderr)
        with self.case("guard-acceptance: the linked-worktree edit is a protocol deny"):
            self.assertDenied(self.edit(wt / self.SUITE, cwd=main), "acceptance suite")
        with self.case("guard-acceptance: an edit outside the suite is allowed"):
            self.assertAllowed(self.edit(self.repo / "src/a.py"))


class SyncReportsNotCopied(GuardFailure):
    """PostToolUse: the command already ran; a failure is reported, never a block."""

    guard = "sync-worktree"

    def run_hook(self, command, cwd):
        """The PostToolUse payload carries the session's cwd (`call` takes it
        as the process's)."""
        payload = {"tool_name": "Bash", "tool_input": {"command": command},
                   "tool_response": {"stdout": "", "stderr": ""}, "cwd": str(cwd)}
        proc = subprocess.run([str(HOOKS / "sync-worktree.sh")], input=json.dumps(payload),
                              cwd=str(cwd), env=self.env, capture_output=True, text=True)
        return Result(proc.returncode, proc.stderr, proc.stdout)

    def test_sync(self):
        repo = self.new_repo({".gitignore": ".env\n", ".env": "SECRET=1\n"})
        self.git(repo, "add", ".gitignore")
        self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "i")
        for label, setter, _ in self.broken():
            saved = dict(self.env)
            setter()
            with self.case("sync-worktree, %s: a worktree command gets an additionalContext "
                           "saying nothing was copied and how to recover; exit 0" % label):
                r = self.run_hook(ADD, repo)
                self.assertEqual(r.rc, 0, r.stderr)
                ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
                self.assertIn("worktree_copy did not run", ctx)
                self.assertIn("Install python3", ctx)
            with self.case("sync-worktree, %s: a command without `worktree` — silent, exit 0"
                           % label):
                r = self.run_hook("ls", repo)
                self.assertEqual((r.rc, r.stdout), (0, ""))
            self.env = saved
