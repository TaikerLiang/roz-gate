"""guard-blind (Bash, Read, Glob, Grep): rule E -- the fidelity dispatch is
blind while the dispatching command's marker exists (1.16.0; D2 measured 4/5
on prose)."""

from hooktest import HookTest

# D2 run-4's exact command.
RUN4 = "git status --short && git rev-parse --abbrev-ref HEAD && cat src/app.txt"

# (name, command, stderr substring) -- Bash calls under the marker.
BASH_DENIED = [
    ("rule E: D2 run-4's exact command under the marker denied", RUN4, "implementation-blind"),
    ("rule E: message states the remedy (report it as a finding)", RUN4, "report it as a finding"),
    ("rule E: message names the agent when the payload carries one", RUN4, "agent: roz-gate:qa"),
    ("rule E: git checkout feat/5 under the marker denied", "git checkout feat/5", "feat/ ref"),
    ("rule E: git diff qa/5...feat/5 denied", "git diff qa/5...feat/5 -- tests/", "feat/ ref"),
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

        self.marker.unlink()
        with self.case("rule E: marker removed — the same read is allowed again"):
            self.assertAllowed(self.run_bash(RUN4))
        with self.case("rule E: outside any git repo the prefilter exits 0"):
            self.assertAllowed(self.run_bash(RUN4, self.new_dir()))
