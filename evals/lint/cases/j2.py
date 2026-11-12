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
