"""hooks/state_check.py and bin/roz-check — the entry preconditions of
integrate as rules over a roz-state snapshot (references/roz-check.md,
#134). Every case starts from one all-pass snapshot and changes one thing.

Red-proof, by mutation of the checker (recorded in the commit message).
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
ROOT = HOOKS.parent
sys.path.insert(0, str(HOOKS))
import state_check as ck  # noqa: E402
import state_contract as sc  # noqa: E402

TOOL = str(ROOT / "bin" / "roz-check")
HEAD = "cd34"


def obs(value, source="op"):
    return {"status": "observed", "value": value, "source": source}


def absent(source="op"):
    return {"status": "absent", "value": None, "source": source}


def unknown(reason="forge_query_failed", source="op"):
    return {"status": "unknown", "value": None, "source": source, "reason": reason}


def cr(number, state="open", draft=False, base="spec/27", head=HEAD):
    return obs({"number": number, "state": state, "draft": draft, "base": base,
                "head_sha": head}, "CR-FIND")


def green():
    """An issue integrate may start on: both CRs there, reviewed, audited."""
    return {
        "schema": sc.SCHEMA, "observed_at": "2026-11-12T01:00:00Z",
        "issue": 27, "track": "spec", "status": None,
        "processing": False, "blocked": False,
        "config": {"branch_template": "{kind}/{n}", "default_branch": "main",
                   "acceptance_dir": "tests/acceptance"},
        "branches": {"spec": obs({"name": "spec/27", "sha": "ab12"}),
                     "implementation": obs({"name": "feat/27", "sha": HEAD}),
                     "qa": obs({"name": "qa/27", "sha": "ef56"})},
        "spec": {"cr": cr(40, base="main", head="ab12")},
        "implementation": {"cr": cr(41, "merged"), "open_review_threads": obs(0, "THREADS-LIST"),
                           "review_marker": obs({"reviewed_sha": HEAD, "comment_id": 9001},
                                                "CR-COMMENTS-LIST")},
        "qa": {"cr": cr(42, head="ef56"), "open_fidelity_threads": obs(0, "THREADS-LIST"),
               "fidelity_marker": obs({"reviewed_sha": None, "comment_id": 9100},
                                      "CR-COMMENTS-LIST")},
        "dependencies": {"blocked_by": obs([])},
    }


def put(snap, path, value):
    node = snap
    keys = path.split(".")
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value
    return snap


IMPL_DEPS = ("IMPLEMENTATION_REVIEW_THREADS_CLEAR", "IMPLEMENTATION_REVIEW_RECORDED",
             "IMPLEMENTATION_REVIEW_CURRENT")
QA_DEPS = ("QA_CR_NOT_DRAFT", "FIDELITY_THREADS_CLEAR", "FIDELITY_AUDIT_RECORDED")


def no_impl(s, env):
    put(s, "implementation.cr", env)
    dep = absent() if env["status"] == "absent" else unknown("depends_on_unknown")
    put(s, "implementation.open_review_threads", dep)
    put(s, "implementation.review_marker", dep)
    return s


def no_qa(s, env):
    put(s, "qa.cr", env)
    dep = absent() if env["status"] == "absent" else unknown("depends_on_unknown")
    put(s, "qa.open_fidelity_threads", dep)
    put(s, "qa.fidelity_marker", dep)
    return s


class Check(unittest.TestCase):
    def result(self, name, snap, verdict, failed=(), unknown_=(), not_evaluated=()):
        r = ck.check_integrate(snap)
        st = {x["code"]: x["status"] for x in r["rules"]}
        with self.subTest("roz-check: %s → %s %s" % (name, verdict, list(failed) or "")):
            self.assertEqual((r["verdict"], r["failed"], r["unknown"]),
                             (verdict, list(failed), list(unknown_)))
            self.assertEqual(r["may_start"], verdict == "eligible")
            self.assertEqual(sorted(c for c, s in st.items() if s == "not_evaluated"),
                             sorted(not_evaluated))
        return r

    def test_green(self):
        r = self.result("every precondition holds", green(), "eligible")
        with self.subTest("roz-check: the result names the operation, the issue and all 13 "
                          "rules, in § 1's order"):
            self.assertEqual((r["schema"], r["operation"], r["issue"]),
                             (ck.SCHEMA, "integrate", 27))
            self.assertEqual([x["code"] for x in r["rules"]], [c for c, *_ in ck.INTEGRATE])
            self.assertEqual(len(r["rules"]), 13)
            self.assertTrue(all(x["status"] == "pass" for x in r["rules"]))
        s = put(green(), "status", "in-user-review")
        self.result("status: in-user-review is the other legal entry", s, "eligible")
        s = put(green(), "qa.cr", cr(42, "merged", head="ef56"))
        self.result("both CRs merged (a re-verdict)", s, "eligible")
        s = put(green(), "branches.implementation", absent())
        self.result("the implementation head deleted after its CR merged (#272): the CR is "
                    "what the rule reads", s, "eligible")
        s = put(green(), "dependencies.blocked_by", unknown())
        self.result("a fact integrate's entry never reads (blockers) may be unknown", s,
                    "eligible")

    def test_each_rule_fails_alone(self):
        for name, change, code, deps in (
                ("track: fast", lambda s: put(s, "track", "fast"), "TRACK_NOT_FAST", ()),
                ("status: processing", lambda s: put(s, "processing", True), "NOT_LOCKED", ()),
                ("status: blocked", lambda s: put(s, "blocked", True), "NOT_BLOCKED", ()),
                ("status: ready-for-spec", lambda s: put(s, "status", "ready-for-spec"),
                 "ENTRY_STATUS_LEGAL", ()),
                ("status: ready-for-dev", lambda s: put(s, "status", "ready-for-dev"),
                 "ENTRY_STATUS_LEGAL", ()),
                ("status: in-spec-review", lambda s: put(s, "status", "in-spec-review"),
                 "ENTRY_STATUS_LEGAL", ()),
                ("status: in-dev", lambda s: put(s, "status", "in-dev"), "ENTRY_STATUS_LEGAL", ()),
                ("no spec branch", lambda s: put(s, "branches.spec", absent()),
                 "SPEC_BRANCH_EXISTS", ()),
                ("no implementation CR", lambda s: no_impl(s, absent()),
                 "IMPLEMENTATION_CR_EXISTS", IMPL_DEPS),
                ("a closed-unmerged implementation CR counts as absent",
                 lambda s: put(s, "implementation.cr", cr(41, "closed")),
                 "IMPLEMENTATION_CR_EXISTS", IMPL_DEPS),
                ("no QA CR", lambda s: no_qa(s, absent()), "QA_CR_EXISTS", QA_DEPS),
                ("a closed-unmerged QA CR counts as absent",
                 lambda s: put(s, "qa.cr", cr(42, "closed", head="ef56")), "QA_CR_EXISTS",
                 QA_DEPS),
                ("an open review thread",
                 lambda s: put(s, "implementation.open_review_threads", obs(1)),
                 "IMPLEMENTATION_REVIEW_THREADS_CLEAR", ()),
                ("no code-review record (zero threads because nobody reviewed)",
                 lambda s: put(s, "implementation.review_marker", absent()),
                 "IMPLEMENTATION_REVIEW_RECORDED", ("IMPLEMENTATION_REVIEW_CURRENT",)),
                ("a stale code-review record",
                 lambda s: put(s, "implementation.review_marker",
                               obs({"reviewed_sha": "0ld", "comment_id": 9001})),
                 "IMPLEMENTATION_REVIEW_CURRENT", ()),
                ("a code-review record with no readable sha",
                 lambda s: put(s, "implementation.review_marker",
                               obs({"reviewed_sha": None, "comment_id": 9001})),
                 "IMPLEMENTATION_REVIEW_CURRENT", ()),
                ("a draft QA CR", lambda s: put(s, "qa.cr", cr(42, draft=True, head="ef56")),
                 "QA_CR_NOT_DRAFT", ()),
                ("open fidelity findings",
                 lambda s: put(s, "qa.open_fidelity_threads", obs(2)),
                 "FIDELITY_THREADS_CLEAR", ()),
                ("no fidelity audit on record (zero threads because nobody audited, #95)",
                 lambda s: put(s, "qa.fidelity_marker", absent()),
                 "FIDELITY_AUDIT_RECORDED", ())):
            self.result(name, change(green()), "ineligible", [code], not_evaluated=deps)

    def test_each_fact_unknown(self):
        for name, change, code, deps in (
                ("the spec branch unknown", lambda s: put(s, "branches.spec",
                                                          unknown("remote_unreachable")),
                 "SPEC_BRANCH_EXISTS", ()),
                ("the implementation CR unknown", lambda s: no_impl(s, unknown()),
                 "IMPLEMENTATION_CR_EXISTS", IMPL_DEPS),
                ("the QA CR unknown", lambda s: no_qa(s, unknown("ambiguous")),
                 "QA_CR_EXISTS", QA_DEPS),
                ("the review threads unknown",
                 lambda s: put(s, "implementation.open_review_threads", unknown()),
                 "IMPLEMENTATION_REVIEW_THREADS_CLEAR", ()),
                ("the code-review record unknown",
                 lambda s: put(s, "implementation.review_marker", unknown()),
                 "IMPLEMENTATION_REVIEW_RECORDED", ("IMPLEMENTATION_REVIEW_CURRENT",)),
                ("the fidelity threads unknown",
                 lambda s: put(s, "qa.open_fidelity_threads", unknown()),
                 "FIDELITY_THREADS_CLEAR", ()),
                ("the fidelity record unknown",
                 lambda s: put(s, "qa.fidelity_marker", unknown()),
                 "FIDELITY_AUDIT_RECORDED", ())):
            r = self.result(name, change(green()), "unknown", unknown_=[code],
                            not_evaluated=deps)
            rule = [x for x in r["rules"] if x["code"] == code][0]
            with self.subTest("roz-check: %s — the rule carries the fact's reason" % name):
                self.assertEqual(rule["reason"], rule["evidence"][0]["fact"]["reason"])
                self.assertIn(rule["reason"], sc.REASONS)

    def test_acceptance_pairs(self):
        """#134's four distinctions, each as two different results."""
        missing = ck.check_integrate(put(green(), "qa.fidelity_marker", absent()))
        clean = ck.check_integrate(green())
        open_ = ck.check_integrate(put(green(), "qa.open_fidelity_threads", obs(1)))
        draft = ck.check_integrate(put(green(), "qa.cr", cr(42, draft=True, head="ef56")))
        gone = ck.check_integrate(no_qa(green(), absent()))
        with self.subTest("roz-check: a missing fidelity audit differs from a completed "
                          "clean audit"):
            self.assertEqual((missing["failed"], clean["failed"]),
                             (["FIDELITY_AUDIT_RECORDED"], []))
        with self.subTest("roz-check: open fidelity findings differ from a missing audit"):
            self.assertEqual((open_["failed"], missing["failed"]),
                             (["FIDELITY_THREADS_CLEAR"], ["FIDELITY_AUDIT_RECORDED"]))
        with self.subTest("roz-check: a draft QA CR differs from a missing QA CR"):
            self.assertEqual((draft["failed"], gone["failed"]),
                             (["QA_CR_NOT_DRAFT"], ["QA_CR_EXISTS"]))
        with self.subTest("roz-check: every illegal entry state has its own code"):
            codes = {c for c, *_ in ck.INTEGRATE}
            self.assertTrue({"TRACK_NOT_FAST", "NOT_LOCKED", "NOT_BLOCKED",
                             "ENTRY_STATUS_LEGAL"} <= codes)

    def test_combinations(self):
        s = put(green(), "qa.fidelity_marker", absent())
        put(s, "implementation.open_review_threads", unknown())
        self.result("a fail and an unknown: the known blocker wins, both are listed", s,
                    "ineligible", ["FIDELITY_AUDIT_RECORDED"],
                    ["IMPLEMENTATION_REVIEW_THREADS_CLEAR"])
        s = put(green(), "processing", True)
        put(s, "qa.cr", cr(42, draft=True, head="ef56"))
        put(s, "qa.open_fidelity_threads", obs(3))
        self.result("three fails, in § 1's order", s, "ineligible",
                    ["NOT_LOCKED", "QA_CR_NOT_DRAFT", "FIDELITY_THREADS_CLEAR"])
        s = no_qa(no_impl(green(), absent()), unknown())
        self.result("a missing CR and an unknown CR: one root cause each", s, "ineligible",
                    ["IMPLEMENTATION_CR_EXISTS"], ["QA_CR_EXISTS"], IMPL_DEPS + QA_DEPS)
        s = put(green(), "implementation.review_marker", unknown())
        put(s, "qa.open_fidelity_threads", unknown("unsupported"))
        self.result("two unknowns", s, "unknown", unknown_=[
            "IMPLEMENTATION_REVIEW_RECORDED", "FIDELITY_THREADS_CLEAR"],
            not_evaluated=("IMPLEMENTATION_REVIEW_CURRENT",))
        s = put(green(), "track", None)
        self.result("no track label: § 1 stops only `fast`", s, "eligible")

    def test_propagation(self):
        """#134 amendment 3: prerequisite pass → evaluated; fail → not_evaluated;
        unknown → not_evaluated — for every edge, and transitively."""
        edges = {c: req for c, req, *_ in ck.INTEGRATE if req}
        with self.subTest("roz-check: the prerequisite edges are these six"):
            self.assertEqual(edges, {
                "IMPLEMENTATION_REVIEW_THREADS_CLEAR": "IMPLEMENTATION_CR_EXISTS",
                "IMPLEMENTATION_REVIEW_RECORDED": "IMPLEMENTATION_CR_EXISTS",
                "IMPLEMENTATION_REVIEW_CURRENT": "IMPLEMENTATION_REVIEW_RECORDED",
                "QA_CR_NOT_DRAFT": "QA_CR_EXISTS",
                "FIDELITY_THREADS_CLEAR": "QA_CR_EXISTS",
                "FIDELITY_AUDIT_RECORDED": "QA_CR_EXISTS"})
        roots = {"IMPLEMENTATION_CR_EXISTS": no_impl, "QA_CR_EXISTS": no_qa}
        for root, breaker in roots.items():
            for label, env in (("fails", absent()), ("is unknown", unknown())):
                r = ck.check_integrate(breaker(green(), env))
                st = {x["code"]: x for x in r["rules"]}
                for code, req in edges.items():
                    top = req if req in roots else edges[req]
                    if top != root:
                        continue
                    with self.subTest("roz-check: %s %s → %s is not_evaluated, names its "
                                      "direct prerequisite, and is in neither list"
                                      % (root, label, code)):
                        self.assertEqual((st[code]["status"], st[code]["requires"],
                                          st[code]["evidence"]), ("not_evaluated", req, []))
                        self.assertNotIn(code, r["failed"] + r["unknown"])
        r = ck.check_integrate(green())
        with self.subTest("roz-check: a passing prerequisite → every dependent is evaluated "
                          "and still names it"):
            for x in r["rules"]:
                if x["code"] in edges:
                    self.assertEqual((x["status"], x["requires"]), ("pass", edges[x["code"]]))

    def test_evidence(self):
        """#134 amendment 2: the exact fact the rule read, never a paraphrase."""
        s = put(green(), "qa.open_fidelity_threads", unknown("forge_query_failed",
                                                             "THREADS-LIST"))
        r = ck.check_integrate(s)
        by = {x["code"]: x for x in r["rules"]}
        with self.subTest("roz-check: an unknown fact is kept whole — status, value, source, "
                          "reason"):
            self.assertEqual(by["FIDELITY_THREADS_CLEAR"]["evidence"], [
                {"path": "qa.open_fidelity_threads",
                 "fact": {"status": "unknown", "value": None, "source": "THREADS-LIST",
                          "reason": "forge_query_failed"}}])
        with self.subTest("roz-check: an observed fact is kept whole, source included"):
            self.assertEqual(by["FIDELITY_AUDIT_RECORDED"]["evidence"], [
                {"path": "qa.fidelity_marker", "fact": s["qa"]["fidelity_marker"]}])
        with self.subTest("roz-check: a plain value is path + value"):
            self.assertEqual(by["ENTRY_STATUS_LEGAL"]["evidence"],
                             [{"path": "status", "value": None}])
            self.assertEqual(by["NOT_LOCKED"]["evidence"], [{"path": "processing",
                                                             "value": False}])
        with self.subTest("roz-check: a rule that compares two facts lists both"):
            self.assertEqual(by["IMPLEMENTATION_REVIEW_CURRENT"]["evidence"], [
                {"path": "implementation.review_marker",
                 "fact": s["implementation"]["review_marker"]},
                {"path": "implementation.cr", "fact": s["implementation"]["cr"]}])
        with self.subTest("roz-check: every evaluated rule has evidence, and each envelope "
                          "entry equals the snapshot's fact"):
            for x in r["rules"]:
                self.assertTrue(x["evidence"], x["code"])
                for e in x["evidence"]:
                    if "fact" in e:
                        node = s
                        for k in e["path"].split("."):
                            node = node[k]
                        self.assertEqual(e["fact"], node)
        with self.subTest("roz-check: evidence is a copy — changing the result leaves the "
                          "snapshot alone"):
            by["FIDELITY_AUDIT_RECORDED"]["evidence"][0]["fact"]["value"]["comment_id"] = 0
            self.assertEqual(s["qa"]["fidelity_marker"]["value"]["comment_id"], 9100)

    def test_pure_and_strict(self):
        s = put(green(), "qa.fidelity_marker", absent())
        before = copy.deepcopy(s)
        ck.check_integrate(s)
        with self.subTest("roz-check: the snapshot is not modified"):
            self.assertEqual(s, before)
        for name, bad in (("a bare count", put(green(), "qa.open_fidelity_threads", 0)),
                          ("a policy field", put(green(), "review_clean", True)),
                          ("a typed collection failure",
                           {"schema": sc.SCHEMA, "collection_failure": {
                               "reason": "forge_query_failed", "source": "ISSUE-VIEW"}})):
            with self.subTest("roz-check: %s is refused, never checked" % name):
                with self.assertRaises(ck.InvalidSnapshot):
                    ck.check_integrate(bad)
        with self.subTest("roz-check: an operation it does not know is an error, not a pass"):
            with self.assertRaises(KeyError):
                ck.check("merge", green())
        with self.subTest("roz-check: the policy module asks nothing of the forge or git"):
            src = (HOOKS / "state_check.py").read_text(encoding="utf-8")
            for word in ("subprocess", "state_collect", "branch_names", "open(", "os."):
                self.assertNotIn(word, src)

    def cli(self, args, snap=None):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "s.json")
        if snap is not None:
            Path(path).write_text(json.dumps(snap), encoding="utf-8")
        p = subprocess.run([sys.executable, TOOL, *[path if a == "@" else a for a in args]],
                           cwd=d, capture_output=True, text=True)
        try:
            obj = json.loads(p.stdout) if p.stdout.strip() else None
        except ValueError:
            obj = "UNPARSEABLE"
        return p.returncode, obj, p.stderr

    def test_cli(self):
        rc, obj, err = self.cli(["integrate", "27", "--json", "--state", "@"], green())
        with self.subTest("roz-check CLI: --state, eligible → exit 0"):
            self.assertEqual((rc, obj["verdict"], obj["may_start"]), (0, "eligible", True))
        rc, obj, err = self.cli(["integrate", "27", "--json", "--state", "@"],
                                put(green(), "qa.fidelity_marker", absent()))
        with self.subTest("roz-check CLI: ineligible is an answer → exit 0, the code in "
                          "`failed`"):
            self.assertEqual((rc, obj["verdict"], obj["failed"]),
                             (0, "ineligible", ["FIDELITY_AUDIT_RECORDED"]))
        fail = {"schema": sc.SCHEMA, "collection_failure": {
            "reason": "forge_query_failed", "source": "ISSUE-VIEW"}}
        rc, obj, err = self.cli(["integrate", "27", "--json", "--state", "@"], fail)
        with self.subTest("roz-check CLI: a typed collection failure is passed through → "
                          "exit 2, no verdict"):
            self.assertEqual((rc, obj), (2, fail))
        rc, obj, err = self.cli(["integrate", "28", "--json", "--state", "@"], green())
        with self.subTest("roz-check CLI: a snapshot of another issue → exit 65, nothing on "
                          "stdout"):
            self.assertEqual((rc, obj), (65, None))
        rc, obj, err = self.cli(["integrate", "27", "--json", "--state", "@"],
                                put(green(), "next_action", "integrate"))
        with self.subTest("roz-check CLI: --state that is not a valid snapshot → exit 65"):
            self.assertEqual((rc, obj), (65, None))
            self.assertIn("policy field", err)
        rc, obj, err = self.cli(["integrate", "27", "--json", "--state", "/nonexistent.json"])
        with self.subTest("roz-check CLI: an unreadable --state file → exit 65"):
            self.assertEqual((rc, obj), (65, None))
        for args in ([], ["integrate"], ["integrate", "27"], ["merge", "27", "--json"],
                     ["integrate", "x", "--json"], ["integrate", "27", "9", "--json"]):
            rc, obj, err = self.cli(args)
            with self.subTest("roz-check CLI: usage %r → exit 64" % (args,)):
                self.assertEqual((rc, obj), (64, None))
        rc, obj, err = self.cli(["integrate", "27", "--json"])
        with self.subTest("roz-check CLI: without --state it collects through roz-state — "
                          "outside a repository, its typed failure, exit 2"):
            self.assertEqual(rc, 2)
            self.assertEqual(sc.validate_failure(obj), [])


if __name__ == "__main__":
    unittest.main()
