"""guard-blind rule E under `implementation_dirs` (#281, PR 2), and the tool
that renders the same list for the dispatch (`bin/roz-implementation-dirs`).

One config, one resolver (`hooks/implementation_dirs.py`), two readers: the
guard enforces the list, the tool prints it. Unset keeps `src/` — that is
the rest of test_guard_blind.py, untouched."""

import os
import subprocess
import sys

from hooktest import HOOKS, HookTest, config_block

TOOL = HOOKS.parent / "bin" / "roz-implementation-dirs"
SUITE = "app/tests/acceptance"
MARKER = "issue=5\nfeat=feat/5\nseat=qa\nread=lib/port.py\n"


def tool(cwd):
    return subprocess.run([sys.executable, str(TOOL)], cwd=str(cwd),
                          capture_output=True, text=True)


class ImplementationDirsBase(HookTest):
    guard = "guard-blind"
    DIRS = "lib, app"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", acceptance_dir=SUITE,
                                       implementation_dirs=self.DIRS),
             "README.md": "lib is where the code lives\n",
             "lib/x.py": "x = 1\n", "lib/port.py": "# the port\n", "lib/other.py": "y = 2\n",
             "app/models.py": "class M: pass\n",
             SUITE + "/test_a.py": "# S1\n",
             "src/x.py": "not the implementation here\n",
             "lib-old/x.py": "old\n", "mylib/x.py": "mine\n", "vendor/pkg/lib/x.py": "theirs\n",
             "docs/notes/n.md": "notes\n", "tools/run.sh": "true\n"})
        # Symlinks, both directions (the contract: the REAL location decides).
        os.symlink("../docs/notes", self.repo / "lib/notes")            # under lib, lands outside
        os.symlink("../lib", self.repo / "tools/impl")                  # outside, lands in lib
        os.symlink("lib/x.py", self.repo / "peek")                      # a root file → lib
        os.symlink("../../../lib", self.repo / SUITE / "impl")          # in the suite → lib
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        self.git(self.repo, "branch", "-q", "feat/5")
        self.git(self.repo, "checkout", "-q", "-b", "qa/5")
        self.wt = self.repo / ".git/roz-gate/wt/spec/5"
        self.git(self.repo, "worktree", "add", "-q", str(self.wt), "-b", "spec/5")
        self.marker = self.repo / ".git/roz-gate/fidelity-dispatch"
        self.write(self.marker, MARKER)

    def tool(self, name, cwd=None, **tool_input):
        return self.call(name, tool_input, cwd or self.repo, agent_type="roz-gate:qa")

    def run_bash(self, command, cwd=None):
        return self.tool("Bash", cwd, command=command)


class RuleE_ImplementationDirs(ImplementationDirsBase):
    def test_listed_directories_are_denied(self):
        repo, wt = self.repo, self.wt
        for name, kw, says in [
            ("dirs: Read lib/x.py (relative) denied", dict(file_path="lib/x.py"), "under lib/"),
            ("dirs: Read lib/x.py (absolute) denied", dict(file_path="%s/lib/x.py" % repo),
             "under lib/"),
            ("dirs: Read app/models.py denied", dict(file_path="app/models.py"), "under app/"),
            ("dirs: Read in the linked worktree's lib/ denied",
             dict(file_path="%s/lib/x.py" % wt), "under lib/"),
            ("dirs: Read of a file that does not exist under lib/ denied",
             dict(file_path="lib/nope.py"), "under lib/"),
        ]:
            with self.case(name):
                self.assertDenied(self.tool("Read", **kw), says)
        with self.case("dirs: Read lib/x.py from a cwd in the linked worktree denied"):
            self.assertDenied(self.tool("Read", wt, file_path="lib/x.py"), "under lib/")
        for name, t, kw in [
            ("dirs: Glob lib/**/*.py denied", "Glob", dict(pattern="lib/**/*.py")),
            ("dirs: Glob **/*.py with path lib denied", "Glob",
             dict(pattern="**/*.py", path="lib")),
            ("dirs: Glob with an absolute path under app denied", "Glob",
             dict(pattern="*.py", path="%s/app" % repo)),
            ("dirs: Grep with path lib/ denied", "Grep", dict(pattern="x", path="lib/")),
            ("dirs: Grep with glob lib/*.py denied", "Grep", dict(pattern="x", glob="lib/*.py")),
        ]:
            with self.case(name):
                self.assertDenied(self.tool(t, **kw), "implementation-blind")
        for name, cmd in [
            ("dirs: cat lib/x.py denied", "cat lib/x.py"),
            ("dirs: grep -r foo lib/ denied", "grep -r foo lib/"),
            ("dirs: cat ./lib/x.py denied", "cat ./lib/x.py"),
            ("dirs: cat $(git rev-parse --show-toplevel)/lib/x.py denied",
             "cat $(git rev-parse --show-toplevel)/lib/x.py"),
            ("dirs: an absolute path into the worktree's lib/ denied", "cat %s/lib/x.py" % wt),
            ("dirs: cat app/models.py denied", "cat app/models.py"),
            ("dirs: a read after an echo mention still denied",
             'echo "excluding lib/" && cat lib/x.py'),
            ("dirs: grep echo lib/x.py denied (echo as an argument)", "grep echo lib/x.py"),
            ("dirs: a read after a blanked heredoc body denied",
             "cat <<EOF > tests/note\nlib/ is off-limits\nEOF\ncat lib/x.py"),
            ("dirs: a read after an exclusion still denied",
             "git ls-files ':!lib/**' && cat lib/x.py"),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of ")

    def test_everything_else_is_allowed(self):
        repo = self.repo
        for name, kw in [
            ("dirs: Read src/x.py allowed — the list replaces the default",
             dict(file_path="src/x.py")),
            ("dirs: Read lib-old/x.py allowed (a look-alike name)", dict(file_path="lib-old/x.py")),
            ("dirs: Read mylib/x.py allowed", dict(file_path="mylib/x.py")),
            ("dirs: Read vendor/pkg/lib/x.py allowed (not at the root)",
             dict(file_path="vendor/pkg/lib/x.py")),
            ("dirs: Read /usr/lib/os-release allowed (another root)",
             dict(file_path="/usr/lib/os-release")),
            ("dirs: Read README.md allowed", dict(file_path="README.md")),
        ]:
            with self.case(name):
                self.assertAllowed(self.tool("Read", **kw))
        other = self.new_repo({"lib/x.py": "another repo\n"}, commit=True)
        with self.case("dirs: Read of another repository's lib/ allowed"):
            self.assertAllowed(self.tool("Read", file_path="%s/lib/x.py" % other))
        with self.case("dirs: Grep whose PATTERN is `lib/` allowed (a pattern is no path)"):
            self.assertAllowed(self.tool("Grep", pattern="lib/", path="docs"))
        for name, cmd in [
            ("dirs: cat src/x.py allowed", "cat src/x.py"),
            ("dirs: cat lib-old/x.py allowed", "cat lib-old/x.py"),
            ("dirs: cat vendor/pkg/lib/x.py allowed", "cat vendor/pkg/lib/x.py"),
            ("dirs: ls /usr/lib/ allowed", "ls /usr/lib/"),
            ("dirs: grep -rv '^lib/' . allowed (an exclusion)", "grep -rv '^lib/' ."),
            ("dirs: git ls-files ':!lib/**' allowed", "git ls-files ':!lib/**' ':!app/**'"),
            ("dirs: grep --exclude-dir=lib/ allowed", "grep -r foo . --exclude-dir=lib/"),
            ("dirs: find -not -path './lib/*' allowed", "find . -name '*.py' -not -path './lib/*'"),
            ("dirs: echo naming lib/x.py allowed (a mention)", 'echo "see lib/x.py"'),
            ("dirs: echo $(cat lib/x.py) allowed — blanked with the echo, the recorded cost",
             "echo $(cat lib/x.py)"),
            ("dirs: a # comment naming lib/ allowed", "ls tests # lib/ is off-limits"),
            ("dirs: a heredoc body naming lib/x.py allowed",
             "cat > notes.txt <<'EOF'\nNothing under lib/x.py is read\nEOF"),
            ("dirs: a forge comment body naming lib/x.py allowed",
             "gh pr comment 103 --body 'port: lib/port.py:3 returns 10'"),
            ("dirs: grep lib README.md allowed (a bare word is a pattern)", "grep lib README.md"),
            ("dirs: the acceptance command allowed", "python3 -m pytest %s -q" % SUITE),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        self.marker.unlink()
        with self.case("dirs: no marker — cat lib/x.py allowed"):
            self.assertAllowed(self.run_bash("cat lib/x.py"))
        with self.case("dirs: no marker — Read lib/x.py allowed"):
            self.assertAllowed(self.tool("Read", file_path="%s/lib/x.py" % repo))

    def test_readable_roots_under_a_listed_directory(self):
        repo, wt = self.repo, self.wt
        for name, t, kw in [
            ("roots: Read of the suite under app/ allowed", "Read",
             dict(file_path=SUITE + "/test_a.py")),
            ("roots: Read of the suite in the linked worktree allowed", "Read",
             dict(file_path="%s/%s/test_a.py" % (wt, SUITE))),
            ("roots: Glob over the suite allowed", "Glob", dict(pattern="*.py", path=SUITE)),
            ("roots: Read of the read= port lib/port.py allowed", "Read",
             dict(file_path="lib/port.py")),
            ("roots: Read of the port by absolute path allowed", "Read",
             dict(file_path="%s/lib/port.py" % repo)),
        ]:
            with self.case(name):
                self.assertAllowed(self.tool(t, **kw))
        for name, cmd in [
            ("roots: cat of the suite allowed", "cat %s/test_a.py" % SUITE),
            ("roots: cat of the port allowed", "cat lib/port.py"),
            ("roots: the suite and the port in one command allowed",
             "cat %s/test_a.py lib/port.py" % SUITE),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd))
        for name, t, kw in [
            ("roots: the suite's sibling app/models.py denied", "Read",
             dict(file_path="app/models.py")),
            ("roots: the port's sibling lib/other.py denied", "Read",
             dict(file_path="lib/other.py")),
            ("roots: a climb out of the suite denied", "Read",
             dict(file_path=SUITE + "/../../models.py")),
        ]:
            with self.case(name):
                self.assertDenied(self.tool(t, **kw), "implementation-blind")
        for name, cmd in [
            ("roots: cat of the port's sibling denied", "cat lib/port.py lib/other.py"),
            ("roots: a Bash climb out of the suite denied", "cat %s/../../models.py" % SUITE),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of ")
        with self.case("roots: the deny names the directories in force and what is readable"):
            r = self.tool("Read", file_path="lib/other.py")
            self.assertDenied(r, "`lib/`, `app/` and `feat/<n>` are off-limits")
            self.assertIn("lib/port.py", r.stderr)
            self.assertIn(SUITE, r.stderr)

    def test_symlinks_resolve_to_the_real_location(self):
        repo = self.repo
        for name, kw in [
            ("symlink: lib/notes → ../docs/notes, Read lib/notes/n.md allowed (lands outside)",
             dict(file_path="lib/notes/n.md")),
        ]:
            with self.case(name):
                self.assertAllowed(self.tool("Read", **kw))
        with self.case("symlink: cat lib/notes/n.md allowed (lands outside)"):
            self.assertAllowed(self.run_bash("cat lib/notes/n.md"))
        for name, kw in [
            ("symlink: tools/impl → ../lib, Read tools/impl/x.py denied (lands inside)",
             dict(file_path="tools/impl/x.py")),
            ("symlink: peek → lib/x.py, Read peek denied", dict(file_path="peek")),
            ("symlink: absolute path through tools/impl denied",
             dict(file_path="%s/tools/impl/other.py" % repo)),
            ("symlink: a link inside the suite that points into lib/ denied",
             dict(file_path=SUITE + "/impl/x.py")),
        ]:
            with self.case(name):
                self.assertDenied(self.tool("Read", **kw), "under lib/")
        for name, cmd in [
            ("symlink: cat tools/impl/x.py denied (lands inside)", "cat tools/impl/x.py"),
            ("symlink: cat peek denied (a symlink word is resolved)", "cat peek"),
            ("symlink: cat through the suite's link into lib/ denied",
             "cat %s/impl/x.py" % SUITE),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd), "read of lib/")
        with self.case("symlink: the port reached through tools/impl is still the port"):
            self.assertAllowed(self.tool("Read", file_path="tools/impl/port.py"))

    def test_relative_operands_resolve_against_the_cwd(self):
        # Codex review, PR #345: the hook joined a relative operand to the
        # toplevel, so from a subdirectory it judged a file the command does
        # not read — `cat ../lib/x.py` from tests/ and `cat ./x.py` from lib/
        # both passed.
        repo = self.repo
        tests, lib = repo / "app/tests", repo / "lib"
        for name, cwd, cmd in [
            ("cwd: from app/tests, cat ../../lib/x.py denied", tests, "cat ../../lib/x.py"),
            ("cwd: from lib/, cat ./x.py denied", lib, "cat ./x.py"),
            ("cwd: from lib/, cat x.py denied (a bare word in an implementation cwd)", lib,
             "cat x.py"),
            ("cwd: from lib/, grep -n x other.py denied", lib, "grep -n x other.py"),
            ("cwd: from lib/, cat lib/x.py is lib/lib/x.py — still the implementation", lib,
             "cat lib/x.py"),
        ]:
            with self.case(name):
                self.assertDenied(self.run_bash(cmd, cwd), "read of lib/")
        for name, cwd, kw in [
            ("cwd: from app/tests, Read ../../lib/x.py denied", tests,
             dict(file_path="../../lib/x.py")),
            ("cwd: from lib/, Read x.py denied", lib, dict(file_path="x.py")),
        ]:
            with self.case(name):
                self.assertDenied(self.tool("Read", cwd, **kw), "under lib/")
        with self.case("cwd: from lib/, Glob *.py (no path) denied"):
            self.assertDenied(self.tool("Glob", lib, pattern="*.py"), "under lib/")
        with self.case("cwd: from lib/, Grep with no path denied"):
            self.assertDenied(self.tool("Grep", lib, pattern="x"), "under lib/")
        for name, cwd, cmd in [
            ("cwd: from lib/, cat ./port.py allowed (the port)", lib, "cat ./port.py"),
            ("cwd: from lib/, cat port.py allowed (the port, a bare word)", lib, "cat port.py"),
            ("cwd: from lib/, cat ../README.md allowed", lib, "cat ../README.md"),
            ("cwd: from docs/, cat lib/x.py is docs/lib/x.py — not the implementation",
             repo / "docs", "cat lib/x.py"),
            ("cwd: from the suite, cat test_a.py allowed", repo / SUITE, "cat ./test_a.py"),
            ("cwd: from lib/, $(git rev-parse --show-toplevel)/README.md allowed", lib,
             "cat $(git rev-parse --show-toplevel)/README.md"),
        ]:
            with self.case(name):
                self.assertAllowed(self.run_bash(cmd, cwd))
        with self.case("cwd: from docs/, $(git rev-parse --show-toplevel)/lib/x.py denied"):
            self.assertDenied(self.run_bash(
                "cat $(git rev-parse --show-toplevel)/lib/x.py", repo / "docs"), "read of lib/")
        with self.case("cwd: from lib/, Read port.py allowed (the port)"):
            self.assertAllowed(self.tool("Read", lib, file_path="port.py"))

    def test_a_listed_directory_that_is_itself_a_symlink(self):
        repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", implementation_dirs="code",
                                       acceptance_dir="code/tests/acceptance"),
             "real/x.py": "x = 1\n", "real/port.py": "# the port\n",
             "real/tests/acceptance/test_a.py": "# S1\n"})
        os.symlink("real", repo / "code")
        self.git(repo, "add", "-A")
        self.git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        self.write(repo / ".git/roz-gate/fidelity-dispatch", "issue=5\nread=code/port.py\n")
        # Codex review, PR #345: membership resolved `code` to its real
        # place, the readable roots did not — the declared port was denied
        # by the message that named it readable.
        for name, t, inp in [
            ("symlink: `code` → real, Read of the read= port code/port.py allowed", "Read",
             {"file_path": "code/port.py"}),
            ("symlink: `code` → real, the port by its real path allowed", "Read",
             {"file_path": "real/port.py"}),
            ("symlink: `code` → real, cat code/port.py allowed", "Bash",
             {"command": "cat code/port.py"}),
            ("symlink: `code` → real, the suite under it allowed", "Read",
             {"file_path": "code/tests/acceptance/test_a.py"}),
            ("symlink: `code` → real, cat of the suite allowed", "Bash",
             {"command": "cat code/tests/acceptance/test_a.py"}),
        ]:
            with self.case(name):
                self.assertAllowed(self.call(t, inp, repo))
        with self.case("symlink: `code` → real, cat code/x.py beside the port denied"):
            self.assertDenied(self.call("Bash", {"command": "cat code/port.py code/x.py"}, repo),
                              "read of code/")
        with self.case("symlink: `code` → real, Read code/x.py denied"):
            self.assertDenied(self.call("Read", {"file_path": "code/x.py"}, repo), "under code/")
        with self.case("symlink: `code` → real, Read real/x.py denied (the same real place)"):
            self.assertDenied(self.call("Read", {"file_path": "real/x.py"}, repo), "under code/")


class RuleE_QuotedOperands(HookTest):
    """Codex review, PR #345 (round 2): operands were split on whitespace
    with no regard for quotes, so a path holding a space — a listed
    directory `my lib`, a checkout under `checkout with spaces` — was judged
    as pieces that are not the file Bash reads, and passed."""

    guard = "guard-blind"

    def repo_with(self, dirs, files, name=None):
        files = dict(files)
        files["CLAUDE.md"] = config_block(forge="github", implementation_dirs=dirs)
        files["README.md"] = "my lib is where the code lives\n"
        repo = self.new_repo(files, commit=True, branch="qa/5")
        if name:
            moved = repo.parent / name
            repo.rename(moved)
            repo = moved
        self.write(repo / ".git/roz-gate/fidelity-dispatch", "issue=5\nread=my lib/port.py\n")
        return repo

    def test_a_listed_directory_with_a_space(self):
        repo = self.repo_with("my lib", {"my lib/x.py": "x\n", "my lib/port.py": "p\n",
                                         "my library/x.py": "other\n"})
        with self.case("quoted: the tool prints `Implementation: my lib`"):
            self.assertEqual(tool(repo).stdout, "Implementation: my lib\n")
        for name, cmd in [
            ('quoted: cat "my lib/x.py" denied', 'cat "my lib/x.py"'),
            ("quoted: cat 'my lib/x.py' denied", "cat 'my lib/x.py'"),
            ("quoted: cat my\\ lib/x.py denied (an escaped space)", "cat my\\ lib/x.py"),
            ('quoted: cat "my lib"/x.py denied (a word of two parts)', 'cat "my lib"/x.py'),
            ('quoted: cat "./my lib/x.py" denied', 'cat "./my lib/x.py"'),
            ('quoted: grep -r foo "my lib/" denied', 'grep -r foo "my lib/"'),
            ('quoted: --file="my lib/x.py" denied', 'python3 t.py --file="my lib/x.py"'),
            ('quoted: an absolute quoted path denied', 'cat "%s/my lib/x.py"' % repo),
            ('quoted: the port and its sibling in one command denied',
             'cat "my lib/port.py" "my lib/x.py"'),
        ]:
            with self.case(name):
                self.assertDenied(self.call("Bash", {"command": cmd}, repo), "read of my lib/")
        with self.case('quoted: Read "my lib/x.py" denied (it always was)'):
            self.assertDenied(self.call("Read", {"file_path": "my lib/x.py"}, repo),
                              "under my lib/")
        for name, cmd in [
            ('quoted: cat "my library/x.py" allowed (a look-alike)', 'cat "my library/x.py"'),
            ('quoted: grep "my lib" README.md allowed (a quoted pattern, no path)',
             'grep "my lib" README.md'),
            ('quoted: cat "my lib/port.py" allowed (the read= port)', 'cat "my lib/port.py"'),
            ("quoted: cat 'my lib/port.py' allowed (the port, single quotes)",
             "cat 'my lib/port.py'"),
            ('quoted: an unterminated quote does not crash the guard', 'echo "my lib'),
        ]:
            with self.case(name):
                self.assertAllowed(self.call("Bash", {"command": cmd}, repo))

    def test_a_checkout_whose_path_has_spaces(self):
        repo = self.repo_with("lib", {"lib/x.py": "x\n", "docs/n.md": "n\n"},
                              name="checkout with spaces")
        for name, cmd in [
            ("spaces: a quoted absolute read of lib/ denied", 'cat "%s/lib/x.py"' % repo),
            ("spaces: the same, single-quoted, denied", "cat '%s/lib/x.py'" % repo),
            ("spaces: the same with escaped spaces denied",
             "cat %s/lib/x.py" % str(repo).replace(" ", "\\ ")),
            ('spaces: "$(git rev-parse --show-toplevel)/lib/x.py" denied',
             'cat "$(git rev-parse --show-toplevel)/lib/x.py"'),
            ("spaces: a relative read is still denied", "cat lib/x.py"),
        ]:
            with self.case(name):
                self.assertDenied(self.call("Bash", {"command": cmd}, repo), "read of lib/")
        for name, cmd in [
            ("spaces: a quoted absolute read of docs/ allowed", 'cat "%s/docs/n.md"' % repo),
            ('spaces: "$(git rev-parse --show-toplevel)/docs/n.md" allowed',
             'cat "$(git rev-parse --show-toplevel)/docs/n.md"'),
        ]:
            with self.case(name):
                self.assertAllowed(self.call("Bash", {"command": cmd}, repo))

    def test_a_command_inside_a_quoted_word_is_still_seen(self):
        # Keeping quoted words whole must not hide what splitting used to
        # catch: the pieces of a quoted word stay candidates too.
        repo = self.repo_with("lib", {"lib/x.py": "x\n"})
        for name, cmd in [
            ('quoted: bash -c "cat lib/x.py" denied', 'bash -c "cat lib/x.py"'),
            ("quoted: sh -c 'grep -r foo lib/' denied", "sh -c 'grep -r foo lib/'"),
        ]:
            with self.case(name):
                self.assertDenied(self.call("Bash", {"command": cmd}, repo), "read of lib/")


# The `src/` table of test_guard_blind.py, replayed under a custom list: the
# same commands with `src/` spelled `impl/`, in the same fixture with the
# directory renamed. One engine means one verdict — a command the default
# predicate denies or allows gets the same answer for a listed directory.
# (Codex review, PR #345, round 3: `gh api -F body=@lib/x.py` passed while
# its `src/` form was denied; found one finding at a time until this.)
# A case is exempt only where the two predicates differ BY CONTRACT, and
# the reason is written beside it.
PARITY_EXEMPT = {}


class RuleE_ParityWithTheSrcTable(HookTest):
    guard = "guard-blind"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", implementation_dirs="impl"),
             "impl/app.txt": "demo\n", "tests/acceptance/test_expiry.py": "# S1\n"},
            commit=True)
        (self.repo / "sub").mkdir()
        self.git(self.repo, "branch", "-q", "feat/5")
        self.git(self.repo, "checkout", "-q", "-b", "qa/5")
        self.git(self.repo, "worktree", "add", "-q",
                 str(self.repo / ".git/roz-gate/wt/spec/5"), "-b", "spec/5")
        self.write(self.repo / ".git/roz-gate/fidelity-dispatch", "issue=5\n")

    def test_the_same_verdicts(self):
        import test_guard_blind as default

        def custom(text):
            return text.replace("src/", "impl/")

        ran = 0
        for name, cmd, says in default.BASH_DENIED:
            if name in PARITY_EXEMPT:
                continue
            ran += 1
            with self.case("parity: " + custom(name)):
                self.assertDenied(self.call("Bash", {"command": custom(cmd)}, self.repo,
                                            agent_type="roz-gate:qa"), custom(says))
        for name, cmd in default.BASH_ALLOWED:
            if name in PARITY_EXEMPT:
                continue
            ran += 1
            with self.case("parity: " + custom(name)):
                self.assertAllowed(self.call("Bash", {"command": custom(cmd)}, self.repo,
                                             agent_type="roz-gate:qa"))
        with self.case("parity: the src/ table was replayed (%d commands), exemptions are "
                       "named cases of it" % ran):
            self.assertGreater(ran, 100)
            names = {c[0] for c in default.BASH_DENIED + default.BASH_ALLOWED}
            self.assertEqual(set(PARITY_EXEMPT) - names, set())


class RuleE_ImplementationDirsWithSrc(ImplementationDirsBase):
    DIRS = "lib, src"

    def test_src_is_denied_when_listed(self):
        with self.case("dirs: `lib, src` — Read src/x.py denied"):
            self.assertDenied(self.tool("Read", file_path="src/x.py"), "under src/")
        with self.case("dirs: `lib, src` — cat src/x.py denied"):
            self.assertDenied(self.run_bash("cat src/x.py"), "read of src/")
        with self.case("dirs: `lib, src` — app/ is not listed, Read app/models.py allowed"):
            self.assertAllowed(self.tool("Read", file_path="app/models.py"))


class RuleE_InvalidImplementationDirs(HookTest):
    guard = "guard-blind"
    INVALID = [("an empty value", ""), ("the repo root", "."), ("an absolute path", "/abs/lib"),
               ("a climb", "../lib"), ("a climb back to the root", "lib/../.."),
               ("an empty element", "lib,,app"), ("the root beside a directory", "lib, ./")]

    def repo_with(self, value, marker=True):
        repo = self.new_repo(
            {"CLAUDE.md": config_block(forge="github", implementation_dirs=value),
             "README.md": "x\n", "lib/x.py": "x = 1\n"}, commit=True, branch="qa/5")
        if marker:
            self.write(repo / ".git/roz-gate/fidelity-dispatch", "issue=5\n")
        return repo

    def test_an_invalid_list_denies_every_blind_call(self):
        for label, value in self.INVALID:
            repo = self.repo_with(value)
            for t, inp in [("Bash", {"command": "ls"}), ("Read", {"file_path": "README.md"}),
                           ("Glob", {"pattern": "*.md"}), ("Grep", {"pattern": "x"})]:
                with self.case("invalid (%s): %s denied with the configuration message"
                               % (label, t)):
                    r = self.call(t, inp, repo)
                    self.assertDenied(r, "implementation_dirs")
                    self.assertIn("is invalid", r.stderr)
                    self.assertIn("- implementation_dirs: ", r.stderr)
            with self.case("invalid (%s): the tool exits 2 with the same reason" % label):
                p = tool(repo)
                self.assertEqual(p.returncode, 2, p.stderr)
                self.assertEqual(p.stdout, "")
                self.assertIn("is invalid", p.stderr)
        repo = self.repo_with("../lib", marker=False)
        with self.case("invalid: no marker — nothing is denied"):
            self.assertAllowed(self.call("Read", {"file_path": "lib/x.py"}, repo))


class RozImplementationDirs(HookTest):
    """The rendered line and the enforced list come from one resolver."""

    guard = "guard-blind"

    def repo_with(self, value=None):
        keys = dict(forge="github")
        if value is not None:
            keys["implementation_dirs"] = value
        repo = self.new_repo(
            {"CLAUDE.md": config_block(**keys), "lib/x.py": "x\n", "app/y.py": "y\n",
             "src/z.py": "z\n"}, commit=True, branch="qa/5")
        self.write(repo / ".git/roz-gate/fidelity-dispatch", "issue=5\n")
        return repo

    def test_the_line_is_the_list_the_guard_enforces(self):
        for label, value, want in [
            ("plain", "lib, app", ["lib", "app"]),
            ("backticks, ./ and trailing slashes", "`./lib/`, `app/`", ["lib", "app"]),
            ("a repeat", "lib, app, lib", ["lib", "app"]),
            ("one directory", "lib", ["lib"]),
            ("nested", "services/api/lib", ["services/api/lib"]),
        ]:
            repo = self.repo_with(value)
            p = tool(repo)
            with self.case("tool (%s): prints `Implementation: %s`" % (label, ", ".join(want))):
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout, "Implementation: %s\n" % ", ".join(want))
            with self.case("tool (%s): the guard's deny names exactly the printed list" % label):
                r = self.call("Read", {"file_path": "%s/probe.py" % want[0]}, repo)
                self.assertDenied(r, "%s and `feat/<n>` are off-limits"
                                  % ", ".join("`%s/`" % d for d in want))
        repo = self.repo_with()
        with self.case("tool: key unset — prints nothing, exit 0"):
            p = tool(repo)
            self.assertEqual((p.returncode, p.stdout), (0, ""), p.stderr)
        with self.case("tool: key unset — the guard still denies src/ with the 1.x message"):
            self.assertDenied(self.call("Read", {"file_path": "src/z.py"}, repo),
                              "`src/` and `feat/<n>` are off-limits")
        with self.case("tool: key unset — lib/ is not the implementation"):
            self.assertAllowed(self.call("Read", {"file_path": "lib/x.py"}, repo))
        repo2 = self.repo_with("lib, app")
        wt = repo2 / ".git/roz-gate/wt/spec/5"
        self.git(repo2, "worktree", "add", "-q", str(wt), "-b", "spec/5")
        with self.case("tool: from a linked worktree — the same line"):
            self.assertEqual(tool(wt).stdout, "Implementation: lib, app\n")
        with self.case("tool: outside a roz-gate project — nothing, exit 0"):
            p = tool(self.new_dir())
            self.assertEqual((p.returncode, p.stdout), (0, ""), p.stderr)
