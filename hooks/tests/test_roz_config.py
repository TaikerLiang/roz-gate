"""bin/roz-config — the three per-person loop keys, in a throwaway repo.

Runtime like the hooks (stdlib, plain python3), so it lives in the runtime
suite. Every case runs the real executable; nothing is imported.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
TOOL = HOOKS.parent / "bin" / "roz-config"
REL = ".claude/roz-gate.local.json"


class RozConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.root / "README.md").write_text("x\n")
        self.git("-c", "user.name=a", "-c", "user.email=a@a", "add", "-A")
        self.git("-c", "user.name=a", "-c", "user.email=a@a", "commit", "-qm", "seed")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, text=True, check=True).stdout

    def run_tool(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(cwd or self.root),
                              capture_output=True, text=True)

    def stored(self):
        return json.loads((self.root / REL).read_text())

    def set_origin_head(self, branch):
        self.git("update-ref", "refs/remotes/origin/%s" % branch, "HEAD")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/%s" % branch)

    # ---- defaults -------------------------------------------------------
    def test_defaults_without_origin_head(self):
        with self.subTest(
                'roz-config: a fresh clone prints main (default), empty lists; no write'):
            p = self.run_tool()
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("default_branch   main  (default: origin/HEAD unset, assuming main)",
                          p.stdout)
            self.assertIn("inbox_label      -  (default: no filter)", p.stdout)
            self.assertFalse((self.root / REL).exists(), "a read never creates the file")

    def test_default_branch_follows_origin_head(self):
        with self.subTest("roz-config: default_branch defaults to the remote's HEAD branch"):
            self.set_origin_head("release/20261006")
            self.assertEqual(json.loads(self.run_tool("--json").stdout),
                             {"default_branch": "release/20261006",
                              "inbox_label": [], "inbox_assignee": []})

    # ---- writes ---------------------------------------------------------
    def test_set_replace_remove_default_branch(self):
        with self.subTest(
                'roz-config: default_branch set, replaced, removed back to the default'):
            p = self.run_tool("default_branch", "release/20261006")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(self.stored(), {"default_branch": "release/20261006"})
            self.run_tool("default_branch", "release/20261020")
            self.assertEqual(self.stored()["default_branch"], "release/20261020")
            p = self.run_tool("default_branch")
            self.assertIn("removed the override", p.stdout)
            self.assertEqual(self.stored(), {})
            self.assertEqual(json.loads(self.run_tool("--json").stdout)["default_branch"], "main")

    def test_inbox_keys_are_lists(self):
        with self.subTest(
                'roz-config: inbox_label / inbox_assignee round-trip as lists; no value removes'):
            self.run_tool("inbox_label", "discuss", "idea")
            self.run_tool("inbox_assignee", "TaikerLiang")
            self.assertEqual(self.stored(), {"inbox_label": ["discuss", "idea"],
                                             "inbox_assignee": ["TaikerLiang"]})
            self.assertEqual(json.loads(self.run_tool("--json").stdout)["inbox_label"],
                             ["discuss", "idea"])
            self.run_tool("inbox_label")
            self.assertEqual(self.stored(), {"inbox_assignee": ["TaikerLiang"]})

    def test_default_branch_takes_one_value(self):
        with self.subTest(
                'roz-config: default_branch refuses two values, writes nothing'):
            p = self.run_tool("default_branch", "a", "b")
            self.assertEqual(p.returncode, 2)
            self.assertFalse((self.root / REL).exists())

    def test_unknown_key_refused(self):
        with self.subTest(
                'roz-config: an unknown key is refused and names the three'):
            p = self.run_tool("patrol_model", "x")
            self.assertEqual(p.returncode, 2)
            self.assertIn("default_branch, inbox_label, inbox_assignee", p.stderr)
            self.assertFalse((self.root / REL).exists())

    # ---- never committed, nothing else touched ----------------------------
    def test_excluded_and_repo_untouched(self):
        with self.subTest(
                'roz-config: the file is excluded once and invisible to git status'):
            before = self.git("rev-parse", "HEAD")
            self.run_tool("inbox_label", "discuss")
            exclude = (self.root / ".git" / "info" / "exclude").read_text().split("\n")
            self.assertIn(REL, exclude)
            self.run_tool("inbox_label", "idea")
            self.assertEqual(exclude.count(REL), 1, "added once, not per write")
            self.assertEqual(self.git("status", "--porcelain"), "", "the file is invisible to git")
            self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_works_from_a_subdirectory_and_a_linked_worktree(self):
        with self.subTest(
                'roz-config: resolves the repo root from a subdirectory; a worktree is its own'):
            sub = self.root / "src"
            sub.mkdir()
            self.run_tool("inbox_label", "discuss", cwd=sub)
            self.assertTrue((self.root / REL).exists(), "resolved to the repository root")
            wt = Path(self.tmp.name) / "wt"
            self.git("worktree", "add", "-q", str(wt), "-b", "spec/5")
            p = self.run_tool("--json", cwd=wt)
            self.assertEqual(json.loads(p.stdout)["inbox_label"], [],
                             "a worktree is its own checkout: its own file, its own defaults")

    # ---- upgrade from a pre-1.23 block ------------------------------------
    def test_migrates_block_values_once(self):
        with self.subTest(
                'roz-config: a pre-1.23 block seeds the local file once, then is ignored'):
            (self.root / "CLAUDE.md").write_text(
                "## Development Workflow (Roz Gate)\n\n### Roz Gate config\n\n"
                "- forge: github\n- default_branch: release/20261006\n- test: true\n"
                "- inbox_label: discuss, idea\n- inbox_assignee: paul\n\n### Roz Gate personas\n\n"
                "- product: roz-gate:product\n")
            p = self.run_tool("--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("seeded", p.stderr)
            self.assertEqual(json.loads(p.stdout),
                             {"default_branch": "release/20261006",
                              "inbox_label": ["discuss", "idea"], "inbox_assignee": ["paul"]})
            self.assertTrue((self.root / REL).exists())
            self.run_tool("default_branch")        # remove the override …
            p = self.run_tool("--json")
            self.assertEqual(json.loads(p.stdout)["default_branch"], "main",
                             "… and the block is not consulted again")
            self.assertNotIn("seeded", p.stderr)

    def test_no_migration_without_block_keys(self):
        with self.subTest(
                'roz-config: a block without the three keys seeds nothing'):
            (self.root / "CLAUDE.md").write_text("### Roz Gate config\n\n- forge: github\n")
            p = self.run_tool("--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertFalse((self.root / REL).exists())
            self.assertEqual(p.stderr, "")

    def test_outside_a_repo(self):
        with self.subTest(
                'roz-config: outside a repository exits 2'):
            p = self.run_tool(cwd=Path(self.tmp.name))
            self.assertEqual(p.returncode, 2)

    def test_corrupt_file_is_an_error_not_a_reset(self):
        with self.subTest(
                'roz-config: a corrupt file is an error, never overwritten'):
            (self.root / ".claude").mkdir()
            (self.root / REL).write_text("{not json")
            p = self.run_tool("inbox_label", "x")
            self.assertEqual(p.returncode, 2)
            self.assertEqual((self.root / REL).read_text(), "{not json")


if __name__ == "__main__":
    unittest.main()
