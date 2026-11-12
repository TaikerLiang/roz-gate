"""J2 · the Judgment V1 corpus is approved, leak-free and scored as stated   (#258)
Judgment V1 (`evals/judgment/v1/`) scores one frozen decision snapshot per
item against a human ruling. Its oracle is only as good as three things no
model run can check: that every item was approved, that no snapshot carries
anything from after its decision point, and that the scorer computes what
the README says. This case runs the corpus check and the scorer's red-proof
(canned answer sets against hand-computed numbers — no model) on every
push, and holds the judge's red-proof documents complete.
"""

import json
import os
import sys

from lib.lintkit import R, c, read

META = {
    "id": "J2",
    "title": "the Judgment V1 corpus is approved, leak-free and scored as stated",
    "tier": "lint (#258)",
    "ledger": "Every Judgment V1 item validates, is approved, takes its next action from its "
              "seat's one vocabulary and belongs to a family that sits in one set only; no "
              "snapshot names its source issue, a forbidden phrase or a decision class; all "
              "three classes are present; the scorer reproduces the hand-computed numbers and "
              "prints the validity line; every judged item has yes and no red-proof documents "
              "(#258: a judgment corpus is only as good as its gold and its blindness).",
}

V1 = os.path.join(R, "evals", "judgment", "v1")
sys.path.insert(0, V1)
import run_v1  # noqa: E402

_items, _actions = run_v1.load_items(), run_v1.load_actions()
_bad = run_v1.check(_items, _actions)
c.expect("pattern", "J2: the corpus check is clean%s"
         % ("" if not _bad else " — " + "; ".join(_bad)), not _bad)
_cc = run_v1.class_counts(_items) if not _bad else {}
c.expect("pattern", "J2: all three classes are present (%s)"
         % ", ".join("%s %d" % kv for kv in _cc.items()), bool(_cc) and all(_cc.values()))
_sbad = run_v1.scorer_redproof(_items, _actions) if not _bad else ["corpus check failed"]
c.expect("pattern", "J2: the scorer reproduces the hand-computed numbers%s"
         % ("" if not _sbad else " — " + "; ".join(_sbad)), not _sbad)

_judge = json.loads(read("evals/judgment/v1/redproof/judge.json"))
for _iid, _it in sorted(_items.items()):
    if _it.get("gold", {}).get("surfaced"):
        _d = _judge.get(_iid, {})
        c.expect("pattern", "J2: %s has judge red-proof documents (yes, and two no)" % _iid,
                 len(_d.get("yes", [])) >= 1 and len(_d.get("no", [])) >= 2)

_readme = " ".join(read("evals/judgment/v1/README.md").split())
c.expect("pattern", "J2: the README scopes the action vocabulary",
         "it does not measure free-form action discovery" in _readme)
c.expect("pattern", "J2: the README bounds the claim to the development set",
         "needs holdout evidence" in _readme)

# codex review, PR #285 — a malformed answer is INVALID and recorded, never a crash
_qa = _items.get("J-expiry-unit")
for _name, _raw in (
        ("a list for next_action", '{"decision": "BLOCK", "next_action": ["fix_harness"]}'),
        ("an object for next_action", '{"decision": "BLOCK", "next_action": {"id": "x"}}'),
        ("a list for decision", '{"decision": ["BLOCK"], "next_action": "fix_harness"}'),
        ("a list for surfaced",
         '{"decision": "BLOCK", "next_action": "stop_and_report", "surfaced": ["a"]}'),
        ("a JSON array", '["BLOCK"]')):
    try:
        _ans, _why = run_v1.parse_answer(_raw, _qa, _actions)
        _ok = _ans is None and bool(_why)
    except Exception as _e:  # noqa: BLE001 — the crash is the defect under test
        _ok, _why = False, "raised %s" % type(_e).__name__
    c.expect("pattern", "J2: %s is INVALID, not a crash (%s)" % (_name, _why), _ok)

# codex review, PR #285 — a result scored under an older brief, snapshot,
# frame or gold is never aggregated with today's
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as _d:
    _row = {"item": "J-expiry-unit", "arm": "treatment", "valid": True,
            "decision": "NO_FINDING", "next_action": "write_the_test", "surfaced": False,
            "key_point": None}
    _fp = getattr(run_v1, "run_fingerprint", lambda *a: "none")(_qa, "treatment", _actions)
    for _dir, _decision in (("fp-%s" % _fp, "FLAG_AND_CONTINUE"), ("fp-0000000000000000", "BLOCK")):
        _p = os.path.join(_d, "sut", "treatment", "J-expiry-unit", _dir, "run-1")
        os.makedirs(_p)
        with open(os.path.join(_p, "result.json"), "w", encoding="utf-8") as _f:
            json.dump(dict(_row, decision=_decision), _f)
    try:
        _cur, _stale = run_v1.load_results("sut", _items, _actions, root=_d)
        _ok = ([r["decision"] for r in _cur] == ["FLAG_AND_CONTINUE"]
               and [r["decision"] for r in _stale] == ["BLOCK"])
    except Exception as _e:  # noqa: BLE001
        _ok = False
    c.expect("pattern", "J2: a stale result is separated from the current ones", _ok)

# codex review, PR #285 — a key-point verdict from another judge configuration
# is never counted in today's column; the SUT's answer itself stays current
with tempfile.TemporaryDirectory() as _d:
    _row = {"item": "J-expiry-unit", "arm": "treatment", "valid": True,
            "decision": "FLAG_AND_CONTINUE", "next_action": "raise_question_and_write_the_test",
            "surfaced": True, "key_point": "yes"}
    for _i, _jfp in ((1, "judge-now"), (2, "judge-then")):
        _p = os.path.join(_d, "sut", "treatment", "J-expiry-unit", "fp-%s" % _fp, "run-%d" % _i)
        os.makedirs(_p)
        with open(os.path.join(_p, "result.json"), "w", encoding="utf-8") as _f:
            json.dump(dict(_row, judge_fingerprint=_jfp), _f)
    try:
        _cur, _stale = run_v1.load_results("sut", _items, _actions, root=_d,
                                           judge_fp="judge-now")
        _rep = run_v1.sc.score(_items, _cur)["treatment"]
        _ok = (len(_cur) == 2 and not _stale
               and sorted(r["key_point"] for r in _cur) == ["judge-stale", "yes"]
               and _rep["key_point"]["of"] == 1 and _rep["key_point"]["judge_stale"] == 1
               and _rep["recall"]["of"] == 2
               and "judge-stale: 1" in run_v1.sc.render({"treatment": _rep}))
    except Exception as _e:  # noqa: BLE001
        _ok = False
    c.expect("pattern", "J2: a verdict from another judge configuration is not counted", _ok)
