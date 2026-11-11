"""hooks/state_contract.py — the roz-state observation contract as code
(references/roz-state.md, #239). The validator is pure; every case builds a
snapshot from one legal base and changes one thing.

Red-proof, by mutation of the validator (recorded in the commit message):
each check deleted → the case that names it fails.
"""

import copy
import json
import re
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS))
import state_contract as sc  # noqa: E402

DOC = HOOKS.parent / "references" / "roz-state.md"


def obs(value, source="op"):
    return {"status": "observed", "value": value, "source": source}


def absent(source="op"):
    return {"status": "absent", "value": None, "source": source}


def unknown(reason="forge_query_failed", source="op"):
    return {"status": "unknown", "value": None, "source": source, "reason": reason}


def cr(number=41, state="open", draft=False, base="spec/27/2", head="cd34"):
    return obs({"number": number, "state": state, "draft": draft, "base": base,
                "head_sha": head})


def base():
    """A legal mid-loop snapshot: implementation CR open, no QA yet."""
    return {
        "schema": sc.SCHEMA, "observed_at": "2026-11-11T01:00:00Z",
        "issue": 27, "track": "spec", "status": "in-dev",
        "processing": False, "blocked": False,
        "config": {"branch_template": "{kind}/{n}/{seq}", "default_branch": "main",
                   "acceptance_dir": "tests/acceptance"},
        "branches": {"spec": obs({"name": "spec/27/2", "sha": "ab12"}),
                     "implementation": obs({"name": "feat/27/2", "sha": "cd34"}),
                     "qa": absent()},
        "spec": {"cr": cr(40, "merged", base="main", head="ab12")},
        "implementation": {"cr": cr(), "open_review_threads": obs(0),
                           "review_marker": absent()},
        "qa": {"cr": absent(), "open_fidelity_threads": absent(),
               "fidelity_marker": absent()},
        "dependencies": {"blocked_by": obs([])},
    }


def put(snap, path, value):
    node = snap
    keys = path.split(".")
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value
    return snap


class Contract(unittest.TestCase):
    def ok(self, name, snap):
        with self.subTest("state_contract: valid — %s" % name):
            self.assertEqual(sc.validate(snap), [])

    def bad(self, name, snap, needle):
        with self.subTest("state_contract: rejected — %s" % name):
            errs = sc.validate(snap)
            self.assertTrue(any(needle in e for e in errs), "%r not in %r" % (needle, errs))

    def test_valid(self):
        self.ok("the base snapshot", base())
        s = base()
        for p in ("branches.spec", "branches.implementation", "spec.cr", "implementation.cr"):
            put(s, p, absent())
        for p in ("implementation.open_review_threads", "implementation.review_marker"):
            put(s, p, absent())
        self.ok("an early issue: every branch and CR absent, blockers observed []", s)
        s = base()
        put(s, "implementation.open_review_threads", unknown())
        put(s, "dependencies.blocked_by", unknown())
        put(s, "branches.qa", unknown("remote_unreachable"))
        self.ok("unknown facts beside observed ones", s)
        s = base()
        put(s, "qa.cr", cr(42, base="spec/27/2", head="ef56"))
        put(s, "qa.open_fidelity_threads", obs(0))
        put(s, "qa.fidelity_marker", obs({"reviewed_sha": "ef56", "comment_id": 9001}))
        put(s, "dependencies.blocked_by",
            obs([{"issue": 31, "state": "open", "url": "https://x/31"}]))
        self.ok("a QA CR with a fidelity marker and an open blocker", s)
        s = base()
        s["status"] = None
        self.ok("no status label worn: status null is an established fact", s)

    def test_doc_example(self):
        text = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
        m = re.search(r"^## Example\s*$.*?```json\n(.*?)```", text, re.M | re.S)
        with self.subTest("state_contract: references/roz-state.md § Example validates"):
            self.assertIsNotNone(m, "no ```json block under ## Example")
            self.assertEqual(sc.validate(json.loads(m.group(1))), [])
        with self.subTest("state_contract: the doc's example shows observed, absent and unknown"):
            self.assertIsNotNone(m)
            for st in sc.STATUSES:
                self.assertIn('"status": "%s"' % st, m.group(1))

    def test_absent_vs_observed_empty(self):
        """#239 amendment 3 — the table, row by row."""
        s = base()
        self.ok("the QA CR does not exist → qa.cr absent", s)
        s = put(base(), "qa.cr", cr(42))
        put(s, "qa.open_fidelity_threads", obs(0))
        self.ok("the QA CR exists, no fidelity marker → marker absent, threads observed 0", s)
        self.ok("the dependency query succeeds, no blockers → observed []", base())
        self.bad("blocked_by absent (the issue always exists: observed [] or unknown)",
                 put(base(), "dependencies.blocked_by", absent()),
                 "dependencies.blocked_by: never absent")
        self.bad("a count absent under an observed CR (absent is not zero)",
                 put(base(), "implementation.open_review_threads", absent()),
                 "implementation.open_review_threads: absent under an observed")
        self.bad("a dependent observed under an absent CR",
                 put(base(), "qa.open_fidelity_threads", obs(0)),
                 "qa.open_fidelity_threads: must be absent")
        s = put(base(), "implementation.cr", unknown())
        self.bad("a dependent not unknown under an unknown CR", s,
                 "implementation.open_review_threads: must be unknown")
        put(s, "implementation.open_review_threads", unknown("depends_on_unknown"))
        put(s, "implementation.review_marker", unknown("depends_on_unknown"))
        self.ok("the CR unknown → its count and marker unknown, depends_on_unknown", s)
        put(s, "implementation.review_marker", unknown("forge_query_failed"))
        self.bad("a dependent of an unknown CR with another reason", s,
                 "implementation.review_marker: reason must be depends_on_unknown")

    def test_envelope(self):
        self.bad("a bare number where an envelope is required (the #95 shape)",
                 put(base(), "implementation.open_review_threads", 0),
                 "implementation.open_review_threads: not an envelope")
        self.bad("a status outside the three",
                 put(base(), "branches.qa", {"status": "missing", "value": None, "source": "x"}),
                 "branches.qa: status")
        e = unknown()
        del e["reason"]
        self.bad("unknown without a reason", put(base(), "branches.qa", e),
                 "branches.qa: unknown needs a reason")
        self.bad("a reason outside the vocabulary",
                 put(base(), "branches.qa", unknown("dunno")), "branches.qa: reason")
        self.bad("a reason on an observed fact",
                 put(base(), "dependencies.blocked_by",
                     {**obs([]), "reason": "forge_query_failed"}),
                 "dependencies.blocked_by: reason only with unknown")
        self.bad("absent carrying a value",
                 put(base(), "branches.qa", {**absent(), "value": {"name": "qa/27", "sha": "x"}}),
                 "branches.qa: value must be null")
        self.bad("unknown carrying a value",
                 put(base(), "branches.qa", {**unknown(), "value": 0}),
                 "branches.qa: value must be null")
        e = obs(0)
        del e["source"]
        self.bad("an envelope without a source",
                 put(base(), "implementation.open_review_threads", e),
                 "implementation.open_review_threads: source")
        self.bad("observed with a null value",
                 put(base(), "implementation.cr", obs(None)), "implementation.cr: value")
        self.bad("an undeclared key inside an envelope",
                 put(base(), "branches.qa", {**absent(), "as_of": "now"}),
                 "branches.qa: undeclared key as_of")

    def test_value_shapes(self):
        self.bad("a negative count", put(base(), "implementation.open_review_threads", obs(-1)),
                 "implementation.open_review_threads: value")
        self.bad("a boolean count", put(base(), "implementation.open_review_threads", obs(True)),
                 "implementation.open_review_threads: value")
        self.bad("a CR state outside open / merged / closed",
                 put(base(), "implementation.cr", cr(state="draft")), "implementation.cr: value")
        v = cr()
        del v["value"]["base"]
        self.bad("a CR without its base", put(base(), "implementation.cr", v),
                 "implementation.cr: value")
        v = cr()
        v["value"]["approved"] = True
        self.bad("a CR value with an undeclared key", put(base(), "implementation.cr", v),
                 "implementation.cr: value")
        self.bad("a marker without reviewed_sha",
                 put(base(), "implementation.review_marker", obs({"comment_id": 1})),
                 "implementation.review_marker: value")
        self.bad("a blocker without its state",
                 put(base(), "dependencies.blocked_by", obs([{"issue": 31, "url": "u"}])),
                 "dependencies.blocked_by: value")
        self.bad("a branch without its sha",
                 put(base(), "branches.spec", obs({"name": "spec/27/2"})), "branches.spec: value")

    def test_plain_and_keys(self):
        for k in ("schema", "observed_at", "issue", "track", "status", "processing",
                  "blocked", "config", "branches", "dependencies"):
            s = base()
            del s[k]
            self.bad("missing top-level key %s" % k, s, "%s: missing" % k)
        self.bad("a plain value wrapped in an envelope", put(base(), "track", obs("spec")),
                 "track: plain value")
        self.bad("issue not an integer", put(base(), "issue", "27"), "issue: plain value")
        self.bad("processing not a boolean", put(base(), "processing", 0),
                 "processing: plain value")
        self.bad("another schema version", put(base(), "schema", "roz-state/9.9"),
                 "schema: this validator checks %s" % sc.SCHEMA)
        s = base()
        del s["config"]["default_branch"]
        self.bad("a config key missing", s, "config.default_branch: missing")
        self.bad("an unrelated config key (no dump of the whole block)",
                 put(base(), "config.review_tool", "codex"),
                 "config.review_tool: undeclared in %s" % sc.SCHEMA)
        s = base()
        del s["qa"]["fidelity_marker"]
        self.bad("a declared fact missing", s, "qa.fidelity_marker: missing")
        for ts, why in (("not-a-timestamp", "not a timestamp"),
                        ("2026-11-11T09:00:00+08:00", "an offset, not Z"),
                        ("2026-11-11T01:00:00", "no zone"),
                        ("2026-11-11 01:00:00Z", "a space, not T"),
                        ("2026-11-11T01:00:00.123Z", "fractional seconds"),
                        ("2026-13-41T01:00:00Z", "not a real date"),
                        ("2026-11-11", "a date only")):
            self.bad("observed_at %s (%s)" % (ts, why), put(base(), "observed_at", ts),
                     "observed_at: must be UTC as YYYY-MM-DDTHH:MM:SSZ")
        self.bad("a config value of the wrong type", put(base(), "config.default_branch", 3),
                 "config.default_branch: plain value")
        self.bad("an undeclared top-level key", put(base(), "labels", ["x"]),
                 "labels: undeclared in %s" % sc.SCHEMA)
        self.bad("a snapshot that is not an object", [base()], "snapshot: not an object")

    def test_policy_and_version(self):
        """#239 amendment 2 — two different errors."""
        for k in sc.POLICY_KEYS:
            self.bad("policy field %s at the top level" % k, put(base(), k, True),
                     "%s: policy field, never a fact" % k)
            s = base()
            s["qa"][k] = True
            self.bad("policy field %s nested" % k, s, "qa.%s: policy field, never a fact" % k)
        s = base()
        s["implementation"]["cr"]["value"]["review_clean"] = True
        self.bad("a policy field inside a fact's value", s,
                 "implementation.cr.value.review_clean: policy field, never a fact")
        self.bad("an undeclared observational key is a version error, not a policy error",
                 put(base(), "qa.labels", obs([])), "qa.labels: undeclared in %s" % sc.SCHEMA)
        with self.subTest("state_contract: an undeclared key is not reported as policy"):
            errs = sc.validate(put(base(), "qa.labels", obs([])))
            self.assertFalse(any("policy field" in e for e in errs))

    def test_collection_failure(self):
        """#239 amendment 1 — a snapshot or a typed failure, never a mix."""
        f = {"schema": sc.SCHEMA,
             "collection_failure": {"reason": "forge_query_failed", "source": "ISSUE-VIEW",
                                    "detail": "gh: HTTP 502"}}
        with self.subTest("state_contract: a collection failure validates as a failure"):
            self.assertEqual(sc.validate_failure(f), [])
        self.bad("a collection failure is not a snapshot", f, "not a snapshot: collection_failure")
        s = base()
        s["collection_failure"] = f["collection_failure"]
        self.bad("a snapshot carrying a collection_failure", s,
                 "not a snapshot: collection_failure")
        with self.subTest("state_contract: rejected — a failure with snapshot fields"):
            self.assertTrue(sc.validate_failure({**f, "issue": 27}))
        with self.subTest("state_contract: rejected — a failure without a reason"):
            g = copy.deepcopy(f)
            del g["collection_failure"]["reason"]
            self.assertTrue(sc.validate_failure(g))
        with self.subTest("state_contract: rejected — a failure reason outside the vocabulary"):
            g = copy.deepcopy(f)
            g["collection_failure"]["reason"] = "dunno"
            self.assertTrue(sc.validate_failure(g))
        with self.subTest("state_contract: rejected — a snapshot offered as a failure"):
            self.assertTrue(sc.validate_failure(base()))

        def bad_failure(name, obj, needle):
            with self.subTest("state_contract: rejected — %s" % name):
                errs = sc.validate_failure(obj)
                self.assertTrue(any(needle in e for e in errs), "%r not in %r" % (needle, errs))

        def cf(**change):
            g = copy.deepcopy(f)
            g["collection_failure"].update(change)
            return g

        bad_failure("a failure that is not an object", [f], "failure: not an object")
        bad_failure("a failure under another schema version", {**f, "schema": "roz-state/9.9"},
                    "schema: this validator checks %s" % sc.SCHEMA)
        bad_failure("a collection_failure that is not an object",
                    {**f, "collection_failure": "forge_query_failed"},
                    "collection_failure: not an object")
        bad_failure("a failure without its source", cf(source=""),
                    "collection_failure.source: required")
        bad_failure("a failure whose detail is not a string", cf(detail=502),
                    "collection_failure.detail: a string")
        bad_failure("a failure with an undeclared key", cf(issue=27),
                    "collection_failure.issue: undeclared")


if __name__ == "__main__":
    unittest.main()
