"""guard-dispatch (Agent, Task): rule L — a seat dispatch carries its contract,
the seat's R&R row and the `Plugin root:` line (#382).

The rows are read from references/workflow.md here as the guard reads them
there: a case that pastes "the row" pastes whatever the table says today.
The D3 wordings are the 2026-11-17/18 sweep's own dispatches (run-1 and
run-3 pointed at the row and failed the case; run-2 pasted it and passed),
with the sandbox's plugin path replaced by this checkout's."""

import json
import re
import subprocess

from hooktest import HOOKS, HookTest, Result, config_block

PLUGIN = HOOKS.parent
ROOT_LINE = ("Plugin root: %s — plugin paths resolve here; never search for plugin files."
             % PLUGIN)
DENIED = "Roz Gate: blocked — a seat dispatch without its contract"
FAILED = "tool failure, not a protocol block"


def row(seat):
    """The seat's row as a dispatch pastes it: `Owns — … Never — …`."""
    text = (PLUGIN / "references" / "workflow.md").read_text()
    m = re.search(r"^\| \*\*%s\*\* \| (.*) \| (.*) \|$" % seat, text, re.M)
    return "Your contract (R&R row): Owns — %s. Never — %s." % m.groups()


# D3/run-1 (FAIL): the row pointed at, the line present.
D3_R1 = ("You are the `product` seat wearing the INTAKE hat, in ASYNC mode, for GitHub issue #9 "
         "in this repo.\n\nPlugin root: {p}\n\nRead first: {p}/references/intake-brief.md "
         "(follow it exactly). Your product R&R row is in {p}/references/workflow.md § Seats "
         "and personas. Read it only for the product row.").format(p=PLUGIN)
# D3/run-3 (FAIL): the same, worded as a see-also.
D3_R3 = ("You are wearing the INTAKE hat, async medium, for issue #9.\n\nPlugin root: {p}\n"
         "Your R&R row: see the seat table in {p}/references/workflow.md (§ Seats and "
         "personas, the `product` row).").format(p=PLUGIN)
# D3/run-2 (PASS): the row paraphrased term by term — "implementation tests" for
# the table's "impl tests".
D3_R2 = ("Your seat: **product**. Your contract (R&R row): Owns — actors, scenarios "
         "(Given/When/Then: happy/edge/failure), consistency, user-facing gaps. Never — "
         "architecture, code, implementation tests.\n\nYour stage instructions: the intake "
         "brief.\n\n" + ROOT_LINE)


class RuleL_SeatDispatchCarriesContract(HookTest):
    guard = "guard-dispatch"

    def setUp(self):
        super().setUp()
        self.repo = self.new_repo({"CLAUDE.md": config_block(forge="github")}, commit=True)

    def dispatch(self, agent, prompt, cwd=None, tool="Agent"):
        inp = {"description": "a dispatch", "prompt": prompt}
        if agent is not None:
            inp["subagent_type"] = agent
        return self.call(tool, inp, cwd or self.repo)

    def test_plugin_seats(self):
        for seat in ("product", "em", "qa", "reviewer"):
            with self.case("roz-gate:%s with its row and the Plugin root line: allowed" % seat):
                self.assertAllowed(self.dispatch("roz-gate:" + seat,
                                                 "Do the stage.\n" + row(seat) + "\n" + ROOT_LINE))
        with self.case("the line missing: denied, the remedy names the line and this plugin's "
                       "root"):
            r = self.dispatch("roz-gate:product", row("product"))
            self.assertDenied(r, DENIED)
            self.assertIn("Plugin root: %s" % PLUGIN, r.stderr)
            self.assertNotIn("not a pointer", r.stderr)
        with self.case("D3/r1 — the row pointed at, not attached: denied, the row printed to "
                       "paste"):
            r = self.dispatch("roz-gate:product", D3_R1)
            self.assertDenied(r, DENIED)
            self.assertIn("the product R&R row itself, not a pointer to it", r.stderr)
            self.assertIn('"actors"', r.stderr)
            self.assertIn("**product** — Owns: actors, scenarios", r.stderr)
            self.assertNotIn("- the line `Plugin root:", r.stderr)
        with self.case("D3/r3 — 'see the seat table': denied"):
            self.assertDenied(self.dispatch("roz-gate:product", D3_R3), "not a pointer")
        with self.case("D3/r2 — the row paraphrased term by term (implementation tests): "
                       "allowed"):
            self.assertAllowed(self.dispatch("roz-gate:product", D3_R2))
        with self.case("the Never column dropped: denied, the missing terms named"):
            r = self.dispatch("roz-gate:product", "Owns — actors, scenarios, consistency, "
                              "user-facing gaps.\n" + ROOT_LINE)
            self.assertDenied(r, '"architecture", "code", "impl tests"')
        with self.case("the qa seat given the em row: denied"):
            self.assertDenied(self.dispatch("roz-gate:qa", row("em") + "\n" + ROOT_LINE),
                              "the qa R&R row")
        with self.case("a continuation ping to a briefed seat (C5's em) is a dispatch: denied"):
            self.assertDenied(self.dispatch("roz-gate:em", "Status check only: reply in one "
                                            "line whether your fold is complete."), DENIED)
        with self.case("the Task tool is guarded too"):
            self.assertDenied(self.dispatch("roz-gate:reviewer", "Review it.", tool="Task"),
                              DENIED)

    def test_plugin_root_line(self):
        rr = row("reviewer")
        with self.case("`Plugin root:` mid-sentence (C5/r3's shape) counts"):
            self.assertAllowed(self.dispatch(
                "roz-gate:reviewer", "%s Re-spawned to fold a ruling. Plugin root: %s (read "
                "its references/workflow.md if you need it)." % (rr, PLUGIN)))
        with self.case("`**Plugin root:** `<dir>`` (markdown) counts"):
            self.assertAllowed(self.dispatch("roz-gate:reviewer",
                                             "%s\n**Plugin root:** `%s`" % (rr, PLUGIN)))
        spaced = self.new_dir() / "my plugins" / "roz gate"
        self.write(spaced / "references" / "workflow.md", "# copy\n")
        for name, line in (("bare", "Plugin root: %s — plugin paths resolve here; never search "
                                    "for plugin files." % spaced),
                           ("in backticks", "Plugin root: `%s`" % spaced),
                           ("in double quotes", 'Plugin root: "%s".' % spaced)):
            with self.case("a plugin root whose path holds spaces, %s, counts (codex, PR #389)"
                           % name):
                self.assertAllowed(self.dispatch("roz-gate:reviewer", "%s\n%s" % (rr, line)))
        for name, value in (("unexpanded `${CLAUDE_PLUGIN_ROOT}`", "${CLAUDE_PLUGIN_ROOT}"),
                            ("a relative dir", "plugin"),
                            ("a dir with no references/workflow.md", str(self.tmp))):
            with self.case("Plugin root naming %s: denied" % name):
                self.assertDenied(self.dispatch("roz-gate:reviewer",
                                                "%s\nPlugin root: %s" % (rr, value)),
                                  "- the line `Plugin root:")

    def test_personas(self):
        mapped = self.new_repo({
            "CLAUDE.md": config_block(forge="github")
            + "\n### Roz Gate personas\n\n- implementer: backend\n- reviewer: critic\n",
            ".claude/agents/backend.md": "---\nname: backend\n---\n"}, commit=True)
        with self.case("a user-mapped persona (implementer: backend) without the contract: "
                       "denied as the implementer seat"):
            r = self.dispatch("backend", "Implement issue #5.", cwd=mapped)
            self.assertDenied(r, "`backend` sits in the implementer seat")
            self.assertIn("missing:", r.stderr)
        with self.case("D25's shape — backend with the implementer row and the line: allowed"):
            self.assertAllowed(self.dispatch("backend", "Implement issue #5.\n%s\n%s"
                                             % (row("implementer"), ROOT_LINE), cwd=mapped))
        with self.case("a second mapped seat (reviewer: critic) is covered too"):
            self.assertDenied(self.dispatch("critic", "Review the CR.", cwd=mapped), DENIED)
        with self.case("roz-gate:reviewer stays a seat after the block maps reviewer away"):
            self.assertDenied(self.dispatch("roz-gate:reviewer", "Review.", cwd=mapped), DENIED)
        with self.case("an agent the block maps to no seat is not judged"):
            self.assertAllowed(self.dispatch("frontend", "Do a thing.", cwd=mapped))
        # A separate git dir (codex, PR #389): the block only in the main
        # checkout's CLAUDE.local.md, reachable from a worktree by core.worktree.
        sgd_main, sgd_git = self.new_dir() / "repo", self.new_dir() / "gitdir"
        subprocess.run(["git", "init", "-q", "-b", "main", "--separate-git-dir", str(sgd_git),
                        str(sgd_main)], check=True, capture_output=True)
        self.write(sgd_main / "CLAUDE.md", config_block(forge="github"))
        self.git(sgd_main, "add", "-A")
        self.git(sgd_main, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "i")
        self.write(sgd_main / "CLAUDE.local.md",
                   "### Roz Gate personas\n\n- implementer: backend\n")
        sgd_wt = self.new_dir() / "wt"
        self.git(sgd_main, "worktree", "add", "-q", "-b", "feat/5", str(sgd_wt))
        self.git(sgd_main, "config", "core.worktree", str(sgd_main))
        with self.case("separate git dir + core.worktree: worktree cwd, personas only in the main "
                       "checkout's CLAUDE.local.md — backend is still the implementer seat"):
            self.assertDenied(self.dispatch("backend", "Implement issue #5.", cwd=sgd_wt),
                              "`backend` sits in the implementer seat")
        with self.case("no personas block: `backend` is no seat — allowed"):
            self.assertAllowed(self.dispatch("backend", "Implement issue #5."))
        default = self.new_repo({"CLAUDE.md": config_block(forge="github"),
                                 ".claude/agents/implementer.md": "---\nname: implementer\n---\n"},
                                commit=True)
        with self.case("no personas block, .claude/agents/implementer.md: `implementer` is the "
                       "implementer seat (roz-persona's default) — denied without the contract"):
            self.assertDenied(self.dispatch("implementer", "Build it.", cwd=default),
                              "`implementer` sits in the implementer seat")

    def test_not_seats(self):
        for agent in ("general-purpose", "Explore", "statusline-setup", None):
            with self.case("non-seat type %s with no contract: allowed" % agent):
                self.assertAllowed(self.dispatch(agent, "You are the commit sub-agent. Follow "
                                                 "references/commit-brief.md."))
        with self.case("the patrol scanner (general-purpose, naming roz-gate:patrol): allowed"):
            self.assertAllowed(self.dispatch("general-purpose", "You are the read-only SCANNER "
                                             "for one roz-gate:patrol pass."))
        with self.case("roz-gate:<not a seat>: allowed"):
            self.assertAllowed(self.dispatch("roz-gate:scanner", "Scan."))
        plain = self.new_repo(commit=True)
        with self.case("no Roz Gate config block: not a roz-gate project — a bare seat "
                       "dispatch is allowed"):
            self.assertAllowed(self.dispatch("roz-gate:product", "Ask.", cwd=plain))
        with self.case("not a git repo: allowed"):
            self.assertAllowed(self.dispatch("roz-gate:product", "Ask.", cwd=self.cwd))
        with self.case("another tool name on stdin: not judged"):
            self.assertAllowed(self.call("Bash", {"command": "echo roz-gate:qa",
                                                  "subagent_type": "roz-gate:qa"}, self.repo))

    def test_registered(self):
        with self.case("hooks.json runs guard-dispatch.sh before every Agent / Task call"):
            pre = json.loads((HOOKS / "hooks.json").read_text())["hooks"]["PreToolUse"]
            self.assertIn(("Agent|Task", '"${CLAUDE_PLUGIN_ROOT}/hooks/guard-dispatch.sh"'),
                          [(e["matcher"], h["command"]) for e in pre for h in e["hooks"]])

    def raw(self, text, cwd):
        proc = subprocess.run([str(HOOKS / "guard-dispatch.sh")], input=text, cwd=str(cwd),
                              env=self.env, capture_output=True, text=True)
        return Result(proc.returncode, proc.stderr, proc.stdout)

    def test_malformed_input(self):
        with self.case("malformed stdin naming a roz-gate seat: denied as a tool failure "
                       "(#281: what the guard cannot read, it blocks)"):
            r = self.raw('{"tool_name": "Agent", "tool_input": {"subagent_type": '
                         '"roz-gate:qa", "prompt": "x"', self.repo)
            self.assertDenied(r, FAILED)
            self.assertIn("roz-gate guard-dispatch:", r.stderr)
        with self.case("a JSON array, not an object: denied as a tool failure"):
            self.assertDenied(self.raw(json.dumps(["subagent_type", "roz-gate:qa"]), self.repo),
                              FAILED)
        with self.case("malformed stdin the prefilter never escalates: allowed"):
            self.assertAllowed(self.raw('{"tool_name": "Agent", "tool_input": {"subagent_'
                                        'type": "general-purpose"', self.repo))
