"""sync-worktree (PostToolUse, Bash; #122): after a `git worktree add`, the
gitignored files `worktree_copy` lists (default `.env`) are copied from the
main checkout into every loop worktree under `<git-common-dir>/roz-gate/wt/`
that lacks them — never overwriting, never outside the checkout, never into
a worktree of yours, and never blocking. Each case is a real repo and a real
`git worktree add`; the payload is the PostToolUse shape."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

from hooktest import HOOKS, HookTest, Result

ADD = "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/spec/5 -B spec/5 main"
LOCAL = ".claude/roz-gate.local.json"


class WorktreeCopy(HookTest):
    guard = "sync-worktree"

    def repo(self, files=None, ignore=".env\nconfig/local/\n.claude/\n"):
        """A repo with `.env` gitignored and present in the checkout."""
        files = dict({".gitignore": ignore, ".env": "SECRET=1\n"}, **(files or {}))
        repo = self.new_repo(files)
        self.git(repo, "add", ".gitignore")
        self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
        return repo

    def add(self, repo, branch="spec/5", where=None):
        path = where or os.path.join(str(repo), ".git", "roz-gate", "wt", branch)
        self.git(repo, "worktree", "add", "-q", "-b", branch, path)
        return path

    def run_hook(self, repo, command=ADD, cwd=None):
        """The PostToolUse payload carries the session's cwd; the hook runs there."""
        where = cwd or repo
        payload = {"tool_name": "Bash", "tool_input": {"command": command},
                   "tool_response": {"stdout": "", "stderr": ""}, "cwd": str(where)}
        proc = subprocess.run([str(HOOKS / "sync-worktree.sh")], input=json.dumps(payload),
                              cwd=str(where), env=self.env, capture_output=True, text=True)
        return Result(proc.returncode, proc.stderr, proc.stdout)

    def context(self, result):
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"] \
            if result.stdout.strip() else ""

    @staticmethod
    def git_out(repo, *args):
        return subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True,
                              text=True, check=True).stdout

    def read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_copies(self):
        with self.case("worktree_copy: .env copied into the loop worktree by default"):
            repo = self.repo()
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertEqual(r.rc, 0)
            self.assertEqual(self.read(os.path.join(wt, ".env")), "SECRET=1\n")
            self.assertIn("copied .env into", self.context(r))
        with self.case("worktree_copy: a listed directory is copied whole"):
            repo = self.repo({"config/local/db.yml": "url: x\n",
                              LOCAL: json.dumps({"worktree_copy": [".env", "config/local"]})})
            wt = self.add(repo)
            self.run_hook(repo)
            self.assertEqual(self.read(os.path.join(wt, "config/local/db.yml")), "url: x\n")
            self.assertTrue(os.path.exists(os.path.join(wt, ".env")))
        with self.case("worktree_copy: run from a subdirectory, the main checkout still found"):
            repo = self.repo({"sub/README": "x\n"})
            wt = self.add(repo)
            self.run_hook(repo, cwd=repo / "sub")
            self.assertTrue(os.path.exists(os.path.join(wt, ".env")))
        with self.case("worktree_copy: run from inside another loop worktree — both filled, "
                       "from the main checkout"):
            repo = self.repo()
            first = self.add(repo, "spec/5")
            second = self.add(repo, "feat/5")
            self.run_hook(repo, cwd=first)
            for wt in (first, second):
                self.assertEqual(self.read(os.path.join(wt, ".env")), "SECRET=1\n")
        with self.case("worktree_copy: a symlinked .env arrives as its contents, never as a "
                       "link to the tracked file it names (codex review, PR #184)"):
            repo = self.repo({"config/default.env": "DEFAULT=1\n"})
            os.remove(repo / ".env")
            os.symlink("config/default.env", repo / ".env")
            self.git(repo, "add", "config/default.env")
            self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "d")
            wt = self.add(repo)
            self.run_hook(repo)
            dst = os.path.join(wt, ".env")
            self.assertFalse(os.path.islink(dst))
            self.assertEqual(self.read(dst), "DEFAULT=1\n")
            with open(dst, "a", encoding="utf-8") as f:
                f.write("WRITTEN=1\n")
            self.assertEqual(self.read(os.path.join(wt, "config/default.env")), "DEFAULT=1\n")
        with self.case("worktree_copy: a .env linked to a shared file outside the repo is "
                       "copied — containment is judged on the path as written"):
            repo = self.repo()
            shared = repo.parent / "shared.env"
            self.write(shared, "SHARED=1\n")
            os.remove(repo / ".env")
            os.symlink(str(shared), repo / ".env")
            wt = self.add(repo)
            self.run_hook(repo)
            self.assertFalse(os.path.islink(os.path.join(wt, ".env")))
            self.assertEqual(self.read(os.path.join(wt, ".env")), "SHARED=1\n")
        with self.case("worktree_copy: a child listed before its parent — the parent is copied "
                       "whole (codex review, PR #184)"):
            repo = self.repo({"config/local/a.yml": "a\n", "config/local/b.yml": "b\n",
                              LOCAL: json.dumps({"worktree_copy": ["config/local/a.yml",
                                                                   "config/local"]})})
            wt = self.add(repo)
            self.run_hook(repo)
            self.assertEqual(self.read(os.path.join(wt, "config/local/b.yml")), "b\n")
            self.assertEqual(self.read(os.path.join(wt, "config/local/a.yml")), "a\n")
        with self.case("worktree_copy: a file named `-secret` is a path, not a git option "
                       "(codex review, PR #184)"):
            repo = self.repo({"-secret": "S\n", LOCAL: json.dumps({"worktree_copy": ["-secret"]})},
                             ignore=".env\n-secret\n.claude/\n")
            wt = self.add(repo)
            self.run_hook(repo)
            self.assertEqual(self.read(os.path.join(wt, "-secret")), "S\n")
        with self.case("worktree_copy: the list as the local file stores it — a comma string"):
            repo = self.repo({"config/local/db.yml": "url: x\n",
                              LOCAL: json.dumps({"worktree_copy": ".env, config/local"})})
            wt = self.add(repo)
            self.run_hook(repo)
            self.assertTrue(os.path.exists(os.path.join(wt, "config/local/db.yml")))

    def test_leaves_alone(self):
        with self.case("worktree_copy: an existing destination is never overwritten"):
            repo = self.repo()
            wt = self.add(repo)
            self.write(Path(wt) / ".env", "MINE=1\n")
            r = self.run_hook(repo)
            self.assertEqual(self.read(os.path.join(wt, ".env")), "MINE=1\n")
            self.assertEqual(self.context(r), "")
        with self.case("worktree_copy: a missing source is skipped silently"):
            repo = self.repo({LOCAL: json.dumps({"worktree_copy": ["nope.env"]})})
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertFalse(os.path.exists(os.path.join(wt, "nope.env")))
            self.assertEqual((r.rc, self.context(r)), (0, ""))
        with self.case("worktree_copy: your own worktree outside roz-gate/wt is never touched"):
            repo = self.repo()
            mine = str(self.new_dir() / "mine")
            self.add(repo, "mine", where=mine)
            self.run_hook(repo)
            self.assertFalse(os.path.exists(os.path.join(mine, ".env")))
        with self.case('worktree_copy: "" copies nothing'):
            repo = self.repo({LOCAL: json.dumps({"worktree_copy": ""})})
            wt = self.add(repo)
            self.run_hook(repo)
            self.assertFalse(os.path.exists(os.path.join(wt, ".env")))
        with self.case("worktree_copy: `..` and absolute entries are dropped, unreported"):
            repo = self.repo()
            outside = repo.parent / "secret"        # what `../secret` names from the repo
            self.write(outside, "x\n")
            self.write(repo / LOCAL, json.dumps({"worktree_copy": ["../secret", str(outside)]}))
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertEqual(sorted(os.listdir(wt)), [".git", ".gitignore"])
            self.assertEqual(self.context(r), "")
        with self.case("worktree_copy: a path git does not ignore is reported, not copied"):
            repo = self.repo(ignore=".claude/\n")
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertFalse(os.path.exists(os.path.join(wt, ".env")))
            self.assertIn("git does not ignore it", self.context(r))
        with self.case("worktree_copy: a command without `worktree add` never reaches python"):
            repo = self.repo()
            wt = self.add(repo)
            r = self.run_hook(repo, command="git status")
            self.assertFalse(os.path.exists(os.path.join(wt, ".env")))
            self.assertEqual((r.rc, r.stdout), (0, ""))
        with self.case("worktree_copy: a copy error is reported and the exit is still 0"):
            repo = self.repo({"config/local/db.yml": "url: x\n",
                              LOCAL: json.dumps({"worktree_copy": ["config/local"]})})
            wt = self.add(repo)
            os.makedirs(os.path.join(wt, "config"))
            os.chmod(os.path.join(wt, "config"), 0o500)
            self.addCleanup(os.chmod, os.path.join(wt, "config"), 0o700)
            r = self.run_hook(repo)
            self.assertEqual(r.rc, 0)
            self.assertIn("could not copy config/local", self.context(r))
        with self.case("worktree_copy: a failed directory copy leaves nothing behind, and the "
                       "next run completes it (codex review, PR #184)"):
            repo = self.repo({"config/local/a.yml": "a\n", "config/local/b.yml": "b\n",
                              LOCAL: json.dumps({"worktree_copy": ["config/local"]})})
            wt = self.add(repo)
            unreadable = repo / "config/local/b.yml"
            os.chmod(unreadable, 0)
            self.addCleanup(os.chmod, unreadable, 0o600)
            r = self.run_hook(repo)
            self.assertIn("could not copy config/local", self.context(r))
            self.assertFalse(os.path.lexists(os.path.join(wt, "config/local")))
            self.assertEqual(os.listdir(os.path.join(wt, "config")), [])
            os.chmod(unreadable, 0o600)
            self.run_hook(repo)
            self.assertEqual(self.read(os.path.join(wt, "config/local/b.yml")), "b\n")
        with self.case("worktree_copy: a directory whose ignore rule has a `!` exception is "
                       "reported, not copied (codex review, PR #184)"):
            repo = self.repo({"config/local/a.yml": "a\n", "config/local/public.txt": "p\n",
                              LOCAL: json.dumps({"worktree_copy": ["config/local"]})},
                             ignore=".env\nconfig/local/*\n!config/local/public.txt\n.claude/\n")
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertFalse(os.path.lexists(os.path.join(wt, "config/local")))
            self.assertIn("config/local (config/local/public.txt)", self.context(r))
            self.assertIn("git does not ignore it", self.context(r))
        with self.case("worktree_copy: a directory whose own .gitignore unignores a file is "
                       "removed after the copy and reported (codex review, PR #184)"):
            repo = self.repo({"config/local/a.yml": "a\n", "config/local/public.txt": "p\n",
                              "config/local/.gitignore": "!public.txt\n",
                              LOCAL: json.dumps({"worktree_copy": ["config/local"]})},
                             ignore=".env\nconfig/local/*\n.claude/\n")
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertFalse(os.path.lexists(os.path.join(wt, "config/local")))
            self.assertIn("config/local (config/local/public.txt)", self.context(r))
            self.assertEqual(self.git_out(wt, "status", "--porcelain"), "")
        with self.case("worktree_copy: a listed .gitignore that unignores another listed file "
                       "— that file is removed and reported (codex review, PR #184)"):
            repo = self.repo({"config/local/a.txt": "a\n", "config/local/.gitignore": "!a.txt\n",
                              LOCAL: json.dumps({"worktree_copy": ["config/local/a.txt",
                                                                   "config/local/.gitignore"]})},
                             ignore=".env\nconfig/local/*\n.claude/\n")
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertFalse(os.path.lexists(os.path.join(wt, "config/local/a.txt")))
            self.assertTrue(os.path.exists(os.path.join(wt, "config/local/.gitignore")))
            self.assertIn("config/local/a.txt (config/local/a.txt)", self.context(r))
            self.assertEqual(self.git_out(wt, "status", "--porcelain"), "")
        with self.case("worktree_copy: an entry written `./x` is matched as git names it — the "
                       "final check still catches it (codex review, PR #184)"):
            repo = self.repo({"config/a.txt": "a\n", "config/.gitignore": "!a.txt\n",
                              LOCAL: json.dumps({"worktree_copy": ["./config/a.txt",
                                                                   "config//.gitignore"]})},
                             ignore=".env\nconfig/*\n.claude/\n")
            wt = self.add(repo)
            r = self.run_hook(repo)
            self.assertFalse(os.path.lexists(os.path.join(wt, "config/a.txt")))
            self.assertIn("config/a.txt (config/a.txt)", self.context(r))
            self.assertEqual(self.git_out(wt, "status", "--porcelain"), "")
        with self.case("worktree_copy: outside any git repository — nothing, exit 0"):
            r = self.run_hook(self.new_dir())
            self.assertEqual((r.rc, r.stdout), (0, ""))


class InstallNeverReplaces(HookTest):
    """The install primitives, against a run that got there first (codex
    review, PR #184: two sessions can both see an absent destination)."""

    guard = "sync-worktree"

    def module(self):
        spec = importlib.util.spec_from_file_location("sync_worktree",
                                                      HOOKS / "sync_worktree.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_install(self):
        mod, d = self.module(), self.new_dir()
        self.write(d / "src.env", "NEW=1\n")
        with self.case("worktree_copy: a file another run installed first is kept, not replaced"):
            self.write(d / "dst.env", "FIRST=1\n")
            self.assertFalse(mod.install_file(str(d / "src.env"), str(d / "dst.env")))
            self.assertEqual((d / "dst.env").read_text(), "FIRST=1\n")
        with self.case("worktree_copy: a directory another run installed first is kept, and the "
                       "stage is cleaned up"):
            self.write(d / "src/a.yml", "new\n")
            self.write(d / "dst/a.yml", "first\n")
            self.assertFalse(mod.install_dir(str(d / "src"), str(d / "dst")))
            self.assertEqual((d / "dst/a.yml").read_text(), "first\n")
            self.assertEqual(sorted(p.name for p in d.iterdir()),
                             ["dst", "dst.env", "src", "src.env"])
        with self.case("worktree_copy: an absent destination is created, with the contents"):
            self.assertTrue(mod.install_file(str(d / "src.env"), str(d / "fresh.env")))
            self.assertEqual((d / "fresh.env").read_text(), "NEW=1\n")

