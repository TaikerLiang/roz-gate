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
    "ledger": "Every Judgment V1 item validates, is unapproved or carries a whole approval — "
              "name, date, a permalink to the review comment, and the fingerprint of the record "
              "and snapshot reviewed, which must still match (#296: a stale approval is a "
              "defect, starts no model call, and leaves the scorer red-proof runnable) — takes "
              "its next action from its "
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

# #258 follow-up review — plan approval is not gold approval. An item's
# approval is a state the repository records honestly, never a defect of
# the corpus: an unapproved item validates and is scored by the red-proof,
# and no model call — SUT or judge — may be spent on it.
_un = {k: dict(v, approved_by=None, approved_on=None, approved_ref=None, approved_fp=None)
       for k, v in _items.items()}
try:
    _ok = (not run_v1.check(_un, _actions)
           and sorted(run_v1.unapproved(_un)) == sorted(_un)
           and not run_v1.unapproved(
               {k: dict(v, approved_by="Paul Liang", approved_on="2026-11-13",
                        approved_ref="https://github.com/o/r/pull/1#pullrequestreview-1",
                        approved_fp=run_v1.review_fingerprint(v))
                for k, v in _items.items()})
           and "refuse" in (run_v1.spend_refusal(_un) or "")
           and run_v1.spend_refusal({}) is None)
except Exception as _e:  # noqa: BLE001
    _ok = False
c.expect("pattern", "J2: an unapproved item validates and cannot be run", _ok)
for _bad_stamp in ({"approved_by": "Paul Liang", "approved_on": None},
                   {"approved_by": None, "approved_on": "2026-11-13"},
                   {"approved_by": "Paul Liang", "approved_on": "yesterday"}):
    _half = dict(_items, **{"J-expiry-unit": dict(_items["J-expiry-unit"], **_bad_stamp)})
    c.expect("pattern", "J2: a half-stamped approval is a defect (%s)" % _bad_stamp,
             any("approval" in b for b in run_v1.check(_half, _actions)))
_fam = " ".join(read("evals/judgment/v1/README.md").split())
c.expect("pattern", "J2: the README freezes family provenance",
         "cannot be relabelled or split after a holdout run" in _fam)
c.expect("pattern", "J2: the README reports run-level frequency, not a pass/fail",
         "the human decides whether it warrants a brief change" in _fam)

# #296 — an approval is bound to the content it was given for. A stamp is
# four fields: who, when, a permalink to the review comment, and the
# fingerprint of the record and snapshot reviewed. The runner checks shape
# and fingerprint; it never fetches the comment and never learns who wrote
# it — the README says so, and J2 holds the sentence.
import contextlib  # noqa: E402
import io  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402

_REF = "https://github.com/TaikerLiang/roz-gate/pull/1#issuecomment-1"
_rf = getattr(run_v1, "review_fingerprint", lambda it: None)


def _stamp(it, **over):
    return dict(it, approved_by="Paul Liang", approved_on="2026-11-22", approved_ref=_REF,
                approved_fp=_rf(it), **over)


def _with(it):
    return dict(_items, **{"J-expiry-unit": it})


def _defects(it):
    try:
        return run_v1.check(_with(it), _actions)
    except Exception as _e:  # noqa: BLE001
        return ["raised %s" % type(_e).__name__]


_good = _stamp(_qa)
try:
    _ok = (not _defects(_good) and "J-expiry-unit" not in run_v1.unapproved(_with(_good))
           and run_v1.spend_refusal({"J-expiry-unit": _good}) is None)
except Exception as _e:  # noqa: BLE001
    _ok = False
c.expect("pattern", "J2: an approved record whose content is unchanged validates and may be run",
         _ok)

_gold = dict(_good, gold=dict(_good["gold"], decision="BLOCK"))
c.expect("pattern", "J2: a gold decision changed after the approval is a stale approval",
         any("stale approval" in b for b in _defects(_gold)))
_mat = dict(_good, materiality=_good["materiality"] + " And more.")
c.expect("pattern", "J2: any reviewed field changed after the approval is a stale approval",
         any("stale approval" in b for b in _defects(_mat)))

with tempfile.TemporaryDirectory() as _d:
    _same = os.path.join(_d, "same.md")
    shutil.copyfile(os.path.join(V1, _qa["snapshot"]), _same)
    _edited = os.path.join(_d, "edited.md")
    with open(_edited, "w", encoding="utf-8") as _f:
        _f.write(read("evals/judgment/v1/" + _qa["snapshot"]) + "\nOne more line.\n")
    # the approval names its evidence source: another path is another
    # record, even when the bytes there happen to match
    c.expect("pattern", "J2: a snapshot changed after the approval is a stale approval",
             any("stale approval" in b for b in _defects(dict(_good, snapshot=_edited))))
    c.expect("pattern", "J2: another snapshot path with the same bytes is a stale approval",
             any("stale approval" in b for b in _defects(dict(_good, snapshot=_same))))
    c.expect("pattern", "J2: a stamp whose snapshot is gone cannot be run",
             "stale" in (run_v1.spend_refusal(
                 {"J-expiry-unit": dict(_good, snapshot=os.path.join(_d, "absent.md"))}) or ""))

for _name, _over in (
        ("no approved_ref", {"approved_ref": None}),
        ("no approved_fp", {"approved_fp": None}),
        ("a bare pull request as approved_ref",
         {"approved_ref": "https://github.com/TaikerLiang/roz-gate/pull/1"}),
        ("an approved_ref that is not a GitHub comment",
         {"approved_ref": "https://example.com/pull/1#issuecomment-1"}),
        ("an approved_fp that is not 16 hex", {"approved_fp": "abc"}),
        ("evidence with no name and date", {"approved_by": None, "approved_on": None})):
    c.expect("pattern", "J2: incomplete approval evidence is a defect (%s)" % _name,
             any("half-stamped" in b for b in _defects(dict(_good, **_over))))
_draft = dict(_qa, approved_by=None, approved_on=None, approved_ref=None, approved_fp=None)
c.expect("pattern", "J2: a draft with four null approval fields validates and cannot be run",
         not _defects(_draft) and "J-expiry-unit" in run_v1.unapproved(_with(_draft)))

# the fingerprint: canonical, scoped to the record and its snapshot
_shuffled = dict(reversed(list(_qa.items())), gold=dict(reversed(list(_qa["gold"].items()))))
c.expect("pattern", "J2: the review fingerprint does not depend on key order or the file name",
         bool(_rf(_qa)) and _rf(_qa) == _rf(dict(_shuffled, _file="elsewhere.json")))
c.expect("pattern", "J2: the review fingerprint does not cover the approval fields",
         _rf(_good) == _rf(_qa) == _rf(_draft))
c.expect("pattern", "J2: the review fingerprint is 16 hex over the record and the snapshot",
         bool(re.match(r"^[0-9a-f]{16}$", str(_rf(_qa))))
         and len({_rf(_qa), _rf(_gold), _rf(_mat), _rf(dict(_qa, family="other")),
                  _rf(dict(_qa, key_point="Other?"))}) == 5)

# result identity is a separate thing and does not move: a result is still
# filed under the hash it had before the two evidence fields existed, and
# editing the approval trail alone neither moves it nor changes the gold
_legacy = {k: v for k, v in _draft.items() if k not in ("_file", "approved_ref", "approved_fp")}
c.expect("pattern", "J2: the evidence fields leave an item's result identity where it was",
         run_v1.item_hash(_draft) == run_v1.sha(json.dumps(_legacy, sort_keys=True))
         and "approved_ref" in _qa)
_ref2 = dict(_good, approved_ref=_REF + "2")
c.expect("pattern", "J2: editing only approved_ref moves neither the results nor the gold",
         run_v1.run_fingerprint(_ref2, "treatment", _actions)
         == run_v1.run_fingerprint(_good, "treatment", _actions)
         and _rf(_ref2) == _rf(_good) and not _defects(_ref2))
with tempfile.TemporaryDirectory() as _d:
    _row = {"item": "J-expiry-unit", "arm": "treatment", "valid": True,
            "decision": "FLAG_AND_CONTINUE", "next_action": "raise_question_and_write_the_test",
            "surfaced": True, "key_point": None}
    _p = os.path.join(_d, "sut", "treatment", "J-expiry-unit",
                      "fp-%s" % run_v1.run_fingerprint(_good, "treatment", _actions), "run-1")
    os.makedirs(_p)
    with open(os.path.join(_p, "result.json"), "w", encoding="utf-8") as _f:
        json.dump(_row, _f)
    try:
        _cur, _ = run_v1.load_results("sut", _with(_ref2), _actions, root=_d, judge_fp="j")
        _cur2, _stale2 = run_v1.load_results("sut", _with(_stamp(_gold)), _actions, root=_d,
                                             judge_fp="j")
        _ok = len(_cur) == 1 and not _cur2 and len(_stale2) == 1
    except Exception as _e:  # noqa: BLE001
        _ok = False
    c.expect("pattern", "J2: a result survives an approval-trail edit and goes stale with its gold",
             _ok)


# a stale approval spends nothing — and the scorer's red-proof, which
# calls no model, still runs on that corpus
def _main_on(items, argv):
    """(exit code, stdout, model calls) of run_v1.main on a patched corpus."""
    calls = []

    def _model(*a, **k):
        calls.append(a)
        raise RuntimeError("a model call was started")

    saved = (run_v1.load_items, run_v1.subprocess.run, run_v1.judge_module)
    run_v1.load_items, run_v1.subprocess.run, run_v1.judge_module = (lambda: items), _model, _model
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = run_v1.main(argv)
    except SystemExit as e:
        code = e.code
    except Exception as e:  # noqa: BLE001
        code = "raised %s" % type(e).__name__
    finally:
        run_v1.load_items, run_v1.subprocess.run, run_v1.judge_module = saved
    return code, out.getvalue(), len(calls)


_stale_corpus = {k: _stamp(v) for k, v in _items.items()}
_stale_corpus["J-expiry-unit"] = _mat    # the gold classes stand, so the scorer's numbers do
for _argv in (["--sut", "haiku55", "--arm", "treatment"],
              ["--sut", "haiku55", "--arm", "baseline", "J-clean-audit"],
              ["--redproof", "--rejudge"]):
    _code, _out, _calls = _main_on(_stale_corpus, _argv)
    c.expect("pattern", "J2: a stale approval starts no model call (%s → exit %s, %d call(s))"
             % (" ".join(_argv), _code, _calls),
             _code == 3 and _calls == 0 and "stale approval" in _out)
_code, _out, _calls = _main_on(_stale_corpus, ["--redproof"])
c.expect("pattern", "J2: on a stale approval the scorer red-proof still runs, with no model call",
         "PASS scorer red-proof (no model)" in _out and _calls == 0 and _code == 3)
_code, _out, _calls = _main_on(_stale_corpus, ["--check"])
c.expect("pattern", "J2: --check names the stale approval and what to do about it",
         _code == 3 and "reset the four approval fields to null" in _out)
_code, _out, _calls = _main_on(_items, ["--check"])
c.expect("pattern", "J2: --check prints each unapproved item's review fingerprint",
         _code == 0 and all("%s %s" % (k, _rf(v)) in _out for k, v in _items.items()
                            if k in run_v1.unapproved(_items)))
c.expect("pattern", "J2: --check does not call a recorded approval a verified one",
         "human authorization: not verified" in _out)

# the README's three levels — a well-shaped reference is an audit trail
_ap = " ".join(read("evals/judgment/v1/README.md").split())
for _phrase in ("**Recorded approval**", "**Auditable approval**",
                "**Verified human authorization** — not established",
                "never fetches the comment and cannot tell who wrote it"):
    c.expect("pattern", "J2: the README separates recorded, auditable and verified (%s)" % _phrase,
             _phrase in _ap)
