"""bin/roz-persona — seat → agent type, in a throwaway repo (#198).

Runtime like the hooks (stdlib, plain python3), so it lives in the runtime
suite. Every case runs the real executable with HOME pointed at an empty
directory; nothing is imported.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
TOOL = HOOKS.parent / "bin" / "roz-persona"
SEATS = ["product", "em", "implementer", "qa", "reviewer"]
DEFAULTS = {"product": "roz-gate:product", "em": "roz-gate:em", "qa": "roz-gate:qa",
            "reviewer": "roz-gate:reviewer"}


def block(**seats):
    lines = "".join("- %s: %s\n" % kv for kv in seats.items())
    return ("## Development Workflow (Roz Gate)\n\n### Roz Gate config\n\n- forge: github\n\n"
            "### Roz Gate personas\n\nFixed role seats → the subagent actually dispatched.\n\n"
            + lines)


class RozPersonaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.home = Path(self.tmp.name) / "home"
        self.root.mkdir()
        self.home.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.root / "README.md").write_text("x\n")
        self.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, text=True, check=True).stdout

    def commit(self):
        self.git("add", "-A")
        self.git("-c", "user.name=a", "-c", "user.email=a@a", "commit", "-qm", "c")

    def agent(self, name, base=None):
        d = (base or self.root) / ".claude" / "agents"
        d.mkdir(parents=True, exist_ok=True)
        (d / ("%s.md" % name)).write_text("---\nname: %s\n---\n" % name)

    def run_tool(self, *args, cwd=None):
        env = dict(os.environ, HOME=str(self.home))
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(cwd or self.root),
                              capture_output=True, text=True, env=env)

    def seats(self, *args, cwd=None):
        p = self.run_tool("--json", *args, cwd=cwd)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return {s["seat"]: s for s in json.loads(p.stdout)}

    # ---- defaults ---------------------------------------------------------
    def test_four_defaults(self):
        with self.subTest("roz-persona: no block → product, em, qa, reviewer default to "
                          "roz-gate:<seat>, found in the plugin's agents/"):
            self.agent("implementer")
            got = self.seats()
            for seat, agent_type in DEFAULTS.items():
                self.assertEqual(got[seat], {"seat": seat, "agent_type": agent_type,
                                             "source": "default", "checked": "found"})

    def test_implementer_default_needs_its_file(self):
        with self.subTest("roz-persona: no block + .claude/agents/implementer.md → implementer, "
                          "source default (ruling 1)"):
            self.agent("implementer")
            self.assertEqual(self.seats()["implementer"],
                             {"seat": "implementer", "agent_type": "implementer",
                              "source": "default", "checked": "found"})

    def test_implementer_unmapped(self):
        with self.subTest("roz-persona: no block, no implementer.md → exit 2 PERSONA_UNMAPPED, "
                          "naming /roz-gate:init"):
            p = self.run_tool("--json")
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            got = {s["seat"]: s for s in json.loads(p.stdout)}
            self.assertEqual(got["implementer"]["failure"], "PERSONA_UNMAPPED")
            self.assertIn("/roz-gate:init", got["implementer"]["detail"])
            self.assertNotIn("checked", got["implementer"])
            self.assertEqual(got["qa"]["checked"], "found", "the other seats still resolve")
            self.assertIn("PERSONA_UNMAPPED", p.stderr)
        with self.subTest("roz-persona: …a block without an implementer line is the same"):
            (self.root / "CLAUDE.md").write_text(block(product="roz-gate:product"))
            p = self.run_tool("implementer")
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["failure"], "PERSONA_UNMAPPED")

    def test_implementer_file_in_home_is_not_the_default(self):
        with self.subTest("roz-persona: ~/.claude/agents/implementer.md alone does not make the "
                          "default — the project's file does"):
            self.agent("implementer", base=self.home)
            self.assertEqual(self.run_tool("implementer").returncode, 2)

    # ---- the block --------------------------------------------------------
    def test_custom_implementer(self):
        (self.root / "CLAUDE.md").write_text(block(implementer="backend"))
        with self.subTest("roz-persona: implementer: backend with no such agent file → backend, "
                          "unverified (ruling 5)"):
            self.assertEqual(self.seats()["implementer"],
                             {"seat": "implementer", "agent_type": "backend",
                              "source": "block", "checked": "unverified"})
        with self.subTest("roz-persona: …with .claude/agents/backend.md → found"):
            self.agent("backend")
            self.assertEqual(self.seats()["implementer"]["checked"], "found")
            self.assertEqual(self.seats()["product"]["source"], "default",
                             "a seat with no line keeps its default")

    def test_bare_name_in_home(self):
        with self.subTest("roz-persona: a bare name found in ~/.claude/agents/ → found"):
            (self.root / "CLAUDE.md").write_text(block(reviewer="my-reviewer"))
            self.agent("my-reviewer", base=self.home)
            self.assertEqual(self.seats()["reviewer"],
                             {"seat": "reviewer", "agent_type": "my-reviewer",
                              "source": "block", "checked": "found"})

    def test_block_in_local_file(self):
        with self.subTest("roz-persona: the block only in CLAUDE.local.md is read"):
            (self.root / "CLAUDE.md").write_text("# Project\n")
            (self.root / "CLAUDE.local.md").write_text(block(implementer="backend"))
            self.agent("backend")
            self.assertEqual(self.seats()["implementer"]["agent_type"], "backend")

    def test_linked_worktree(self):
        with self.subTest("roz-persona: from a linked worktree, the main checkout's untracked "
                          "CLAUDE.local.md and agent file are read"):
            (self.root / "CLAUDE.local.md").write_text(block(implementer="backend"))
            self.agent("backend")
            wt = Path(self.tmp.name) / "wt"
            self.git("worktree", "add", "-q", str(wt), "-b", "feat/5")
            self.assertFalse((wt / "CLAUDE.local.md").exists())
            self.assertEqual(self.seats(cwd=wt)["implementer"],
                             {"seat": "implementer", "agent_type": "backend",
                              "source": "block", "checked": "found"})

    def test_plugin_type_that_does_not_exist(self):
        with self.subTest("roz-persona: qa: roz-gate:nope → exit 2 AGENT_TYPE_UNAVAILABLE"):
            self.agent("implementer")
            (self.root / "CLAUDE.md").write_text(block(qa="roz-gate:nope",
                                                       implementer="implementer"))
            p = self.run_tool("--json")
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            got = {s["seat"]: s for s in json.loads(p.stdout)}
            self.assertEqual(got["qa"]["failure"], "AGENT_TYPE_UNAVAILABLE")
            self.assertEqual(got["qa"]["agent_type"], "roz-gate:nope")
            self.assertIn("AGENT_TYPE_UNAVAILABLE", p.stderr)

    def test_another_plugins_agent(self):
        with self.subTest("roz-persona: other:agent → unverified, never refused"):
            (self.root / "CLAUDE.md").write_text(block(em="other:agent",
                                                       implementer="implementer"))
            self.assertEqual(self.seats()["em"],
                             {"seat": "em", "agent_type": "other:agent", "source": "block",
                              "checked": "unverified"})

    def test_line_for_a_non_seat(self):
        with self.subTest("roz-persona: a `- patrol: x` line is ignored and named on stderr "
                          "(ruling 7)"):
            self.agent("implementer")
            (self.root / "CLAUDE.md").write_text(block(patrol="x", implementer="implementer"))
            p = self.run_tool("--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual([s["seat"] for s in json.loads(p.stdout)], SEATS)
            self.assertIn("patrol", p.stderr)

    # ---- the interface ----------------------------------------------------
    def test_usage(self):
        with self.subTest("roz-persona: an unknown seat, no argument or an extra one → usage, "
                          "exit 64"):
            for args in (["patrol"], [], ["qa", "em"], ["--yaml"]):
                p = self.run_tool(*args)
                self.assertEqual(p.returncode, 64, "%r: %s" % (args, p.stdout))
                self.assertIn("usage", p.stderr)
                self.assertEqual(p.stdout, "")

    def test_json_shape(self):
        with self.subTest("roz-persona: --json is the five seats in order, four keys each; "
                          "<seat> is one of them"):
            self.agent("implementer")
            p = self.run_tool("--json")
            out = json.loads(p.stdout)
            self.assertEqual([s["seat"] for s in out], SEATS)
            for s in out:
                self.assertEqual(sorted(s), ["agent_type", "checked", "seat", "source"])
            one = self.run_tool("qa")
            self.assertEqual(one.returncode, 0, one.stderr)
            self.assertEqual(json.loads(one.stdout), out[3])


if __name__ == "__main__":
    unittest.main()
