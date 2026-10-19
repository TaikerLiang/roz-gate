"""guard-acceptance (Edit, Write, MultiEdit): the acceptance suite is not
editable on a spec branch -- it changes on qa/<n> and merges in."""

import json
import subprocess

from hooktest import HookTest, config_block

ACCEPTANCE_FILE = "tests/acceptance/offers/test_expiry.py"


LOCAL = ".claude/roz-gate.local.json"   # bin/roz-config's file: the template's home (#165)


def local_template(template):
    return json.dumps({"branch_template": template}, indent=2) + "\n"


class AcceptanceSuiteIsNotEditableOnSpecBranch(HookTest):
    guard = "guard-acceptance"

    # (name, tool, path) -- on spec/63; each is denied with "acceptance suite".
    DENIED = [
        ("acceptance edit on spec branch blocked", "Edit",
         "tests/acceptance/offers/test_expiry.py"),
        ("Write is guarded too", "Write", "tests/acceptance/offers/test_new.py"),
        ("MultiEdit is guarded too", "MultiEdit", "tests/acceptance/offers/test_expiry.py"),
    ]
    # (name, tool, path) -- on spec/63.
    ALLOWED = [
        ("implementation code on spec branch allowed", "Edit", "src/offers/repo.py"),
        ("spec docs on spec branch allowed", "Edit", "docs/specs/63/spec.md"),
        ("unit tests on spec branch allowed", "Edit", "tests/unit/test_repo.py"),
        ("sibling dir is not the acceptance dir", "Edit", "tests/acceptance-old/test_x.py"),
        ("the acceptance dir itself is not a file under it", "Edit", "tests/acceptance"),
    ]

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance")},
            commit=True, branch="spec/63")

    def edit(self, repo, tool, path):
        return self.call(tool, {"file_path": str(repo / path)}, repo)

    def test_on_spec_branch(self):
        for name, tool, path in self.DENIED:
            with self.case(name):
                self.assertDenied(self.edit(self.repo, tool, path), "acceptance suite")
        for name, tool, path in self.ALLOWED:
            with self.case(name):
                self.assertAllowed(self.edit(self.repo, tool, path))

    def test_config(self):
        no_config = self.new_repo(commit=True, branch="spec/1")
        with self.case("no Roz Gate config: nothing to enforce"):
            self.assertAllowed(self.edit(no_config, "Edit", "tests/acceptance/test_x.py"))
        # A misconfigured acceptance_dir pointing at the repo root would match
        # every path -- it must enforce nothing rather than deny every edit.
        root = self.new_repo({"CLAUDE.md": config_block(forge="github", acceptance_dir=".")},
                             commit=True, branch="spec/1")
        with self.case("acceptance_dir at the repo root enforces nothing"):
            self.assertAllowed(self.edit(root, "Edit", "src/anything.py"))

    # branch_template (#75): the spec branch is whatever the template renders.
    def test_branch_template(self):
        tpl = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance"),
             LOCAL: local_template("{type}/{user}/{n}/{seq}")},
            commit=True, branch="spec/pwliangc/63/1")
        with self.case("template: a templated spec branch is a spec branch — acceptance edit "
                       "denied"):
            self.assertDenied(self.edit(tpl, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        with self.case("template: implementation code on the templated spec branch allowed"):
            self.assertAllowed(self.edit(tpl, "Edit", "src/offers/repo.py"))
        self.git(tpl, "checkout", "-q", "-b", "test/pwliangc/63/1")
        with self.case("template: the templated qa branch (type test) allowed — that is the road"):
            self.assertAllowed(self.edit(tpl, "Edit", ACCEPTANCE_FILE))
        self.git(tpl, "checkout", "-q", "-b", "fix/pwliangc/63/1")
        with self.case("template: the templated implementation branch allowed"):
            self.assertAllowed(self.edit(tpl, "Edit", ACCEPTANCE_FILE))
        self.git(tpl, "checkout", "-q", "-b", "spec/pwliangc/63/1x")
        with self.case("template: a near-miss (trailing junk) is not the spec branch"):
            self.assertAllowed(self.edit(tpl, "Edit", ACCEPTANCE_FILE))
        self.git(tpl, "checkout", "-q", "-b", "spec/63")
        with self.case("template: the pre-template name spec/<n> is NOT a spec branch under it"):
            self.assertAllowed(self.edit(tpl, "Edit", ACCEPTANCE_FILE))
        # {kind} first, {user} later: the prefilter's spec/* test still routes it to python.
        kind_first = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance"),
             LOCAL: local_template("{kind}/{user}/{n}")},
            commit=True, branch="spec/paul/7")
        with self.case("template: {kind}/{user}/{n} spec branch denied"):
            self.assertDenied(self.edit(kind_first, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        # An invalid template (unknown placeholder) enforces nothing rather than everything.
        bad = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance"),
             LOCAL: local_template("{kind}/{ticket}")},
            commit=True, branch="spec/63")
        with self.case("template: an unknown placeholder matches no branch (enforces nothing)"):
            self.assertAllowed(self.edit(bad, "Edit", ACCEPTANCE_FILE))
        with self.case("no template line: spec/<n> still denied (the 1.11–1.28 rule, unchanged)"):
            self.assertDenied(self.edit(self.repo, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        # The block's line is not read since 2.4.0 (#165): roz-config moves it
        # into the local file once; until then the spec branch is spec/*.
        notes = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance",
                                       branch_template="{user}/{type}/{n}")},
            commit=True, branch="spec/5")
        with self.case("template: a block branch_template line with no local key is ignored — "
                       "spec/5 still denied"):
            self.assertDenied(self.edit(notes, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        self.git(notes, "checkout", "-q", "-b", "pwliangc/spec/5")
        with self.case("template: …and the block line's own render is not a spec branch there"):
            self.assertAllowed(self.edit(notes, "Edit", ACCEPTANCE_FILE))
        cleared = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance"),
             LOCAL: local_template("")}, commit=True, branch="spec/5")
        with self.case('template: a cleared local key ("") is the default — spec/5 denied'):
            self.assertDenied(self.edit(cleared, "Edit", ACCEPTANCE_FILE), "acceptance suite")

    # The block's two homes (#94): CLAUDE.md, else CLAUDE.local.md, here or in
    # the main checkout. ADMC kept its block in an untracked CLAUDE.local.md and
    # this guard was silently OFF on every spec branch.
    def test_config_homes(self):
        block = config_block(forge="github", acceptance_dir="tests/acceptance")
        local = self.new_repo({"CLAUDE.local.md": block, "CLAUDE.md": "# Project\n"},
                              commit=True, branch="spec/63")
        with self.case("homes: block only in CLAUDE.local.md — acceptance edit denied"):
            self.assertDenied(self.edit(local, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        both = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance"),
             "CLAUDE.local.md": config_block(forge="github", acceptance_dir="qa/suite")},
            commit=True, branch="spec/63")
        with self.case("homes: both files carry a block — CLAUDE.md wins (its dir denied)"):
            self.assertDenied(self.edit(both, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        with self.case("homes: both files carry a block — CLAUDE.local.md's dir is not the suite"):
            self.assertAllowed(self.edit(both, "Edit", "qa/suite/test_x.py"))
        # A linked worktree has no CLAUDE.local.md (untracked): the hook falls
        # back to the main checkout, the parent of the common git dir.
        main = self.new_repo({"CLAUDE.md": "# Project\n"}, commit=True)
        self.write(main / "CLAUDE.local.md", block)
        wt = self.new_dir() / "wt"
        self.git(main, "worktree", "add", "-q", "-b", "spec/7", str(wt))
        with self.case("homes: worktree cwd, block only in the main checkout's CLAUDE.local.md "
                       "— denied"):
            self.assertDenied(self.edit(wt, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        with self.case("homes: the same worktree, a file outside the suite allowed"):
            self.assertAllowed(self.edit(wt, "Edit", "src/offers/repo.py"))
        # The prefilter's branch_template escalation reads the local file in
        # both places too: this toplevel, else the main checkout (#165).
        tpl_local = self.new_repo(
            {"CLAUDE.md": "# Project\n",
             "CLAUDE.local.md": config_block(forge="github", acceptance_dir="tests/acceptance"),
             LOCAL: local_template("{type}/{user}/{n}/{seq}")},
            commit=True, branch="spec/pwliangc/63/1")
        with self.case("homes: branch_template in the local file, block in CLAUDE.local.md — "
                       "templated spec branch denied"):
            self.assertDenied(self.edit(tpl_local, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        tpl_wt_main = self.new_repo({"CLAUDE.md": "# Project\n"}, commit=True)
        self.write(tpl_wt_main / "CLAUDE.local.md",
                   config_block(forge="github", acceptance_dir="tests/acceptance"))
        self.write(tpl_wt_main / LOCAL, local_template("{type}/{user}/{n}/{seq}"))
        tpl_wt = self.new_dir() / "wt"
        self.git(tpl_wt_main, "worktree", "add", "-q", "-b", "spec/pwliangc/9/1", str(tpl_wt))
        with self.case("homes: worktree cwd, branch_template only in the main checkout's "
                       "local file — denied"):
            self.assertDenied(self.edit(tpl_wt, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        # A spec branch only the template names (not spec/*): the main checkout's
        # file is the one thing that makes it one, in python and in the prefilter.
        lead_main = self.new_repo({"CLAUDE.md": config_block(
            forge="github", acceptance_dir="tests/acceptance")}, commit=True)
        self.write(lead_main / LOCAL, local_template("{user}/{kind}/{n}"))
        lead_wt = self.new_dir() / "wt"
        self.git(lead_main, "worktree", "add", "-q", "-b", "pwliangc/spec/9", str(lead_wt))
        with self.case("homes: worktree cwd on pwliangc/spec/9, {user}/{kind}/{n} only in the "
                       "main checkout's local file — denied"):
            self.assertDenied(self.edit(lead_wt, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        # The worktree's own file without the key passes to the main checkout's
        # (codex, PR #169); a stored "" there is a chosen default and stops.
        self.write(lead_wt / LOCAL, json.dumps({"branch_user": "pwliangc"}) + "\n")
        with self.case("homes: the worktree's own local file holds only branch_user — the main "
                       "checkout's template still applies, denied"):
            self.assertDenied(self.edit(lead_wt, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        self.write(lead_wt / LOCAL, local_template(""))
        with self.case('homes: the worktree\'s own file stores branch_template "" — the default, '
                       "so pwliangc/spec/9 is not a spec branch there"):
            self.assertAllowed(self.edit(lead_wt, "Edit", ACCEPTANCE_FILE))
        # A separate git dir (codex, PR #100): git records the main work tree
        # nowhere a linked worktree can read — `core.worktree` is the one hint.
        sgd_main, sgd_git = self.new_dir() / "repo", self.new_dir() / "gitdir"
        subprocess.run(["git", "init", "-q", "-b", "main", "--separate-git-dir", str(sgd_git),
                        str(sgd_main)], check=True, capture_output=True)
        self.write(sgd_main / "CLAUDE.md", "# Project\n")
        self.git(sgd_main, "add", "-A")
        self.git(sgd_main, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "i")
        self.write(sgd_main / "CLAUDE.local.md", block)  # untracked, as in life
        sgd_wt = self.new_dir() / "wt"
        self.git(sgd_main, "worktree", "add", "-q", "-b", "spec/8", str(sgd_wt))
        with self.case("homes: separate git dir, no core.worktree — the main checkout is "
                       "unreachable from the worktree (documented: keep the block in CLAUDE.md)"):
            self.assertAllowed(self.edit(sgd_wt, "Edit", ACCEPTANCE_FILE))
        self.git(sgd_main, "config", "core.worktree", str(sgd_main))
        with self.case("homes: separate git dir + core.worktree — worktree cwd, block only in "
                       "the main checkout's CLAUDE.local.md — denied"):
            self.assertDenied(self.edit(sgd_wt, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        with self.case("homes: no block in either file, either place — nothing to enforce"):
            bare = self.new_repo({"CLAUDE.md": "# Project\n", "CLAUDE.local.md": "# notes\n"},
                                 commit=True, branch="spec/1")
            self.assertAllowed(self.edit(bare, "Edit", ACCEPTANCE_FILE))

    def test_other_branches(self):
        self.git(self.repo, "checkout", "-q", "-b", "qa/63")
        with self.case("same file on qa/<n> allowed — that is the road"):
            self.assertAllowed(self.edit(self.repo, "Edit", ACCEPTANCE_FILE))
        self.git(self.repo, "checkout", "-q", "-b", "feat/63")
        with self.case("feat branch unaffected"):
            self.assertAllowed(self.edit(self.repo, "Edit", ACCEPTANCE_FILE))
