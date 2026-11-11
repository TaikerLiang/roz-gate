"""bin/roz-state — the collector (hooks/state_collect.py) end to end, against
a throwaway repository and fake `gh` / `glab` (fakeforge.py). Every case
runs the real CLI and checks the exit code, that stdout is a snapshot the
contract accepts (or a typed failure), and the facts it names.

Red-proof, by mutation of the collector (recorded in the commit message).
"""

import importlib.machinery
import importlib.util
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
ROOT = HOOKS.parent
sys.path.insert(0, str(HOOKS))
import state_collect  # noqa: E402
import state_contract as sc  # noqa: E402

TOOL = str(ROOT / "bin" / "roz-state")
FAKE = str(Path(__file__).resolve().parent / "fakeforge.py")
CODE = "**[reviewer] · code-review**"
FID = "**[reviewer] · fidelity**"


def sh(args, cwd):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    assert p.returncode == 0, (args, p.stderr)
    return p.stdout.strip()


class Repo:
    """work + bare remote, a config block, and the branches asked for."""

    def __init__(self, forge="github", branches=("spec/27", "feat/27", "qa/27"),
                 template=None, block=True):
        self.dir = tempfile.mkdtemp()
        self.bare = os.path.join(self.dir, "origin.git")
        self.work = os.path.join(self.dir, "work")
        self.bin = os.path.join(self.dir, "bin")
        os.makedirs(self.work)
        os.makedirs(self.bin)
        for name in ("gh", "glab"):
            dst = os.path.join(self.bin, name)
            shutil.copy(FAKE, dst)
            os.chmod(dst, 0o755)
        sh(["git", "init", "-q", "--bare", self.bare], self.dir)
        sh(["git", "init", "-q", "-b", "main"], self.work)
        text = "# demo\n"
        if block:
            text += ("\n### Roz Gate config\n\n- forge: %s\n- acceptance_dir: tests/acc\n"
                     % forge)
        Path(self.work, "CLAUDE.md").write_text(text, encoding="utf-8")
        self.commit("seed")
        sh(["git", "remote", "add", "origin", self.bare], self.work)
        sh(["git", "push", "-q", "origin", "main"], self.work)
        self.sha = {}
        for b in branches:
            sh(["git", "checkout", "-q", "-b", b, "main"], self.work)
            Path(self.work, "f.txt").write_text(b, encoding="utf-8")
            self.commit(b)
            sh(["git", "push", "-q", "origin", b], self.work)
            self.sha[b] = sh(["git", "rev-parse", "HEAD"], self.work)
        sh(["git", "checkout", "-q", "main"], self.work)
        if template:
            os.makedirs(os.path.join(self.work, ".claude"), exist_ok=True)
            Path(self.work, ".claude", "roz-gate.local.json").write_text(
                json.dumps({"branch_template": template}), encoding="utf-8")

    def commit(self, msg):
        sh(["git", "add", "-A"], self.work)
        sh(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", msg],
           self.work)

    def env(self, world):
        wf, log = os.path.join(self.dir, "world.json"), os.path.join(self.dir, "log.jsonl")
        Path(wf).write_text(json.dumps(world), encoding="utf-8")
        open(log, "w").close()
        return dict(os.environ, FAKE_FORGE=wf, FAKE_LOG=log,
                    PATH=self.bin + os.pathsep + os.environ["PATH"])

    def run(self, world, args=("27", "--json")):
        log = os.path.join(self.dir, "log.jsonl")
        env = self.env(world)
        p = subprocess.run([sys.executable, TOOL, *args], cwd=self.work, env=env,
                           capture_output=True, text=True)
        try:
            obj = json.loads(p.stdout) if p.stdout.strip() else None
        except ValueError:
            obj = "UNPARSEABLE: %r" % p.stdout[:200]
        with open(log, encoding="utf-8") as f:
            calls = [json.loads(x) for x in f if x.strip()]
        return p.returncode, obj, p.stderr, calls

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def world(repo, labels=("track: spec", "status: in-dev"), prs=None, blockers=None, **kw):
    if prs is None:
        prs = [pr(repo, 40, "merged", "spec/27", base="main"), pr(repo, 41, "open", "feat/27")]
    return {"issues": {"27": {"labels": list(labels)}}, "prs": prs,
            "blockers": {"27": blockers or []}, **kw}


def pr(repo, number, state, head, base="spec/27", draft=False, threads=(), comments=()):
    return {"number": number, "state": state, "draft": draft, "base": base, "head": head,
            "head_sha": repo.sha.get(head, "0" * 40), "threads": list(threads),
            "comments": [{"id": i, "body": b} for i, b in comments]}


def fact(snap, path):
    for k in path.split("."):
        snap = snap[k]
    return snap


class RozState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gh = Repo("github")
        cls.gl = Repo("gitlab")

    @classmethod
    def tearDownClass(cls):
        cls.gh.close()
        cls.gl.close()

    def snap(self, name, repo, w):
        """Run; assert exit 0 and a contract-valid snapshot; return it."""
        rc, obj, err, calls = repo.run(w)
        with self.subTest("roz-state: %s — exit 0 and a valid snapshot" % name):
            self.assertEqual(rc, 0, err)
            self.assertEqual(sc.validate(obj), [])
        return obj if isinstance(obj, dict) else {}

    def expect(self, name, snap, path, status, value=None, reason=None):
        with self.subTest("roz-state: %s — %s is %s" % (name, path, status)):
            f = fact(snap, path)
            self.assertEqual(f["status"], status, f)
            if status == "observed":
                self.assertEqual(f["value"], value)
            if reason:
                self.assertEqual(f.get("reason"), reason)

    # ---- CR states ------------------------------------------------------
    def test_cr_states(self):
        r = self.gh
        s = self.snap("open implementation CR", r, world(r))
        self.expect("open CR", s, "implementation.cr", "observed",
                    {"number": 41, "state": "open", "draft": False, "base": "spec/27",
                     "head_sha": r.sha["feat/27"]})
        self.expect("merged spec CR", s, "spec.cr", "observed",
                    {"number": 40, "state": "merged", "draft": False, "base": "main",
                     "head_sha": r.sha["spec/27"]})
        self.expect("no QA CR on an existing qa branch", s, "qa.cr", "absent")
        self.expect("…its threads follow it", s, "qa.open_fidelity_threads", "absent")
        self.expect("…its marker follows it", s, "qa.fidelity_marker", "absent")
        with self.subTest("roz-state: every envelope names its source op"):
            self.assertEqual(fact(s, "implementation.cr")["source"], "CR-FIND")
            self.assertEqual(fact(s, "branches.spec")["source"], "roz-branch match")
            self.assertEqual(fact(s, "dependencies.blocked_by")["source"], "ISSUE-BLOCKERS")

        s = self.snap("draft QA CR", r, world(r, prs=[pr(r, 42, "open", "qa/27", draft=True)]))
        self.expect("draft", s, "qa.cr", "observed",
                    {"number": 42, "state": "open", "draft": True, "base": "spec/27",
                     "head_sha": r.sha["qa/27"]})
        self.expect("missing spec CR", s, "spec.cr", "absent")

        s = self.snap("closed-unmerged CR", r, world(r, prs=[pr(r, 41, "closed", "feat/27")]))
        self.expect("closed", s, "implementation.cr", "observed",
                    {"number": 41, "state": "closed", "draft": False, "base": "spec/27",
                     "head_sha": r.sha["feat/27"]})

    def test_cr_selection_is_ours(self):
        """#133 amendment 2 — never the CLI's order: each set in two orders."""
        r = self.gh
        sets = {
            "two open → ambiguous": ([pr(r, 41, "open", "feat/27"), pr(r, 43, "open", "feat/27")],
                                     None),
            "a merged and a newer open → the open one":
                ([pr(r, 41, "merged", "feat/27"), pr(r, 43, "open", "feat/27")], 43),
            "an open and a newer merged → the open one":
                ([pr(r, 41, "open", "feat/27"), pr(r, 43, "merged", "feat/27")], 41),
            "three merged → the highest number":
                ([pr(r, 41, "merged", "feat/27"), pr(r, 47, "merged", "feat/27"),
                  pr(r, 43, "merged", "feat/27")], 47),
            "merged beats a newer closed":
                ([pr(r, 41, "merged", "feat/27"), pr(r, 43, "closed", "feat/27")], 41),
            "only closed → the highest number":
                ([pr(r, 41, "closed", "feat/27"), pr(r, 45, "closed", "feat/27"),
                  pr(r, 43, "closed", "feat/27")], 45),
        }
        for name, (prs, want) in sets.items():
            for order in (prs, list(reversed(prs))):
                s = self.snap(name, r, world(r, prs=order))
                if want is None:
                    self.expect(name, s, "implementation.cr", "unknown", reason="ambiguous")
                    self.expect(name + " (dependents)", s, "implementation.open_review_threads",
                                "unknown", reason="depends_on_unknown")
                else:
                    with self.subTest("roz-state: %s (input order %s)"
                                      % (name, [p["number"] for p in order])):
                        self.assertEqual(fact(s, "implementation.cr")["value"]["number"], want)

    # ---- issue state ----------------------------------------------------
    def test_issue_state(self):
        r = self.gh
        s = self.snap("processing", r, world(r, labels=["track: spec", "status: in-dev",
                                                        "status: processing"]))
        with self.subTest("roz-state: processing is a boolean, status is the stage label"):
            self.assertEqual((s["processing"], s["blocked"], s["status"], s["track"]),
                             (True, False, "in-dev", "spec"))
        s = self.snap("blocked", r, world(r, labels=["track: spec", "status: blocked"]))
        with self.subTest("roz-state: blocked with no stage label → status null"):
            self.assertEqual((s["processing"], s["blocked"], s["status"]), (False, True, None))
        s = self.snap("no status", r, world(r, labels=["track: spec", "type: fix"]))
        with self.subTest("roz-state: no status label → status null"):
            self.assertEqual(s["status"], None)
        s = self.snap("no track", r, world(r, labels=["discuss"]))
        with self.subTest("roz-state: no track label → track null"):
            self.assertEqual(s["track"], None)
        self.expect("no track: 0.1 covers track: spec — branches unknown",
                    s, "branches.spec", "unknown", reason="unsupported")
        self.expect("no track: CRs unknown", s, "spec.cr", "unknown",
                    reason="depends_on_unknown")
        self.expect("no track: blockers still observed", s, "dependencies.blocked_by",
                    "observed", [])
        s = self.snap("fast track", r, world(r, labels=["track: fast", "status: ready-for-dev"]))
        self.expect("track: fast is not 0.1's", s, "branches.implementation", "unknown",
                    reason="unsupported")
        with self.subTest("roz-state: config carries the three resolved values"):
            self.assertEqual(s["config"], {"branch_template": "{kind}/{n}",
                                           "default_branch": "main",
                                           "acceptance_dir": "tests/acc"})

    # ---- branches -------------------------------------------------------
    def test_branches(self):
        r = Repo("github", branches=("spec/27/1", "spec/27/2", "feat/27/2"),
                 template="{kind}/{n}/{seq}")
        try:
            s = self.snap("{seq} re-spec", r, world(r, prs=[
                pr(r, 30, "closed", "spec/27/1", base="main"),
                pr(r, 40, "open", "spec/27/2", base="main")]))
            self.expect("the highest {seq} binds", s, "branches.spec", "observed",
                        {"name": "spec/27/2", "sha": r.sha["spec/27/2"]})
            with self.subTest("roz-state: the CR is the bound attempt's, not the old one's"):
                self.assertEqual(fact(s, "spec.cr")["value"]["number"], 40)
            self.expect("no qa branch", s, "branches.qa", "absent")
            self.expect("no qa branch → its CR absent", s, "qa.cr", "absent")
            with self.subTest("roz-state: an absent branch's CR cites the branch read"):
                self.assertEqual(fact(s, "qa.cr")["source"], "roz-branch match")
            with self.subTest("roz-state: config carries the template in force"):
                self.assertEqual(s["config"]["branch_template"], "{kind}/{n}/{seq}")
        finally:
            r.close()
        r = Repo("github", branches=("spec/ann/27/1", "spec/bob/27/1"),
                 template="{type}/{user}/{n}/{seq}")
        try:
            s = self.snap("MULTIPLE_SAME_SEQ", r, world(r, prs=[]))
            self.expect("two attempts with one {seq}", s, "branches.spec", "unknown",
                        reason="ambiguous")
            self.expect("…its CR", s, "spec.cr", "unknown", reason="depends_on_unknown")
        finally:
            r.close()
        r = Repo("github")
        try:
            sh(["git", "remote", "set-url", "origin", os.path.join(r.dir, "gone.git")], r.work)
            s = self.snap("unreachable remote", r, world(r))
            for p in ("branches.spec", "branches.implementation", "branches.qa"):
                self.expect("unreachable remote", s, p, "unknown", reason="remote_unreachable")
            for p in ("spec.cr", "implementation.cr", "implementation.open_review_threads",
                      "implementation.review_marker", "qa.cr", "qa.fidelity_marker"):
                self.expect("unreachable remote", s, p, "unknown", reason="depends_on_unknown")
            self.expect("unreachable remote: blockers do not depend on git",
                        s, "dependencies.blocked_by", "observed", [])
        finally:
            r.close()

    # ---- #272: a head the forge deleted --------------------------------
    def test_deleted_heads(self):
        for r, cli in ((self.gh, "gh"), (self.gl, "glab")):
            gone = Repo("github" if cli == "gh" else "gitlab", branches=("feat/27",))
            try:
                def mpr(n, state, head, when=None, sha="c" * 40, base="main"):
                    p = pr(gone, n, state, head, base=base)
                    p["head_sha"], p["merged_at"] = sha, when
                    return p
                w = world(gone, prs=[mpr(40, "merged", "spec/27", "2026-08-01T00:00:00Z"),
                                     pr(gone, 41, "open", "feat/27")])
                s = self.snap("%s: the spec head deleted after its CR merged" % cli, gone, w)
                self.expect("%s: a deleted head is no branch" % cli, s, "branches.spec", "absent")
                self.expect("%s: …and its merged CR is observed, by its head name" % cli, s,
                            "spec.cr", "observed",
                            {"number": 40, "state": "merged", "draft": False, "base": "main",
                             "head_sha": "c" * 40})
                self.expect("%s: a live branch is unaffected" % cli, s, "branches.implementation",
                            "observed", {"name": "feat/27", "sha": gone.sha["feat/27"]})
                s = self.snap("%s: a closed-unmerged CR with a deleted head" % cli, gone,
                              world(gone, prs=[mpr(40, "closed", "spec/27")]))
                self.expect("%s: closed-unmerged + deleted stays absent (re-entry cleanup)" % cli,
                            s, "branches.spec", "absent")
                self.expect("%s: …its CR too" % cli, s, "spec.cr", "absent")

                s = self.snap("%s: the merged history unreadable" % cli, gone,
                              world(gone, fail=["merged"], prs=[pr(gone, 41, "open", "feat/27")]))
                self.expect("%s: history failed, live branch → still observed" % cli, s,
                            "branches.implementation", "observed",
                            {"name": "feat/27", "sha": gone.sha["feat/27"]})
                self.expect("%s: …and its CR" % cli, s, "implementation.cr", "observed",
                            {"number": 41, "state": "open", "draft": False, "base": "spec/27",
                             "head_sha": gone.sha["feat/27"]})
                self.expect("%s: history failed, no live branch → unknown, never absent" % cli,
                            s, "branches.spec", "unknown", reason="forge_query_failed")
                self.expect("%s: …its CR follows" % cli, s, "spec.cr", "unknown",
                            reason="depends_on_unknown")

                many = [mpr(1000 + i, "merged", "other/%d" % i, "2026-01-01T00:00:00Z")
                        for i in range(230)] + [mpr(40, "merged", "spec/27",
                                                    "2025-01-01T00:00:00Z")]
                s = self.snap("%s: the history across several pages" % cli, gone,
                              world(gone, prs=many))
                self.expect("%s: a deleted head on the history's last page is found" % cli, s,
                            "spec.cr", "observed",
                            {"number": 40, "state": "merged", "draft": False, "base": "main",
                             "head_sha": "c" * 40})
                s = self.snap("%s: more merged CRs than the ceiling" % cli, gone,
                              world(gone, merged_filler=5001, prs=[]))
                self.expect("%s: a truncated history is unknown, never absence" % cli, s,
                            "branches.spec", "unknown", reason="unsupported")
                self.expect("%s: …a live branch still stands" % cli, s,
                            "branches.implementation", "observed",
                            {"name": "feat/27", "sha": gone.sha["feat/27"]})

                a = mpr(40, "merged", "spec/27", "2026-08-01T00:00:00Z", sha="a" * 40)
                b = mpr(39, "merged", "spec/27", "2026-09-01T00:00:00Z", sha="b" * 40)
                for order in ([a, b], [b, a]):
                    code = subprocess.run(
                        [sys.executable, str(ROOT / "bin" / "roz-branch"), "lookup", "--issues",
                         "27", "--tracks", "27=spec", "--json"], cwd=gone.work,
                        env=gone.env(world(gone, prs=order)), capture_output=True, text=True)
                    with self.subTest("roz-state: %s — two merged CRs share a deleted head: the "
                                      "later merged_at wins over the higher number, in any "
                                      "input order" % cli):
                        m = json.loads(code.stdout)["issues"]["27"]["spec"]["matches"]
                        self.assertEqual([(x["branch"], x["cr"], x["sha"], x["deleted"])
                                          for x in m], [("spec/27", 39, "b" * 40, True)])
            finally:
                gone.close()

    def test_snapshot_without_a_block_asks_no_forge(self):
        nb = Repo("github", branches=("spec/27",), block=False)
        try:
            env = nb.env(world(nb))
            p = subprocess.run([sys.executable, str(ROOT / "bin" / "roz-branch"), "snapshot",
                                "--json"], cwd=nb.work, env=env, capture_output=True, text=True)
            snap = json.loads(p.stdout)
            with open(os.path.join(nb.dir, "log.jsonl"), encoding="utf-8") as f:
                calls = [x for x in f if x.strip()]
            with self.subTest("roz-branch: no config block → the snapshot is the remote's "
                              "heads, merged_heads not_asked, and no forge call is made"):
                self.assertEqual((p.returncode, snap["status"], snap["heads"], calls),
                                 (0, "observed", ["main", "spec/27"], []))
                self.assertEqual(snap["merged_heads"], {"status": "not_asked", "heads": {}})
        finally:
            nb.close()

    # ---- evidence -------------------------------------------------------
    def test_evidence(self):
        r = self.gh
        s = self.snap("zero threads, no marker (#95)", r, world(r))
        self.expect("zero threads", s, "implementation.open_review_threads", "observed", 0)
        self.expect("no review ran", s, "implementation.review_marker", "absent")

        sha = r.sha["feat/27"]
        body = "%s\nreviewed-sha: %s\n0 blocking" % (CODE, sha)
        s = self.snap("zero threads and a record (#95)", r, world(r, prs=[
            pr(r, 41, "open", "feat/27", threads=[True, True], comments=[(9001, body)])]))
        self.expect("resolved threads are not counted", s, "implementation.open_review_threads",
                    "observed", 0)
        self.expect("the record, raw", s, "implementation.review_marker", "observed",
                    {"reviewed_sha": sha, "comment_id": 9001})
        with self.subTest("roz-state: no verdict is derived from the record"):
            self.assertEqual(sorted(s["implementation"]),
                             ["cr", "open_review_threads", "review_marker"])

        s = self.snap("a fidelity record carries no sha", r, world(r, prs=[
            pr(r, 42, "open", "qa/27", threads=[False, True, False],
               comments=[(7, "LGTM"), (9100, "%s 29/32 faithful" % FID)])]))
        self.expect("fidelity record", s, "qa.fidelity_marker", "observed",
                    {"reviewed_sha": None, "comment_id": 9100})
        self.expect("two unresolved of three", s, "qa.open_fidelity_threads", "observed", 2)

        old = (9001, "%s\nreviewed-sha: %s" % (CODE, "a" * 40))
        new = (9050, "%s\nreviewed-sha: %s" % (CODE, sha))
        not_one = (9090, "see the %s above" % CODE)
        for order in ([old, new, not_one], [not_one, new, old]):
            s = self.snap("two records", r, world(r, prs=[
                pr(r, 41, "open", "feat/27", comments=order)]))
            self.expect("the highest comment id wins, in any input order; a comment that "
                        "only mentions the marker is not one",
                        s, "implementation.review_marker", "observed",
                        {"reviewed_sha": sha, "comment_id": 9050})

        many = [False] * 5
        s = self.snap("threads across pages", r, world(r, page_size=2, prs=[
            pr(r, 41, "open", "feat/27", threads=many,
               comments=[(i, "c%d" % i) for i in range(1, 6)] + [(9001, body)])]))
        self.expect("every page is counted", s, "implementation.open_review_threads",
                    "observed", 5)
        self.expect("a record on the last comments page is found", s,
                    "implementation.review_marker", "observed",
                    {"reviewed_sha": sha, "comment_id": 9001})

        s = self.snap("a failing second thread page", r, world(r, page_size=2, fail=["threads2:41"],
                                                               prs=[pr(r, 41, "open", "feat/27",
                                                                       threads=many)]))
        self.expect("never a partial count", s, "implementation.open_review_threads", "unknown",
                    reason="forge_query_failed")
        self.expect("…the comments read is its own", s, "implementation.review_marker", "absent")

        s = self.snap("a failing thread read", r, world(r, fail=["threads:41", "comments:41"]))
        self.expect("unknown, never 0", s, "implementation.open_review_threads", "unknown",
                    reason="forge_query_failed")
        self.expect("unknown, never absent", s, "implementation.review_marker", "unknown",
                    reason="forge_query_failed")

        s = self.snap("a failing CR read", r, world(r, fail=["prs"]))
        self.expect("the CR", s, "implementation.cr", "unknown", reason="forge_query_failed")
        self.expect("its dependents", s, "implementation.review_marker", "unknown",
                    reason="depends_on_unknown")

    # ---- blockers -------------------------------------------------------
    def test_blockers(self):
        r = self.gh
        s = self.snap("no blockers", r, world(r))
        self.expect("asked and empty", s, "dependencies.blocked_by", "observed", [])
        s = self.snap("one open blocker", r, world(r, blockers=[{"number": 31, "state": "open"}]))
        self.expect("one", s, "dependencies.blocked_by", "observed",
                    [{"issue": 31, "state": "open", "url": "https://forge/x/y/issues/31"}])
        bl = [{"number": 35, "state": "closed"}, {"number": 31, "state": "open"},
              {"number": 33, "state": "open"}]
        for order in (bl, list(reversed(bl))):
            s = self.snap("several blockers", r, world(r, page_size=2, blockers=order))
            self.expect("every page, sorted by issue number — no ordering is implied",
                        s, "dependencies.blocked_by", "observed",
                        [{"issue": 31, "state": "open", "url": "https://forge/x/y/issues/31"},
                         {"issue": 33, "state": "open", "url": "https://forge/x/y/issues/33"},
                         {"issue": 35, "state": "closed", "url": "https://forge/x/y/issues/35"}])
        s = self.snap("a blocker record the adapter cannot normalise", r,
                      world(r, blockers=[{"number": 31, "state": "weird"}]))
        self.expect("unknown, never a half-read list", s, "dependencies.blocked_by", "unknown",
                    reason="forge_query_failed")
        s = self.snap("a failed blocker read", r, world(r, fail=["blockers"]))
        self.expect("unknown, never [] (F15)", s, "dependencies.blocked_by", "unknown",
                    reason="forge_query_failed")

    # ---- collection failure --------------------------------------------
    def failure(self, name, repo, w, reason, source, args=("27", "--json")):
        rc, obj, err, calls = repo.run(w, args)
        with self.subTest("roz-state: %s — exit 2 and a typed failure, no snapshot" % name):
            self.assertEqual(rc, 2, err)
            self.assertEqual(sc.validate_failure(obj), [])
            self.assertEqual((obj["collection_failure"]["reason"],
                              obj["collection_failure"]["source"]), (reason, source))

    def test_collection_failure(self):
        r = self.gh
        self.failure("ISSUE-VIEW fails", r, world(r, fail=["issue"]),
                     "forge_query_failed", "ISSUE-VIEW")
        self.failure("the issue does not exist", r, world(r), "forge_query_failed",
                     "ISSUE-VIEW", args=("99", "--json"))
        self.failure("two stage labels: the base state cannot be established", r,
                     world(r, labels=["track: spec", "status: in-dev", "status: in-qa"]),
                     "ambiguous", "ISSUE-VIEW")
        self.failure("two track labels", r, world(r, labels=["track: spec", "track: fast"]),
                     "ambiguous", "ISSUE-VIEW")
        nb = Repo("github", branches=(), block=False)
        try:
            self.failure("no config block", nb, world(nb), "unsupported", "config block")
        finally:
            nb.close()
        bt = Repo("github", branches=(), template="{n}")
        try:
            self.failure("an invalid branch_template", bt, world(bt), "unsupported", "roz-config")
        finally:
            bt.close()
        d = tempfile.mkdtemp()
        try:
            p = subprocess.run([sys.executable, TOOL, "27", "--json"], cwd=d,
                               capture_output=True, text=True)
            with self.subTest("roz-state: outside a repository — exit 2 and a typed failure"):
                self.assertEqual(p.returncode, 2)
                self.assertEqual(sc.validate_failure(json.loads(p.stdout)), [])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    # ---- the CLI's exits ------------------------------------------------
    def test_exits(self):
        r = self.gh
        for args in ((), ("27",), ("abc", "--json"), ("27", "--json", "extra")):
            rc, obj, err, calls = r.run(world(r), args)
            with self.subTest("roz-state: usage error %r — exit 64, nothing on stdout, "
                              "no forge call" % (args,)):
                self.assertEqual((rc, obj, calls), (64, None, []))
        loader = importlib.machinery.SourceFileLoader("roz_state_cli", TOOL)
        spec = importlib.util.spec_from_loader("roz_state_cli", loader)
        cli = importlib.util.module_from_spec(spec)
        loader.exec_module(cli)
        real = cli.collect
        try:
            cli.collect = lambda issue: ({"schema": sc.SCHEMA, "review_clean": True}, 0)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["27", "--json"])
            with self.subTest("roz-state: a snapshot its own validator rejects — exit 3, "
                              "nothing on stdout, the errors on stderr (#133 amendment 3)"):
                self.assertEqual((rc, out.getvalue()), (3, ""))
                self.assertIn("internal contract violation", err.getvalue())
                self.assertIn("review_clean: policy field", err.getvalue())
            cli.collect = lambda issue: ({"schema": sc.SCHEMA, "collection_failure": {}}, 2)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["27", "--json"])
            with self.subTest("roz-state: a malformed failure object is internal too — exit 3"):
                self.assertEqual((rc, out.getvalue()), (3, ""))
        finally:
            cli.collect = real

    def test_gitlab_labels(self):
        """Codex, PR #273: GitLab wears scoped labels and a plain `processing`."""
        r = self.gl
        s = self.snap("GitLab labels", r, world(r, labels=[
            "track: spec", "status: in-dev", "status: processing", "type: fix"]))
        with self.subTest("roz-state: glab — track::spec / status::in-dev / processing are "
                          "read as the loop's labels"):
            self.assertEqual((s["track"], s["status"], s["processing"], s["blocked"]),
                             ("spec", "in-dev", True, False))
        self.expect("glab — the branches of a track::spec issue are bound", s, "branches.spec",
                    "observed", {"name": "spec/27", "sha": r.sha["spec/27"]})
        s = self.snap("GitLab blocked", r, world(r, labels=["track: spec", "status: blocked"]))
        with self.subTest("roz-state: glab — status::blocked is the blocked boolean"):
            self.assertEqual((s["status"], s["blocked"]), (None, True))
        with self.subTest("roz-state: glab — the adapter's label map, name by name"):
            lab = state_collect.GitLab._label
            self.assertEqual([lab(x) for x in ("track::fast", "status::ready-for-dev",
                                               "processing", "type::chore", "discuss",
                                               "area::billing", "status: in-dev")],
                             ["track: fast", "status: ready-for-dev", "status: processing",
                              "type: chore", "discuss", "area::billing", "status: in-dev"])

    # ---- parity ---------------------------------------------------------
    def test_parity(self):
        """The two adapters normalise the same canned logical state to the same
        snapshot. Canned glab output only: live GitLab is not verified."""
        rnd = random.Random(133)
        for name, kw in (
                ("mid-loop", {}),
                ("evidence", {"page_size": 2, "prs_for": lambda r: [
                    pr(r, 40, "merged", "spec/27", base="main"),
                    pr(r, 41, "open", "feat/27", threads=[False, True, False],
                       comments=[(9001, "%s\nreviewed-sha: %s" % (CODE, r.sha["feat/27"]))]),
                    pr(r, 42, "open", "qa/27", draft=True,
                       comments=[(9100, "%s 3/3" % FID)])]}),
                ("blockers", {"blockers": [{"number": 33, "state": "closed"},
                                           {"number": 31, "state": "open"}]}),
                ("failed reads", {"fail": ["threads:41", "blockers"]}),
                ("labels", {"labels": ["track: spec", "status: blocked", "status: processing"]})):
            snaps = []
            for r in (self.gh, self.gl):
                k = dict(kw)
                if "prs_for" in k:
                    k["prs"] = k.pop("prs_for")(r)
                w = world(r, **k)
                rnd.shuffle(w["prs"])
                s = self.snap("parity/%s through %s" % (name, "gh" if r is self.gh else "glab"),
                              r, w)
                s = json.loads(json.dumps(s).replace(r.sha.get("spec/27", "-"), "SPEC")
                               .replace(r.sha.get("feat/27", "-"), "FEAT")
                               .replace(r.sha.get("qa/27", "-"), "QA"))
                s.pop("observed_at", None)
                snaps.append(s)
            with self.subTest("roz-state: parity — %s: gh and glab adapters give the same "
                              "snapshot (canned output)" % name):
                self.assertEqual(snaps[0], snaps[1])

    # ---- read-only ------------------------------------------------------
    def test_read_only(self):
        for r, cli in ((self.gh, "gh"), (self.gl, "glab")):
            rc, obj, err, calls = r.run(world(r, prs=[
                pr(r, 41, "open", "feat/27", threads=[False]),
                pr(r, 42, "open", "qa/27", threads=[False])]))
            with self.subTest("roz-state: every %s call it made is on the read allow-list" % cli):
                self.assertTrue(calls)
                for argv in calls:
                    self.assertEqual(argv[0], cli)
                    self.assertTrue(state_collect.allowed(argv), argv)
        refused = (
            ["gh", "issue", "edit", "27", "--add-label", "x"],
            ["gh", "issue", "comment", "27", "--body", "x"],
            ["gh", "pr", "merge", "41"],
            ["gh", "pr", "ready", "41"],
            ["gh", "api", "-X", "POST", "repos/a/b/issues/27/comments", "-f", "body=x"],
            ["gh", "api", "repos/a/b/issues/27/comments", "-f", "body=x"],
            ["gh", "api", "--method", "DELETE", "repos/a/b/issues/comments/1"],
            ["gh", "api", "graphql", "-f", "query=mutation{resolveReviewThread(input:{}){x}}"],
            ["gh", "api", "repos/a/b/issues/27", "--input", "x.json"],
            ["glab", "api", "-X", "PUT", "projects/:id/issues/27"],
            ["glab", "api", "projects/:id/issues/27/notes", "-f", "body=x"],
            ["glab", "mr", "merge", "41"],
            ["gh", "api", "graphql", "-f"],
            ["gh", "api", "repos/a/b/issues/1", "repos/a/b/issues/2"],
            ["gh", "api", "--paginate"],
            ["gh", "api", "graphql", "-f", "query=query{a} mutation{resolveReviewThread{x}}"],
            ["gh", "api", "graphql"],
            ["git", "push", "origin", "main"],
            ["rm", "-rf", "."],
        )
        for argv in refused:
            with self.subTest("roz-state: the gate refuses %s" % " ".join(argv[:4])):
                self.assertFalse(state_collect.allowed(argv))
                with self.assertRaises(state_collect.Refused):
                    state_collect.run(argv)
        with self.subTest("roz-state: the collector's source never names a write op"):
            src = (HOOKS / "state_collect.py").read_text(encoding="utf-8")
            for word in ("LABEL-ADD", "CR-MERGE", "--add-label", "pr merge", "git push",
                         "worktree add", "expand("):
                self.assertNotIn(word, src)
        r = self.gh
        before = sh(["git", "status", "--porcelain"], r.work), sh(
            ["git", "for-each-ref"], r.bare)
        r.run(world(r))
        with self.subTest("roz-state: the repository and its remote are untouched by a run"):
            self.assertEqual(before, (sh(["git", "status", "--porcelain"], r.work),
                                      sh(["git", "for-each-ref"], r.bare)))


class Adapters(unittest.TestCase):
    """What a forge answer the adapter cannot read becomes: a failed read —
    never a guessed value. `run` is replaced; no process is started."""

    def answers(self, name, call, canned):
        real = state_collect.run
        state_collect.run = lambda argv: canned
        try:
            with self.subTest("roz-state: %s → a failed read" % name):
                with self.assertRaises(state_collect.ReadFailed) as cm:
                    call()
                self.assertEqual(cm.exception.reason, "forge_query_failed")
        finally:
            state_collect.run = real

    def test_unreadable_answers(self):
        gh, gl = state_collect.GitHub, state_collect.GitLab
        repo = '{"owner": {"login": "acme"}, "name": "demo"}'

        def with_repo(fn):
            def call():
                api = gh()
                api._repo = ("acme", "demo")
                return fn(api)
            return call
        cr = {"number": 41, "state": "OPEN", "isDraft": False, "baseRefName": "spec/27",
              "headRefOid": "abc"}
        self.answers("unparseable output", lambda: gh().crs("feat/27"), "<html>502</html>")
        self.answers("an object where a list is expected", lambda: gh().crs("feat/27"), repo)
        self.answers("a list of non-objects", lambda: gh().crs("feat/27"), "[1, 2]")
        self.answers("a list where one object is expected", lambda: gh().labels(27), "[]")
        self.answers("two objects where one is expected", lambda: gh().labels(27), repo + repo)
        for field, bad in (("headRefOid", ""), ("headRefOid", None), ("state", "LOCKED"),
                           ("number", "41"), ("number", True), ("isDraft", None),
                           ("baseRefName", "")):
            self.answers("a CR record with %s=%r" % (field, bad), lambda: gh().crs("feat/27"),
                         json.dumps([{**cr, field: bad}]))
        self.answers("gh repo view naming no repository", lambda: gh().repo(), '{"name": "demo"}')
        self.answers("ISSUE-VIEW without a label list (gh)", lambda: gh().labels(27), "{}")
        self.answers("ISSUE-VIEW without a label list (glab)", lambda: gl().labels(27),
                     '{"labels": "a,b"}')
        self.answers("THREADS-LIST with an unexpected shape",
                     with_repo(lambda api: api.unresolved_threads(41)), '{"data": {}}')
        self.answers("THREADS-LIST promising a next page with no cursor",
                     with_repo(lambda api: api.unresolved_threads(41)),
                     json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": {
                         "pageInfo": {"hasNextPage": True, "endCursor": None},
                         "nodes": [{"isResolved": False}]}}}}}))

    def test_cli_missing(self):
        d = tempfile.mkdtemp()
        old = os.environ["PATH"]
        os.environ["PATH"] = d
        try:
            with self.subTest("roz-state: the forge CLI is not installed → a failed read"):
                with self.assertRaises(state_collect.ReadFailed):
                    state_collect.run(["gh", "repo", "view", "--json", "owner,name"])
        finally:
            os.environ["PATH"] = old
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
