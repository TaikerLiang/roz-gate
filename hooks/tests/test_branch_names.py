"""hooks/branch_names.py and bin/roz-branch — the one implementation of
references/branch-names.md (#135). The module's functions are tested
directly (they are pure, bar collect_remote_heads); the CLI runs as a
subprocess against a throwaway clone with a bare remote.

Red-proof, by mutation (recorded in the commit message): `1 + count`
reinstated in a caller → the gapped case fails; UNKNOWN collapsed to
NO_MATCH → the unknown case fails.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS))
import branch_names as bn  # noqa: E402

TOOL = HOOKS.parent / "bin" / "roz-branch"
T = "{type}/{user}/{n}/{seq}"          # the convention the docs use as their example
K = "{kind}/{user}/{n}/{seq}"


def snap(*heads):
    return bn.snapshot_from_heads(list(heads))


class Validate(unittest.TestCase):
    def test_default_and_valid(self):
        for t in (None, "", "{kind}/{n}", T, K, "{type}-{n}", "x/{kind}/{n}"):
            with self.subTest("branch_names: %r is valid" % t):
                self.assertIsNone(bn.validate(t))

    def test_invalid_shapes(self):
        for t, needle in (("{kind}", "no {n}"), ("{user}/{n}", "neither {kind} nor {type}"),
                          ("{kind}/{foo}/{n}", "unknown placeholder {foo}"),
                          ("{kind}/{n}/{n}", "appears more than once"),
                          ("{kind}/{n}/{}", "unknown placeholder {}")):
            with self.subTest("branch_names: %r is invalid — %s" % (t, needle)):
                self.assertIn(needle, bn.validate(t) or "")


class Expand(unittest.TestCase):
    def test_default(self):
        for kind, want in (("spec", "spec/7"), ("feat", "feat/7"), ("qa", "qa/7"), ("fast",
            "fast/7")):
            with self.subTest("branch_names: default template renders %s" % want):
                self.assertEqual(bn.expand(None, kind=kind, n=7), want)

    def test_every_placeholder(self):
        with self.subTest("branch_names: {type}/{user}/{n}/{seq} — spec and qa fix their type"):
            self.assertEqual(bn.expand(T, kind="spec", n=5, user="pwl", seq=1), "spec/pwl/5/1")
            self.assertEqual(bn.expand(T, kind="qa", n=5, user="pwl", seq=1), "test/pwl/5/1")
        with self.subTest("branch_names: feat and fast render the issue's type label"):
            self.assertEqual(bn.expand(T, kind="feat", n=5, type="fix", user="pwl", seq=2),
                "fix/pwl/5/2")
            self.assertEqual(bn.expand(T, kind="fast", n=4, type="chore", user="pwl", seq=1),
                "chore/pwl/4/1")
        with self.subTest("branch_names: {kind} and {type} together"):
            self.assertEqual(bn.expand("{kind}/{type}/{n}", kind="feat", n=5, type="fix"),
                "feat/fix/5")

    def test_missing_values_are_typed(self):
        for kw, code, needle in (
                (dict(kind="feat", n=5, user="pwl", seq=1), "MISSING_REQUIRED_VALUE", "{type}"),
                (dict(kind="spec", n=5, seq=1), "MISSING_REQUIRED_VALUE", "{user}"),
                (dict(kind="spec", n=5, user="pwl"), "INVALID_SEQUENCE", "{seq}"),
                (dict(kind="spec", n=5, user="pwl", seq=0), "INVALID_SEQUENCE", "{seq}"),
                (dict(kind="spec", n="x", user="pwl", seq=1), "MISSING_REQUIRED_VALUE", "n must"),
                (dict(kind="branch", n=5, user="pwl", seq=1), "MISSING_REQUIRED_VALUE", "kind")):
            with self.subTest("branch_names: expand(%s) → %s" % (kw, code)):
                with self.assertRaises(bn.BranchNameError) as cm:
                    bn.expand(T, **kw)
                self.assertEqual(cm.exception.code, code)
                self.assertIn(needle, cm.exception.why)
        with self.subTest("branch_names: expand never computes {seq} — the caller passes 1 + max"):
            self.assertEqual(bn.expand(T, kind="spec", n=73, user="paul", seq=4), "spec/paul/73/4")

    def test_invalid_template_raises(self):
        with self.assertRaises(bn.BranchNameError) as cm:
            bn.expand("{user}/{n}", kind="spec", n=1, user="a")
        self.assertEqual(cm.exception.code, "INVALID_TEMPLATE")


class Patterns(unittest.TestCase):
    def test_pattern_for_kind_any_issue(self):
        p = bn.pattern_for_kind(T, "spec")
        with self.subTest("branch_names: guard-acceptance's question — is this a spec branch?"):
            self.assertTrue(p.match("spec/pwl/5/1"))
            self.assertTrue(p.match("spec/someone-else/999/12"))
            self.assertFalse(p.match("fix/pwl/5/1"))
            self.assertFalse(p.match("test/pwl/5/1"))
            self.assertFalse(p.match("spec/pwl/5/1/extra"))
        with self.subTest("branch_names: default template → spec/<n> exactly"):
            p = bn.pattern_for_kind(None, "spec")
            self.assertTrue(p.match("spec/5")) and self.assertFalse(p.match("spec/5/1"))
            self.assertFalse(p.match("spec/abc"))
        with self.subTest("branch_names: a fixed n narrows the pattern"):
            p = bn.pattern_for_kind(K, "feat", n=5)
            self.assertTrue(p.match("feat/x/5/1")) and self.assertFalse(p.match("feat/x/55/1"))
        with self.subTest("branch_names: an invalid template matches nothing, never everything"):
            self.assertFalse(bn.pattern_for_kind("{user}/{n}", "spec").match("a/1"))

    def test_parse_branch_any_kind(self):
        with self.subTest("branch_names: parse every slot, any kind"):
            self.assertEqual(bn.parse_branch("fix/pwl/5/3", T),
                             {"kind": "feat|fast", "type": "fix", "user": "pwl", "n": "5",
                                 "seq": 3})
            self.assertEqual(bn.parse_branch("spec/pwl/5/1", T)["kind"], "spec")
            self.assertEqual(bn.parse_branch("test/pwl/5/1", T)["kind"], "qa")
            self.assertEqual(bn.parse_branch("qa/pwl/5/1", K),
                             {"kind": "qa", "type": "test", "user": "pwl", "n": "5", "seq": 1})
        with self.subTest("branch_names: default template"):
            self.assertEqual(bn.parse_branch("spec/9", None),
                             {"kind": "spec", "type": "spec", "user": None, "n": "9", "seq": None})
            self.assertIsNone(bn.parse_branch("main", None))
            self.assertIsNone(bn.parse_branch("release/20261117", None))
            self.assertIsNone(bn.parse_branch("spec/9/2", None))
        with self.subTest("branch_names: rule K's question — same issue?"):
            a, b, c = (bn.parse_branch(x, T) for x in ("spec/pwl/5/1", "fix/other/5/2",
                "fix/pwl/6/1"))
            self.assertEqual(a["n"], b["n"])
            self.assertNotEqual(a["n"], c["n"])


class Match(unittest.TestCase):
    def test_outcomes(self):
        s = snap("spec/paul/73/1", "spec/paul/73/3", "feat/paul/73/1", "spec/paul/74/1", "main")
        with self.subTest("branch_names: gapped {seq} → MULTIPLE_SEQ, both sorted, max visible"):
            m = bn.match_heads(s, K, kind="spec", n=73)
            self.assertEqual(m["outcome"], "MULTIPLE_SEQ")
            self.assertEqual([x["seq"] for x in m["matches"]], [1, 3])
            self.assertEqual(max(x["seq"] for x in m["matches"]) + 1, 4)
        with self.subTest("branch_names: contiguous {seq}"):
            m = bn.match_heads(snap("spec/p/1/1", "spec/p/1/2", "spec/p/1/3"), K, kind="spec", n=1)
            self.assertEqual((m["outcome"], [x["seq"] for x in m["matches"]]), ("MULTIPLE_SEQ",
                [1, 2, 3]))
        with self.subTest("branch_names: one"):
            self.assertEqual(bn.match_heads(s, K, kind="feat", n=73)["outcome"], "ONE")
        with self.subTest("branch_names: none"):
            self.assertEqual(bn.match_heads(s, K, kind="qa", n=73)["outcome"], "NO_MATCH")
        with self.subTest("branch_names: another user's branch is found (lookup, not expand)"):
            m = bn.match_heads(snap("spec/someone/5/1"), K, kind="spec", n=5)
            self.assertEqual((m["outcome"], m["matches"][0]["user"]), ("ONE", "someone"))
        with self.subTest("branch_names: same {seq} twice → MULTIPLE_SAME_SEQ, never a pick"):
            m = bn.match_heads(snap("spec/a/5/1", "spec/b/5/1"), K, kind="spec", n=5)
            self.assertEqual(m["outcome"], "MULTIPLE_SAME_SEQ")
            self.assertEqual(len(m["matches"]), 2)
        with self.subTest("branch_names: a template without {seq}: two users → MULTIPLE_SAME_SEQ"):
            m = bn.match_heads(snap("spec/a/5", "spec/b/5"), "{kind}/{user}/{n}", kind="spec", n=5)
            self.assertEqual(m["outcome"], "MULTIPLE_SAME_SEQ")
        with self.subTest("branch_names: feat with the type label narrows; without it, any type"):
            s2 = snap("fix/p/5/1", "feat/p/5/1", "spec/p/5/1")
            self.assertEqual(bn.match_heads(s2, T, kind="feat", n=5,
                type="fix")["matches"][0]["branch"], "fix/p/5/1")
            self.assertEqual(len(bn.match_heads(s2, T, kind="feat", n=5)["matches"]), 2)

    def test_fixed_types_excluded_whatever_the_delimiter(self):
        """codex review, PR #254: a feat/fast lookup with no type label must
        never bind a spec or qa branch — under `{type}-{n}` too, not only
        slash-delimited templates."""
        for tpl, heads, want in (
                ("{type}-{n}", ("spec-5", "test-5", "fix-5"), ["fix-5"]),
                ("{type}.{n}.{seq}", ("spec.5.1", "test.5.1", "chore.5.1"), ["chore.5.1"]),
                ("{type}_{user}_{n}", ("spec_p_5", "test_p_5", "feat_p_5"), ["feat_p_5"]),
                ("{type}/{n}", ("spec/5", "test/5", "fix/5"), ["fix/5"]),
                ("{type}-{n}", ("spec-5", "test-5"), [])):
            for kind in ("feat", "fast"):
                with self.subTest("branch_names: %s, %s without a type → %s" % (tpl, kind, want)):
                    m = bn.match_heads(snap(*heads), tpl, kind=kind, n=5)
                    self.assertEqual([x["branch"] for x in m["matches"]], want)
        with self.subTest("branch_names: a type that merely starts with spec/test is not excluded"):
            m = bn.match_heads(snap("specs-5", "testing-5"), "{type}-{n}", kind="feat", n=5)
            self.assertEqual(len(m["matches"]), 2)

    def test_typed_lookup_binds_the_issues_type_only(self):
        """codex review, PR #254: issue #5 is `type: fix`; the remote keeps
        fix/alice/5/1 and feat/bob/5/2. Typed, only the fix branch matches;
        untyped, both do — which is why tip must pass --types."""
        s = snap("fix/alice/5/1", "feat/bob/5/2", "spec/alice/5/1")
        with self.subTest("branch_names: --types 5=fix binds fix/alice/5/1 alone"):
            m = bn.match_heads(s, T, kind="feat", n=5, type="fix")
            self.assertEqual((m["outcome"], [x["branch"] for x in m["matches"]]),
                             ("ONE", ["fix/alice/5/1"]))
        with self.subTest("branch_names: untyped, both implementation branches match"):
            m = bn.match_heads(s, T, kind="feat", n=5)
            self.assertEqual([x["branch"] for x in m["matches"]],
                             ["fix/alice/5/1", "feat/bob/5/2"])

    def test_snapshot_keeps_each_heads_sha(self):
        """codex review, PR #254: the scanner and tip compare `reviewed-sha:`
        against the implementation branch's remote head; the snapshot is
        all they are handed, so it must keep every head's SHA."""
        a, b = "a" * 40, "b" * 40
        s = bn.snapshot_from_heads({"feat/5": a, "spec/5": b})
        with self.subTest("branch_names: snapshot_from_heads keeps a branch → sha map"):
            self.assertEqual(s["shas"], {"feat/5": a, "spec/5": b})
            self.assertEqual(s["heads"], ["feat/5", "spec/5"])
        with self.subTest("branch_names: every match carries its sha"):
            m = bn.match_heads(s, None, kind="feat", n=5)
            self.assertEqual(m["matches"][0]["sha"], a)
        with self.subTest("branch_names: a moved head changes heads_sha256"):
            moved = bn.snapshot_from_heads({"feat/5": "c" * 40, "spec/5": b})
            self.assertNotEqual(s["heads_sha256"], moved["heads_sha256"])
        with self.subTest("branch_names: a bare name list still works (sha None)"):
            m = bn.match_heads(snap("feat/5"), None, kind="feat", n=5)
            self.assertIsNone(m["matches"][0]["sha"])

    def test_unknown_is_never_absence(self):
        for s in ({"status": "unknown", "reason": "offline", "heads": []},
                  {"status": "unknown", "heads": ["spec/5"]}):
            with self.subTest("branch_names: an unobserved snapshot → UNKNOWN, not NO_MATCH"):
                m = bn.match_heads(s, None, kind="spec", n=5)
                self.assertEqual(m["outcome"], "UNKNOWN")
                self.assertEqual(m["matches"], [])

    def test_bulk_equals_singles(self):
        s = snap("spec/p/5/1", "fix/p/5/1", "spec/p/6/1", "spec/p/6/2")
        with self.subTest("branch_names: match_issue over one snapshot = per-kind singles"):
            bulk = {n: bn.match_issue(s, T, n, track="spec", type=t) for n, t in (("5", "fix"),
                ("6", None))}
            self.assertEqual(bulk["5"]["feat"], bn.match_heads(s, T, kind="feat", n="5",
                type="fix"))
            self.assertEqual(bulk["6"]["spec"], bn.match_heads(s, T, kind="spec", n="6"))
            self.assertEqual(set(bulk["5"]), {"spec", "feat", "qa"})
            self.assertEqual(set(bn.match_issue(s, T, "5", track="fast")), {"fast"})


class CollectAndCli(unittest.TestCase):
    """The I/O edge and the CLI, against a throwaway clone with a bare remote."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.bare = base / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.bare)], check=True)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.repo / "README.md").write_text("x\n")
        self.git("-c", "user.name=a", "-c", "user.email=a@a", "add", "-A")
        self.git("-c", "user.name=a", "-c", "user.email=a@a", "commit", "-qm", "seed")
        self.git("remote", "add", "origin", str(self.bare))
        for b in ("spec/paul/73/1", "spec/paul/73/3", "feat/paul/73/1", "spec/paul/74/1"):
            self.git("branch", b)
        self.git("push", "-q", "origin", "--all")
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude/roz-gate.local.json").write_text(
            json.dumps({"branch_template": K, "branch_user": "paul"}))

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              text=True, check=True).stdout

    def tool(self, *args, env=None):
        return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(self.repo),
                              capture_output=True, text=True, env=env)

    def test_collect(self):
        with self.subTest("branch_names: collect_remote_heads observes the remote, stable hash"):
            a = bn.collect_remote_heads("origin", cwd=str(self.repo))
            b = bn.collect_remote_heads("origin", cwd=str(self.repo))
            self.assertEqual(a["status"], "observed")
            self.assertIn("spec/paul/73/3", a["heads"])
            self.assertEqual(a["heads_sha256"], b["heads_sha256"])
            self.assertRegex(a["shas"]["spec/paul/73/3"], r"\A[0-9a-f]{40}\Z")
        with self.subTest("branch_names: an unreadable remote → unknown with a reason, no heads"):
            u = bn.collect_remote_heads("nowhere", cwd=str(self.repo))
            self.assertEqual((u["status"], u["heads"], u["heads_sha256"]), ("unknown", [], None))
            self.assertTrue(u["reason"])

    def test_cli_lookup_and_match(self):
        with self.subTest("roz-branch lookup: one snapshot, every issue, typed outcomes"):
            p = self.tool("lookup", "--issues", "73,74", "--tracks", "73=spec,74=spec", "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["snapshot"]["status"], "observed")
            self.assertNotIn("heads", out["snapshot"])
            self.assertEqual(out["issues"]["73"]["spec"]["outcome"], "MULTIPLE_SEQ")
            self.assertEqual([m["seq"] for m in out["issues"]["73"]["spec"]["matches"]], [1, 3])
            self.assertEqual(out["issues"]["73"]["feat"]["outcome"], "ONE")
            self.assertEqual(out["issues"]["73"]["feat"]["matches"][0]["sha"],
                             self.git("rev-parse", "feat/paul/73/1").strip())
            self.assertEqual(out["issues"]["73"]["qa"]["outcome"], "NO_MATCH")
            self.assertEqual(out["issues"]["74"]["spec"]["outcome"], "ONE")
        with self.subTest("roz-branch snapshot + match: match is pure — no git on PATH"):
            p = self.tool("snapshot", "--json")
            self.assertEqual(p.returncode, 0, p.stderr)
            snap_path = self.repo / "snap.json"
            snap_path.write_text(p.stdout)
            env = {**os.environ, "PATH": os.path.dirname(sys.executable)}   # python only, no git
            m = self.tool("match", "--snapshot", str(snap_path), "--issues", "73", "--json",
                env=env)
            self.assertEqual(m.returncode, 0, m.stderr)
            self.assertEqual(json.loads(m.stdout)["issues"]["73"]["spec"]["outcome"],
                "MULTIPLE_SEQ")
        with self.subTest("roz-branch match equals lookup on the same snapshot"):
            lk = json.loads(self.tool("lookup", "--issues", "73", "--json").stdout)
            mt = json.loads(self.tool("match", "--snapshot", str(self.repo / "snap.json"),
                                      "--issues", "73", "--json").stdout)
            self.assertEqual(lk["issues"], mt["issues"])
        with self.subTest("roz-branch lookup: unreachable remote → UNKNOWN everywhere, exit 2"):
            p = self.tool("lookup", "--issues", "73", "--remote", "nowhere", "--json")
            self.assertEqual(p.returncode, 2)
            out = json.loads(p.stdout)
            self.assertEqual(out["snapshot"]["status"], "unknown")
            self.assertTrue(all(v["outcome"] == "UNKNOWN" for v in out["issues"]["73"].values()))

    def test_cli_expand_validate(self):
        with self.subTest("roz-branch expand: explicit seq, user from the local key"):
            p = self.tool("expand", "--kind", "spec", "--n", "73", "--seq", "4")
            self.assertEqual((p.returncode, p.stdout.strip()), (0, "spec/paul/73/4"))
        with self.subTest("roz-branch expand: no --seq under {seq} → INVALID_SEQUENCE, exit 2"):
            p = self.tool("expand", "--kind", "spec", "--n", "73", "--json")
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)["error"]["code"], "INVALID_SEQUENCE")
        with self.subTest("roz-branch expand: feat without --type → MISSING_REQUIRED_VALUE"):
            (self.repo / ".claude/roz-gate.local.json").write_text(
                json.dumps({"branch_template": T, "branch_user": "paul"}))
            p = self.tool("expand", "--kind", "feat", "--n", "5", "--seq", "1", "--json")
            self.assertEqual(json.loads(p.stdout)["error"]["code"], "MISSING_REQUIRED_VALUE")
            p = self.tool("expand", "--kind", "feat", "--n", "5", "--seq", "1", "--type", "fix")
            self.assertEqual(p.stdout.strip(), "fix/paul/5/1")
        with self.subTest("roz-branch validate: a hand-edited invalid template fails visibly"):
            (self.repo /
                ".claude/roz-gate.local.json").write_text(
                json.dumps({"branch_template": "{user}/{n}"}))
            p = self.tool("validate", "--json")
            self.assertEqual(p.returncode, 2)
            self.assertFalse(json.loads(p.stdout)["valid"])
            p = self.tool("lookup", "--issues", "1", "--json")
            self.assertEqual(json.loads(p.stdout)["error"]["code"], "INVALID_TEMPLATE")
        with self.subTest("roz-branch: no local file → the default template"):
            (self.repo / ".claude/roz-gate.local.json").unlink()
            p = self.tool("expand", "--kind", "qa", "--n", "9")
            self.assertEqual(p.stdout.strip(), "qa/9")

    def test_cli_runs_from_a_worktree(self):
        with self.subTest("roz-branch: a linked worktree reads the clone's local file"):
            wt = Path(self.tmp.name) / "wt"
            self.git("worktree", "add", "-q", str(wt), "spec/paul/73/3")
            p = subprocess.run([sys.executable, str(TOOL), "expand", "--kind", "spec", "--n", "73",
                                "--seq", "4"], cwd=str(wt), capture_output=True, text=True)
            self.assertEqual(p.stdout.strip(), "spec/paul/73/4", p.stderr)


if __name__ == "__main__":
    unittest.main()
