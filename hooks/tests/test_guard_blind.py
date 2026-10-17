"""guard-blind (Bash, Read, Glob, Grep): rule E -- the fidelity dispatch is
blind while the dispatching command's marker exists (1.16.0; D2 measured 4/5
on prose)."""

from hooktest import HookTest, config_block

# D2 run-4's exact command.
RUN4 = "git status --short && git rev-parse --abbrev-ref HEAD && cat src/app.txt"

# (name, command, stderr substring) -- Bash calls under the marker.
BASH_DENIED = [
    ("rule E: D2 run-4's exact command under the marker denied", RUN4, "implementation-blind"),
    ("rule E: message states the remedy (report it as a finding)", RUN4, "report it as a finding"),
    ("rule E: message names the agent when the payload carries one", RUN4, "agent: roz-gate:qa"),
    ("rule E: git checkout feat/5 under the marker denied", "git checkout feat/5", "feat/ ref"),
    ("rule E: git diff qa/5...feat/5 denied", "git diff qa/5...feat/5 -- tests/", "feat/ ref"),
    # Commands work in linked worktrees (issue #37); a worktree on a feat/ ref is a touch.
    ("rule E: git worktree remove of the feat/ worktree under the marker denied",
     "git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/feat/5",
     "feat/ ref"),
    ("rule E: cd into a worktree then checkout feat/5 denied",
     "cd $(git rev-parse --git-common-dir)/roz-gate/wt/qa/5 && git checkout feat/5", "feat/ ref"),
    ("rule E: a read after an echo mention still denied",
     'echo "excluding src/" && cat src/app.txt', "read of src/"),
    # echo/printf are commands, never arguments (codex, PR #11: `grep echo src/app.txt` passed).
    ("rule E: grep echo src/app.txt denied (echo as an argument)",
     "grep echo src/app.txt", "read of src/"),
    ("rule E: grep -n echo src/a.py denied", "grep -n echo src/a.py", "read of src/"),
    ("rule E: printf_helper src/x denied (word inside a token)",
     "printf_helper src/x", "read of src/"),
    ("rule E: cat src/app.txt | grep printf still denied",
     "cat src/app.txt | grep printf", "read of src/"),
]
# (name, command) -- Bash calls under the marker that name src/ without reading it.
BASH_ALLOWED = [
    ("rule E: exclusion form grep -v '^src/' allowed", "git ls-files | grep -v '^src/'"),
    # Mention is not use, third form (D2 re-run under 1.16.0: the only denial).
    ("rule E: the re-run's exact echo-mention command allowed",
     'git ls-files && echo "--- grep fixtures (tracked files, excluding src/)" && '
     "git grep -n -E 'expires' -- ':!src/**' ; "
     'echo "--- diff of fix" && git show e61367c -- tests/acceptance/'),
    ("rule E: a comment mentioning src/ allowed", "# never read src/ here\ngit status"),
    ("rule E: echo mention then ls allowed", 'echo "excluding src/" && ls tests'),
    ("rule E: FOO=1 echo src/ && ls allowed (env-assignment prefix)", "FOO=1 echo src/ && ls"),
    ("rule E: ls && echo src/ | cat allowed (echo after &&)", "ls && echo src/ | cat"),
    ("rule E: exclusion pathspec ':!src/**' allowed", "git grep -n price -- ':!src/**'"),
    ("rule E: qa/<n> work — tests and spec docs — allowed",
     "cat tests/acceptance/test_expiry.py && git status"),
    ("rule E: the command's own qa/<n> worktree allowed",
     "git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/qa/5 -b qa/5 origin/spec/5"),
    ("rule E: git -C the qa/<n> worktree status allowed",
     "git -C $(git rev-parse --git-common-dir)/roz-gate/wt/qa/5 status --short"),
]


class RuleE_FidelityDispatchIsBlind(HookTest):
    """The repo is checked out on qa/5 with feat/5 beside it. The steps run in
    order: marker off, on, then off again."""

    guard = "guard-blind"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"src/app.txt": "demo\n", "tests/acceptance/test_expiry.py": "# S1\n"}, commit=True)
        (self.repo / "sub").mkdir()
        self.git(self.repo, "branch", "-q", "feat/5")
        self.git(self.repo, "checkout", "-q", "-b", "qa/5")
        self.marker = self.repo / ".git/roz-gate/fidelity-dispatch"
        # The reviewer is dispatched into the qa worktree (issue #37): a
        # linked worktree whose own --git-dir is .git/worktrees/<name>.
        self.wt = self.repo / ".git/roz-gate/wt/spec/5"
        self.git(self.repo, "worktree", "add", "-q", str(self.wt), "-b", "spec/5")

    def tool(self, tool, cwd=None, **tool_input):
        return self.call(tool, tool_input, cwd or self.repo, agent_type="roz-gate:qa")

    def run_bash(self, command, cwd=None):
        return self.tool("Bash", cwd, command=command)

    def test_rule_e(self):
        repo = self.repo
        with self.case("rule E: D2 run-4's exact command without a marker allowed"):
            self.assertAllowed(self.run_bash(RUN4))

        self.write(self.marker, "issue=5\n")  # the dispatching command's marker
        for name, cmd, says in BASH_DENIED:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), says)
        with self.case("rule E: the marker governs a call whose cwd is a linked worktree "
                       "(codex, PR #53: --git-dir there is worktrees/<name>)"):
            self.assertDenied(self.run_bash("cat src/app.txt", cwd=self.wt), "read of src/")
        with self.case("rule E: Read of an absolute src/ path denied"):
            self.assertDenied(self.tool("Read", file_path=str(repo / "src/app.txt")),
                              "Read under src/")
        with self.case("rule E: Grep with path src/ denied"):
            self.assertDenied(self.tool("Grep", pattern="price", path="src/"), "Grep under src/")
        with self.case("rule E: Glob under src/ denied"):
            self.assertDenied(self.tool("Glob", pattern="src/**/*.py"), "Glob under src/")
        for name, cmd in BASH_ALLOWED:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        with self.case("rule E: Read of a spec doc allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(repo / "docs/specs/5/spec.md")))
        with self.case("rule E: judged from a subdirectory (marker found via git dir)"):
            self.assertDenied(self.run_bash(RUN4, repo / "sub"), "implementation-blind")
        with self.case("rule E: stale marker still denies and names the marker file"):
            self.assertDenied(self.run_bash(RUN4), "roz-gate/fidelity-dispatch")

        # branch_template (#75): the marker names the bound implementation ref.
        self.write(self.marker, "issue=5\nfeat=fix/pwliangc/5/1\n")
        with self.case("rule E: git checkout of the marker's ref denied"):
            self.assertDenied(self.run_bash("git checkout fix/pwliangc/5/1"),
                              "fix/pwliangc/5/1, the implementation branch")
        with self.case("rule E: git diff test/…...fix/… (the marker's ref) denied"):
            self.assertDenied(self.run_bash(
                "git diff test/pwliangc/5/1...fix/pwliangc/5/1 -- tests/"), "implementation branch")
        with self.case("rule E: git log origin/<marker ref> denied (a leading origin/ is "
                       "that ref)"):
            self.assertDenied(self.run_bash("git log origin/fix/pwliangc/5/1 --oneline"),
                              "implementation branch")
        with self.case("rule E: git worktree remove of the marker ref's worktree denied"):
            self.assertDenied(self.run_bash(
                "git worktree remove --force $(git rev-parse --git-common-dir)"
                "/roz-gate/wt/fix/pwliangc/5/1"),
                "implementation branch")
        with self.case("rule E: the feat/ literal stays denied under a templated marker"):
            self.assertDenied(self.run_bash("git checkout feat/5"), "feat/ ref")
        with self.case("rule E: a longer sequence of the same issue is not the marker's ref"):
            self.assertAllowed(self.run_bash("git log fix/pwliangc/5/10 --oneline"))
        with self.case("rule E: the templated qa branch (type test) allowed"):
            self.assertAllowed(self.run_bash("git diff test/pwliangc/5/1 -- tests/"))
        with self.case("rule E: a prompt that MENTIONS the ref is not a git action"):
            self.assertAllowed(self.run_bash('echo "do not touch fix/pwliangc/5/1" && ls tests'))
        with self.case("rule E: src/ read still denied under a templated marker"):
            self.assertDenied(self.run_bash(RUN4), "read of src/")

        self.marker.unlink()
        with self.case("rule E: marker removed — the same read is allowed again"):
            self.assertAllowed(self.run_bash(RUN4))
        with self.case("rule E: outside any git repo the prefilter exits 0"):
            self.assertAllowed(self.run_bash(RUN4, self.new_dir()))


class RuleE_MultiModuleSuite(HookTest):
    """#94: a multi-module Maven/Gradle layout keeps the suite under
    `<module>/src/test/…`; the first cut of the exemption required `src` to be
    the FIRST segment, so every such repo was denied its own suite. The deny
    side needs nothing: `<module>/src/main/…` is a read of src/ either way.
    The block lives in CLAUDE.local.md here — the two homes (#94), as ADMC
    keeps it."""

    guard = "guard-blind"
    SUITE = "dlh-api/console/src/test/java/acme/acceptance"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": "# Project\n",
             "CLAUDE.local.md": config_block(forge="github", acceptance_dir=self.SUITE),
             "dlh-api/console/src/main/java/acme/App.java": "class App {}\n",
             "dlh-api/console/src/test/java/acme/acceptance/ExpiryTest.java":
                 "// @Traces(5, S1)\n",
             "dlh-api/console/src/test/java/acme/unit/UnitTest.java": "// unit\n",
             "dlh-api/other/src/main/java/acme/Other.java": "class Other {}\n"},
            commit=True, branch="qa/5")
        self.write(self.repo / ".git/roz-gate/fidelity-dispatch", "issue=5\n")

    def tool(self, tool, cwd=None, **tool_input):
        return self.call(tool, tool_input, cwd or self.repo, agent_type="roz-gate:reviewer")

    def run_bash(self, command, cwd=None):
        return self.tool("Bash", cwd, command=command)

    def test_suite_is_readable(self):
        repo, suite = self.repo, self.SUITE
        for name, cmd in [
            ("multi-module: cat of a suite file allowed (block in CLAUDE.local.md)",
             "cat %s/ExpiryTest.java" % suite),
            ("multi-module: grep over the suite dir allowed", "grep -n Traces %s/" % suite),
            ("multi-module: ./-prefixed suite path allowed", "cat ./%s/ExpiryTest.java" % suite),
            ("multi-module: absolute suite path allowed",
             "cat %s/%s/ExpiryTest.java" % (repo, suite)),
            ("multi-module: $(git rev-parse --show-toplevel)/<suite> allowed",
             "cat $(git rev-parse --show-toplevel)/%s/ExpiryTest.java" % suite),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        with self.case("multi-module: Read of the absolute suite file allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(repo / suite / "ExpiryTest.java")))
        with self.case("multi-module: Grep with the suite as path allowed"):
            self.assertAllowed(self.tool("Grep", pattern="Traces", path=suite))

    def test_implementation_stays_denied(self):
        repo, suite = self.repo, self.SUITE
        for name, cmd in [
            ("multi-module: the same module's src/main denied",
             "cat dlh-api/console/src/main/java/acme/App.java"),
            ("multi-module: a sibling module's src/main denied",
             "cat dlh-api/other/src/main/java/acme/Other.java"),
            ("multi-module: the same module's unit tests (not the suite) denied",
             "cat dlh-api/console/src/test/java/acme/unit/UnitTest.java"),
            ("multi-module: a suite file AND a src/main file in one command denied",
             "cat %s/ExpiryTest.java dlh-api/other/src/main/java/acme/Other.java" % suite),
            ("multi-module: a climb out of the suite denied",
             "cat %s/../../../../main/java/acme/App.java" % suite),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of src/")
        with self.case("multi-module: Read of the same module's src/main denied"):
            self.assertDenied(self.tool("Read", file_path=str(
                repo / "dlh-api/console/src/main/java/acme/App.java")), "Read under src/")
        with self.case("multi-module: the deny message names the readable suite"):
            self.assertDenied(self.run_bash("cat dlh-api/other/src/main/java/acme/Other.java"),
                              "`%s` is readable here" % suite)

    def test_suite_in_a_linked_worktree(self):
        """#107: the dispatch runs in the qa/<n> worktree (B5b), the Read tool's
        paths are absolute and a sub-agent's Bash cwd is the session's — the
        hook fires from the main checkout. The suite resolves under every
        tree of the repo but the implementation worktree."""
        repo, suite = self.repo, self.SUITE
        qa = repo / ".git/roz-gate/wt/qa/73"
        feat = repo / ".git/roz-gate/wt/feat/73"
        fix = repo / ".git/roz-gate/wt/fix/paul/73/1"
        self.git(repo, "worktree", "add", "-q", str(qa), "-b", "qa/73")
        self.git(repo, "worktree", "add", "-q", str(feat), "-b", "feat/73")
        self.git(repo, "worktree", "add", "-q", str(fix), "-b", "fix/paul/73/1")
        main_src = "dlh-api/console/src/main/java/acme/App.java"
        for name, cmd in [
            ("worktree: cat of the qa/<n> worktree's suite, cwd = main checkout, allowed",
             "cat %s/%s/ExpiryTest.java" % (qa, suite)),
            ("worktree: grep over the qa/<n> worktree's suite dir, cwd = main checkout, allowed",
             "grep -rn Traces %s/%s/" % (qa, suite)),
            ("worktree: ls of the qa/<n> worktree's suite dir itself allowed",
             "ls %s/%s" % (qa, suite)),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        with self.case("worktree: Read of the qa/<n> worktree's suite, cwd = main checkout, "
                       "allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(qa / suite / "ExpiryTest.java")))
        with self.case("worktree: Grep with the qa/<n> worktree's suite as path allowed"):
            self.assertAllowed(self.tool("Grep", pattern="Traces", path=str(qa / suite)))
        with self.case("worktree: Glob under the qa/<n> worktree's suite allowed"):
            self.assertAllowed(self.tool("Glob", pattern=str(qa / suite) + "/**/*.java"))
        with self.case("worktree: cwd = the qa/<n> worktree, the main checkout's suite allowed"):
            self.assertAllowed(
                self.tool("Read", qa, file_path=str(repo / suite / "ExpiryTest.java")))
        with self.case("worktree: cwd = the qa/<n> worktree, its own suite relative allowed"):
            self.assertAllowed(self.run_bash("cat %s/ExpiryTest.java" % suite, cwd=qa))
        for name, cmd in [
            ("worktree: the qa/<n> worktree's src/main denied", "cat %s/%s" % (qa, main_src)),
            ("worktree: the qa/<n> worktree's unit tests (not the suite) denied",
             "cat %s/dlh-api/console/src/test/java/acme/unit/UnitTest.java" % qa),
            ("worktree: a climb out of the qa/<n> worktree's suite denied",
             "cat %s/%s/../../../../main/java/acme/App.java" % (qa, suite)),
            ("worktree: the qa/<n> suite AND the main checkout's src/main in one command denied",
             "cat %s/%s/ExpiryTest.java %s" % (qa, suite, main_src)),
            ("worktree: the feat/<n> worktree's suite is not a readable tree — denied",
             "cat %s/%s/ExpiryTest.java" % (feat, suite)),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of src/")
        with self.case("worktree: Read of the qa/<n> worktree's src/main denied"):
            self.assertDenied(self.tool("Read", file_path=str(qa / main_src)), "Read under src/")
        with self.case("worktree: Read of the feat/<n> worktree's suite denied"):
            self.assertDenied(self.tool("Read", file_path=str(feat / suite / "ExpiryTest.java")),
                              "Read under src/")
        # The hook's own tree is filtered too (codex review, PR #110): fired
        # from the implementation worktree, its suite is still not readable.
        with self.case("worktree: cwd = the feat/<n> worktree, its own suite relative — denied"):
            self.assertDenied(self.run_bash("cat %s/ExpiryTest.java" % suite, cwd=feat),
                              "read of src/")
        with self.case("worktree: cwd = the feat/<n> worktree, Read of its own suite denied"):
            self.assertDenied(
                self.tool("Read", feat, file_path=str(feat / suite / "ExpiryTest.java")),
                "Read under src/")
        with self.case("worktree: cwd = the feat/<n> worktree, the qa/<n> worktree's suite "
                       "allowed"):
            self.assertAllowed(
                self.tool("Read", feat, file_path=str(qa / suite / "ExpiryTest.java")))
        with self.case("worktree: a templated implementation branch's tree is readable "
                       "until the marker names it"):
            self.assertAllowed(self.tool("Read", file_path=str(fix / suite / "ExpiryTest.java")))
        self.write(repo / ".git/roz-gate/fidelity-dispatch", "issue=73\nfeat=fix/paul/73/1\n")
        with self.case("worktree: the tree on the marker's feat= ref is not readable — denied"):
            self.assertDenied(self.tool("Read", file_path=str(fix / suite / "ExpiryTest.java")),
                              "Read under src/")
        with self.case("worktree: the qa/<n> worktree's suite still allowed under that marker"):
            self.assertAllowed(self.tool("Read", file_path=str(qa / suite / "ExpiryTest.java")))
        with self.case("worktree: cwd = the marker's tree, its own suite relative — denied"):
            self.assertDenied(self.run_bash("cat %s/ExpiryTest.java" % suite, cwd=fix),
                              "read of src/")

    def test_module_src_exempts_nothing(self):
        bare = self.new_repo(
            {"CLAUDE.local.md": config_block(forge="github", acceptance_dir="dlh-api/console/src"),
             "dlh-api/console/src/main/java/acme/App.java": "class App {}\n"},
            commit=True, branch="qa/5")
        self.write(bare / ".git/roz-gate/fidelity-dispatch", "issue=5\n")
        with self.case("multi-module: acceptance_dir <module>/src exempts nothing"):
            self.assertDenied(self.run_bash("cat dlh-api/console/src/main/java/acme/App.java",
                                            bare), "read of src/")


class RuleE_SuiteUnderSrc(HookTest):
    """Issue #81 (1.29.1): a Maven/Gradle layout keeps the acceptance suite
    under src/test/…; the suite is what the fidelity dispatch audits and is
    never a read of the implementation. The repo is checked out on qa/5 with
    the marker on; `acceptance_dir` names the suite."""

    guard = "guard-blind"
    SUITE = "src/test/java/acme/acceptance"
    CFG = config_block(forge="github", acceptance_dir="src/test/java/acme/acceptance")

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": self.CFG,
             "src/main/java/acme/App.java": "class App {}\n",
             "src/test/java/acme/acceptance/ExpiryTest.java": "// @Traces(5, S1)\n",
             "src/test/java/acme/acceptance-old/OldTest.java": "// old\n",
             "src/test/java/acme/unit/UnitTest.java": "// unit\n"},
            commit=True, branch="qa/5")
        self.write(self.repo / ".git/roz-gate/fidelity-dispatch", "issue=5\n")

    def tool(self, tool, cwd=None, **tool_input):
        return self.call(tool, tool_input, cwd or self.repo, agent_type="roz-gate:reviewer")

    def run_bash(self, command, cwd=None):
        return self.tool("Bash", cwd, command=command)

    def test_suite_is_readable(self):
        repo, suite = self.repo, self.SUITE
        for name, cmd in [
            ("suite: cat of a suite file allowed", "cat %s/ExpiryTest.java" % suite),
            ("suite: grep over the suite dir allowed", "grep -n Traces %s/" % suite),
            ("suite: ls of the suite dir itself allowed", "ls %s" % suite),
            ("suite: ./-prefixed suite path allowed", "cat ./%s/ExpiryTest.java" % suite),
            ("suite: absolute suite path allowed", "cat %s/%s/ExpiryTest.java" % (repo, suite)),
            ("suite: $(git rev-parse --show-toplevel)/<suite> allowed",
             "cat $(git rev-parse --show-toplevel)/%s/ExpiryTest.java" % suite),
            ("suite: qa/<n> work outside src/ still allowed", "cat docs/specs/5/spec.md"),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        with self.case("suite: Read of the absolute suite file allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(repo / suite / "ExpiryTest.java")))
        with self.case("suite: Grep with the suite as path allowed"):
            self.assertAllowed(self.tool("Grep", pattern="Traces", path=suite))
        with self.case("suite: Glob under the suite allowed"):
            self.assertAllowed(self.tool("Glob", pattern=suite + "/**/*.java"))

    def test_implementation_stays_denied(self):
        repo, suite = self.repo, self.SUITE
        for name, cmd in [
            ("suite: src/main still denied", "cat src/main/java/acme/App.java"),
            ("suite: a suite file AND a src/main file in one command denied",
             "cat %s/ExpiryTest.java src/main/java/acme/App.java" % suite),
            ("suite: the near-miss sibling acceptance-old denied",
             "cat src/test/java/acme/acceptance-old/OldTest.java"),
            ("suite: a unit test under src/test is not the suite — denied",
             "cat src/test/java/acme/unit/UnitTest.java"),
            ("suite: a climb out of the suite (../../../main) denied",
             "cat %s/../../../main/java/acme/App.java" % suite),
            ("suite: another tree's src/ is not the suite — denied",
             "cat vendor/%s/ExpiryTest.java" % suite),
            # The operand ends at a shell control character (codex, PR #84).
            ("suite: `cat <suite>/T;cat<src/main/App` — the second read denied",
             "cat %s/ExpiryTest.java;cat<src/main/java/acme/App.java" % suite),
            ("suite: `cat <suite>/T|cat src/main/App` denied",
             "cat %s/ExpiryTest.java|cat src/main/java/acme/App.java" % suite),
            ("suite: `cat <suite>/T&&cat src/main/App` denied",
             "cat %s/ExpiryTest.java&&cat src/main/java/acme/App.java" % suite),
            ("suite: `cat <suite>/T>src/main/x` names src/main — denied",
             "cat %s/ExpiryTest.java>src/main/java/acme/Out.java" % suite),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of src/")
        # A symlink inside the suite that points out of it (codex, PR #84).
        (repo / suite / "impl").symlink_to("../../../../main")
        with self.case("suite: a symlink inside the suite pointing at src/main — Bash denied"):
            self.assertDenied(self.run_bash("cat %s/impl/java/acme/App.java" % suite),
                              "read of src/")
        with self.case("suite: the same symlink, absolute — Bash denied"):
            self.assertDenied(self.run_bash("cat %s/%s/impl/java/acme/App.java" % (repo, suite)),
                              "read of src/")
        with self.case("suite: the same symlink — Read denied"):
            self.assertDenied(self.tool("Read", file_path=str(
                repo / suite / "impl/java/acme/App.java")), "Read under src/")
        with self.case("suite: a symlink inside the suite that stays inside — allowed"):
            (repo / suite / "alias").symlink_to(".")
            self.assertAllowed(self.run_bash("cat %s/alias/ExpiryTest.java" % suite))
        with self.case("suite: the deny message names the readable suite"):
            self.assertDenied(self.run_bash("cat src/main/java/acme/App.java"),
                              "its `%s` is readable here" % suite)
        with self.case("suite: Read of src/main denied"):
            self.assertDenied(self.tool("Read", file_path=str(
                repo / "src/main/java/acme/App.java")), "Read under src/")
        with self.case("suite: Read of a climb out of the suite denied"):
            self.assertDenied(self.tool("Read", file_path=str(
                repo / suite / "../../../main/java/acme/App.java")), "Read under src/")
        with self.case("suite: Glob src/** denied"):
            self.assertDenied(self.tool("Glob", pattern="src/**"), "Glob under src/")
        with self.case("suite: Grep with path src/ denied"):
            self.assertDenied(self.tool("Grep", pattern="Traces", path="src/"), "Grep under src/")

    def test_config_edges(self):
        for name, cfg in [
            ("suite: acceptance_dir outside src/ exempts nothing — cat src/app.txt denied",
             config_block(forge="github", acceptance_dir="tests/acceptance")),
            ("suite: acceptance_dir = src would swallow the rule — exempts nothing",
             config_block(forge="github", acceptance_dir="src")),
            ("suite: acceptance_dir = src/ (trailing slash) exempts nothing",
             config_block(forge="github", acceptance_dir="src/")),
            ("suite: a bullet outside the block is not config",
             config_block(forge="github", acceptance_dir="tests/acceptance")
             + "\n## Notes\n\n- acceptance_dir: src/test/java/acme/acceptance\n"),
        ]:
            repo = self.new_repo({"CLAUDE.md": cfg, "src/app.txt": "demo\n",
                                  "src/test/java/acme/acceptance/T.java": "// t\n"},
                                 commit=True, branch="qa/5")
            self.write(repo / ".git/roz-gate/fidelity-dispatch", "issue=5\n")
            with self.case(name):
                self.assertDenied(self.run_bash("cat src/app.txt", repo), "read of src/")
            with self.case(name.split(" — ")[0] + " — the suite path is a read there too"):
                self.assertDenied(self.run_bash("cat src/test/java/acme/acceptance/T.java", repo),
                                  "read of src/")
        no_cfg = self.new_repo({"src/app.txt": "demo\n"}, commit=True, branch="qa/5")
        self.write(no_cfg / ".git/roz-gate/fidelity-dispatch", "issue=5\n")
        with self.case("suite: no CLAUDE.md — the rule is whole, src/ denied"):
            self.assertDenied(self.run_bash("cat src/app.txt", no_cfg), "read of src/")


class RuleE_TestPortIsReadable(HookTest):
    """#125 (1.40.0): the contract's test port may live outside the suite —
    ADMC #11's sat in an existing unit-test file under src/test/… — and the
    dispatch audits the suite that drives it. The dispatching command copies
    `technical-spec.md`'s `**Test port** — <path>` line into the marker as
    `read=<path>` lines; a read under one of them is exempt exactly as a
    read under the suite is. Maven layout: the suite under src/test/…, the
    port file beside it, a port directory, a unit test that is neither."""

    guard = "guard-blind"
    SUITE = "src/test/java/acme/acceptance"
    PORT = "src/test/java/acme/port/OfferPortTest.java"
    KIT = "src/test/java/acme/portkit"
    UNIT = "src/test/java/acme/unit/UnitTest.java"
    MAIN = "src/main/java/acme/App.java"
    MARKER = "issue=5\nfeat=feat/5\nread=%s\nread=%s\n" % (PORT, KIT)

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir=self.SUITE),
             self.MAIN: "class App {}\n",
             self.SUITE + "/ExpiryTest.java": "// @Traces(5, S1)\n",
             self.PORT: "// the port: advance_clock, run_expiry_sweep, get_offer_state\n",
             self.PORT + ".bak": "// stale copy\n",
             "src/test/java/acme/port/OfferPortTestX.java": "// not the port\n",
             self.KIT + "/Kit.java": "// port helpers\n",
             self.UNIT: "// unit\n"},
            commit=True, branch="qa/5")
        self.marker = self.repo / ".git/roz-gate/fidelity-dispatch"
        self.write(self.marker, self.MARKER)

    def tool(self, tool, cwd=None, **tool_input):
        return self.call(tool, tool_input, cwd or self.repo, agent_type="roz-gate:reviewer")

    def run_bash(self, command, cwd=None):
        return self.tool("Bash", cwd, command=command)

    def test_port_is_readable(self):
        repo, port, kit = self.repo, self.PORT, self.KIT
        for name, cmd in [
            ("port: cat of the port file allowed", "cat %s" % port),
            ("port: grep over the port file allowed", "grep -n advance_clock %s" % port),
            ("port: sed -n over the port file allowed", "sed -n '1,40p' %s" % port),
            ("port: ./-prefixed port path allowed", "cat ./%s" % port),
            ("port: absolute port path allowed", "cat %s/%s" % (repo, port)),
            ("port: a child of the port directory allowed", "cat %s/Kit.java" % kit),
            ("port: ls of the port directory itself allowed", "ls %s" % kit),
            ("port: the suite AND the port in one command allowed",
             "cat %s/ExpiryTest.java %s" % (self.SUITE, port)),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        with self.case("port: Read of the absolute port file allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(repo / port)))
        with self.case("port: Read of a file under the port directory allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(repo / kit / "Kit.java")))
        with self.case("port: Grep with the port directory as path allowed"):
            self.assertAllowed(self.tool("Grep", pattern="helpers", path=kit))
        with self.case("port: Glob under the port directory allowed"):
            self.assertAllowed(self.tool("Glob", pattern=str(repo / kit) + "/**/*.java"))
        with self.case("port: the suite stays readable beside the port"):
            self.assertAllowed(self.run_bash("cat %s/ExpiryTest.java" % self.SUITE))

    def test_everything_else_stays_denied(self):
        repo, port, kit = self.repo, self.PORT, self.KIT
        for name, cmd in [
            ("port: a unit test beside the port (not listed) denied", "cat %s" % self.UNIT),
            ("port: src/main denied", "cat %s" % self.MAIN),
            ("port: a climb out of the port directory denied",
             "cat %s/../../../../main/java/acme/App.java" % kit),
            ("port: the port AND a src/main file in one command denied",
             "cat %s %s" % (port, self.MAIN)),
            ("port: a sibling spelled with the port's name as a prefix denied",
             "cat src/test/java/acme/port/OfferPortTestX.java"),
            ("port: a stale copy of the port (.bak) denied", "cat %s.bak" % port),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of src/")
        with self.case("port: Read of the unit test beside the port denied"):
            self.assertDenied(self.tool("Read", file_path=str(repo / self.UNIT)),
                              "Read under src/")
        with self.case("port: Read of a climb out of the port directory denied"):
            self.assertDenied(self.tool("Read", file_path=str(
                repo / kit / "../../../../main/java/acme/App.java")), "Read under src/")
        with self.case("port: the deny message names the suite AND the port"):
            r = self.run_bash("cat %s" % self.MAIN)
            self.assertDenied(r, "`%s` is readable here" % self.SUITE)
            self.assertDenied(r, "the port it names: `%s`, `%s`" % (port, kit))
        with self.case("port: git action on the feat/ ref still denied"):
            self.assertDenied(self.run_bash("git diff qa/5...feat/5 -- %s" % port), "feat/ ref")

    def test_port_in_a_linked_worktree(self):
        """#107's rule for the port: the dispatch runs in the qa/<n> worktree,
        the Read tool's paths are absolute, a sub-agent's Bash cwd is the
        session's — the port resolves under every tree but the implementation's."""
        repo, port, kit = self.repo, self.PORT, self.KIT
        qa = repo / ".git/roz-gate/wt/qa/73"
        feat = repo / ".git/roz-gate/wt/feat/73"
        self.git(repo, "worktree", "add", "-q", str(qa), "-b", "qa/73")
        self.git(repo, "worktree", "add", "-q", str(feat), "-b", "feat/73")
        self.write(self.marker, "issue=73\nfeat=feat/73\nread=%s\nread=%s\n" % (port, kit))
        with self.case("port: cat of the qa/<n> worktree's port, cwd = main checkout, allowed"):
            self.assertAllowed(self.run_bash("cat %s/%s" % (qa, port)))
        with self.case("port: Read of the qa/<n> worktree's port, cwd = main checkout, allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(qa / port)))
        with self.case("port: cwd = the qa/<n> worktree, the port relative allowed"):
            self.assertAllowed(self.run_bash("cat %s" % port, cwd=qa))
        with self.case("port: Grep with the qa/<n> worktree's port directory allowed"):
            self.assertAllowed(self.tool("Grep", pattern="helpers", path=str(qa / kit)))
        with self.case("port: the feat/<n> worktree's port is not a readable tree — denied"):
            self.assertDenied(self.run_bash("cat %s/%s" % (feat, port)), "read of src/")
        with self.case("port: cwd = the feat/<n> worktree, its own port relative — denied"):
            self.assertDenied(self.run_bash("cat %s" % port, cwd=feat), "read of src/")
        with self.case("port: the qa/<n> worktree's unit test (not listed) denied"):
            self.assertDenied(self.run_bash("cat %s/%s" % (qa, self.UNIT)), "read of src/")

    def test_marker_edges(self):
        port = self.PORT
        self.write(self.marker, "issue=5\nfeat=feat/5\n")
        with self.case("port: no read= line — the port is denied exactly as before #125"):
            self.assertDenied(self.run_bash("cat %s" % port), "read of src/")
        with self.case("port: no read= line — the deny message names no port"):
            r = self.run_bash("cat %s" % port)
            self.assertDenied(r, "`%s` is readable here)" % self.SUITE)
        self.write(self.marker, "issue=5\nfeat=feat/5\nread=src\n")
        with self.case("port: read=src (the segment itself) exempts nothing"):
            self.assertDenied(self.run_bash("cat %s" % self.MAIN), "read of src/")
        self.write(self.marker, "issue=5\nfeat=feat/5\nread=tests/port.py\n")
        with self.case("port: read=tests/port.py exempts nothing and nothing denies it"):
            self.assertAllowed(self.run_bash("cat tests/port.py"))
            self.assertDenied(self.run_bash("cat %s" % port), "read of src/")
        self.write(self.marker, "issue=5\nfeat=feat/5\nread= ./%s \n" % port)
        with self.case("port: a read= line with ./ and spaces is normalized"):
            self.assertAllowed(self.run_bash("cat %s" % port))
        self.write(self.marker, "issue=5\nfeat=feat/5\nread=`%s`\n" % port)
        with self.case("port: a read= line in backticks is normalized"):
            self.assertAllowed(self.run_bash("cat %s" % port))
        self.write(self.marker, "issue=5\nread=%s\n" % port)
        with self.case("port: the 1.16–1.28 marker shape plus read= — the port readable, feat/ "
                       "denied"):
            self.assertAllowed(self.run_bash("cat %s" % port))
            self.assertDenied(self.run_bash("git checkout feat/5"), "feat/ ref")
        self.marker.unlink()
        with self.case("port: marker removed — everything allowed again"):
            self.assertAllowed(self.run_bash("cat %s" % self.MAIN))


class RuleE_QaDispatchSeat(HookTest):
    """2.0.0 (#140): QA writes its suite on a qa/<n> cut AFTER the
    implementation landed on the spec branch, so the branch carries the code
    and the topology no longer protects — the QA dispatch runs under the
    same marker with `seat=qa`. The predicate is unchanged: QA may RUN its
    suite (`acceptance_test` names no src/ operand) and read the suite and
    the port; it may not read the code it runs against, nor touch the
    implementation ref. The deny message names the dispatch and its brief."""

    guard = "guard-blind"
    SUITE = "src/test/java/acme/acceptance"
    PORT = "src/test/java/acme/port/OfferPort.java"
    MAIN = "src/main/java/acme/App.java"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir=self.SUITE),
             self.MAIN: "class App {}\n",
             self.SUITE + "/OfferAcceptanceTest.java": "// @Traces(5, S1)\n",
             self.PORT: "// the port: seedOffer, advanceClock, priceCart\n",
             "src/test/java/acme/unit/UnitTest.java": "// unit\n",
             "docs/specs/5/technical-spec.md": "# tech spec\n"},
            commit=True)
        self.git(self.repo, "branch", "-q", "feat/5")
        self.git(self.repo, "checkout", "-q", "-b", "qa/5")
        self.marker = self.repo / ".git/roz-gate/fidelity-dispatch"
        self.write(self.marker, "issue=5\nfeat=feat/5\nread=%s\nseat=qa\n" % self.PORT)

    def tool(self, tool, cwd=None, **tool_input):
        return self.call(tool, tool_input, cwd or self.repo, agent_type="roz-gate:qa")

    def run_bash(self, command, cwd=None):
        return self.tool("Bash", cwd, command=command)

    def test_qa_may_run_but_not_read(self):
        repo = self.repo
        for name, cmd in [
            ("seat=qa: running the acceptance suite (mvnw -Dtest=…AcceptanceTest) allowed",
             "./mvnw -q test -Dtest=OfferAcceptanceTest"),
            ("seat=qa: running the suite by pattern allowed",
             "mvn -q test -Dtest='*AcceptanceTest' -Dmaven.gitcommitid.skip=true"),
            ("seat=qa: a pytest acceptance run allowed", "pytest tests/acceptance -q"),
            ("seat=qa: a read under <acceptance_dir> allowed",
             "cat %s/OfferAcceptanceTest.java" % self.SUITE),
            ("seat=qa: a read of the port the marker names allowed", "cat %s" % self.PORT),
            ("seat=qa: the spec docs allowed", "cat docs/specs/5/technical-spec.md"),
            ("seat=qa: git status in the qa worktree allowed",
             "git -C $(git rev-parse --git-common-dir)/roz-gate/wt/qa/5 status --short"),
            ("seat=qa: a test report under target/ (no src/) allowed",
             "cat target/surefire-reports/acme.acceptance.OfferAcceptanceTest.txt"),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        with self.case("seat=qa: Read of the suite file allowed"):
            self.assertAllowed(self.tool("Read", file_path=str(
                repo / self.SUITE / "OfferAcceptanceTest.java")))
        for name, cmd, says in [
            ("seat=qa: cat src/main denied", "cat %s" % self.MAIN, "read of src/"),
            ("seat=qa: the deny message names the QA dispatch", "cat %s" % self.MAIN,
             "this is a QA dispatch"),
            ("seat=qa: the deny message names the QA brief", "cat %s" % self.MAIN,
             "references/qa-brief.md"),
            ("seat=qa: the deny message still states the remedy", "cat %s" % self.MAIN,
             "report it as a finding"),
            ("seat=qa: a unit test beside the suite (not the suite, not the port) denied",
             "cat src/test/java/acme/unit/UnitTest.java", "read of src/"),
            ("seat=qa: git diff feat/5 denied", "git diff feat/5 -- src/", "feat/ ref"),
            ("seat=qa: git diff spec/5...feat/5 denied", "git diff spec/5...feat/5",
             "feat/ ref"),
            ("seat=qa: git log origin/feat/5 denied", "git log origin/feat/5 --oneline",
             "feat/ ref"),
            ("seat=qa: a grep over src/main denied", "grep -rn price src/main/", "read of src/"),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), says)
        with self.case("seat=qa: Read of src/main denied, message names the QA dispatch"):
            r = self.tool("Read", file_path=str(repo / self.MAIN))
            self.assertDenied(r, "Read under src/")
            self.assertDenied(r, "this is a QA dispatch")
        with self.case("seat=qa: Grep with path src/main denied"):
            self.assertDenied(self.tool("Grep", pattern="price", path="src/main"),
                              "Grep under src/")

    def test_seat_names_the_dispatch(self):
        for name, marker, says in [
            ("seat=reviewer: the message opens as a fidelity dispatch",
             "issue=5\nfeat=feat/5\nseat=reviewer\n", "this is a fidelity dispatch"),
            ("no seat line (the 1.x marker): a fidelity dispatch",
             "issue=5\nfeat=feat/5\n", "this is a fidelity dispatch"),
            ("an unknown seat value: a fidelity dispatch (the predicate is the same)",
             "issue=5\nfeat=feat/5\nseat=product\n", "this is a fidelity dispatch"),
            ("seat=qa in backticks is normalized",
             "issue=5\nfeat=feat/5\nseat=`qa`\n", "this is a QA dispatch"),
            ("seat=QA (case) is normalized", "issue=5\nfeat=feat/5\nseat=QA\n",
             "this is a QA dispatch"),
        ]:
            self.write(self.marker, marker)
            with self.case(name):
                self.assertDenied(self.run_bash("cat %s" % self.MAIN), says)
        with self.case("seat=reviewer: the message names the fidelity brief"):
            self.write(self.marker, "issue=5\nfeat=feat/5\nseat=reviewer\n")
            self.assertDenied(self.run_bash("cat %s" % self.MAIN), "references/fidelity-brief.md")
        with self.case("the stale-marker remedy no longer says 'fidelity dispatch' alone"):
            self.assertDenied(self.run_bash("cat %s" % self.MAIN), "Not inside a blind dispatch?")
        self.marker.unlink()
        with self.case("marker removed — src/main readable again"):
            self.assertAllowed(self.run_bash("cat %s" % self.MAIN))
