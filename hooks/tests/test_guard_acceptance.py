"""guard-acceptance (Edit, Write, MultiEdit): the acceptance suite is not
editable on a spec branch -- it changes on qa/<n> and merges in."""

from hooktest import HookTest, config_block

ACCEPTANCE_FILE = "tests/acceptance/offers/test_expiry.py"


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
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance",
                                       branch_template="{type}/{user}/{n}/{seq}")},
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
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance",
                                       branch_template="{kind}/{user}/{n}")},
            commit=True, branch="spec/paul/7")
        with self.case("template: {kind}/{user}/{n} spec branch denied"):
            self.assertDenied(self.edit(kind_first, "Edit", ACCEPTANCE_FILE), "acceptance suite")
        # An invalid template (unknown placeholder) enforces nothing rather than everything.
        bad = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir="tests/acceptance",
                                       branch_template="{kind}/{ticket}")},
            commit=True, branch="spec/63")
        with self.case("template: an unknown placeholder matches no branch (enforces nothing)"):
            self.assertAllowed(self.edit(bad, "Edit", ACCEPTANCE_FILE))
        with self.case("no template line: spec/<n> still denied (the 1.11–1.28 rule, unchanged)"):
            self.assertDenied(self.edit(self.repo, "Edit", ACCEPTANCE_FILE), "acceptance suite")

    def test_other_branches(self):
        self.git(self.repo, "checkout", "-q", "-b", "qa/63")
        with self.case("same file on qa/<n> allowed — that is the road"):
            self.assertAllowed(self.edit(self.repo, "Edit", ACCEPTANCE_FILE))
        self.git(self.repo, "checkout", "-q", "-b", "feat/63")
        with self.case("feat branch unaffected"):
            self.assertAllowed(self.edit(self.repo, "Edit", ACCEPTANCE_FILE))
