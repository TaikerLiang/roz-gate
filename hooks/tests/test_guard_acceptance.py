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

    def test_other_branches(self):
        self.git(self.repo, "checkout", "-q", "-b", "qa/63")
        with self.case("same file on qa/<n> allowed — that is the road"):
            self.assertAllowed(self.edit(self.repo, "Edit", ACCEPTANCE_FILE))
        self.git(self.repo, "checkout", "-q", "-b", "feat/63")
        with self.case("feat branch unaffected"):
            self.assertAllowed(self.edit(self.repo, "Edit", ACCEPTANCE_FILE))
