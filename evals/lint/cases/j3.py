"""J3 · the Workflow Value pilot pairs like with like                    (#259)
The pilot's Phase A (`evals/workflow-value.md`) runs the frozen ADMC
fixtures under two arms — the current loop, and a capable agent with no
loop — and prints them side by side. Three things decide whether that
table means anything, and no model run can check them: the baseline is
told nothing of the loop and is denied nothing an engineer would know; the
gold is the retrospective record and was reviewed by the gate holder; an
arm that never produced a valid run is not compared. This case runs the
pilot's unit tests (no model) and holds the fixtures' records.
"""

import json
import os
import sys

from lib.lintkit import R, c, read

META = {
    "id": "J3",
    "title": "the Workflow Value pilot pairs like with like",
    "tier": "lint (#259)",
    "ledger": "Every judgment fixture has a `retrospective.json` whose `important` / "
              "`immaterial` are exactly its P / N criteria and whose unknowns are listed; "
              "the baseline prompt carries no loop vocabulary and the baseline `CLAUDE.md` "
              "keeps the project's commands and drops the loop's section; the baseline sandbox "
              "is one root commit whose message, refs and objects hold nothing of that "
              "section; an INVALID arm or "
              "an unreviewed record is never paired; the report prints no cross-issue total "
              "(#259: a workflow-value comparison is only as fair as its baseline and its "
              "gold).",
}

J = os.path.join(R, "evals", "judgment")
sys.path.insert(0, os.path.join(J, "tests"))
import test_workflow_value  # noqa: E402

for _name, _ok in test_workflow_value.run():
    c.expect("pattern", "J3: %s" % _name, _ok)

sys.path.insert(0, J)
try:
    import workflow_value as _wv
except ImportError:
    _wv = None
_crit = json.loads(read("evals/judgment/criteria.json"))
_pol = {k: v["polarity"] for k, v in _crit.items() if not k.startswith("_")}
for _case in sorted(os.listdir(os.path.join(J, "cases"))):
    _dir = os.path.join(J, "cases", _case)
    if not os.path.isdir(_dir):
        continue
    _path = os.path.join(_dir, "retrospective.json")
    _have = os.path.exists(_path)
    c.expect("pattern", "J3: %s has a retrospective record" % _case, _have)
    if _have and _wv:
        _fx = json.loads(read(os.path.join("evals/judgment/cases", _case, "fixture.json")))
        _bad = _wv.validate_retrospective(json.loads(read(
            os.path.join("evals/judgment/cases", _case, "retrospective.json"))), _fx, _pol)
        c.expect("pattern", "J3: %s's record validates%s"
                 % (_case, "" if not _bad else " — " + "; ".join(_bad)), not _bad)

_prompt = read("evals/judgment/baseline-prompt.md") \
    if os.path.exists(os.path.join(J, "baseline-prompt.md")) else None
c.expect("pattern", "J3: the baseline prompt exists and has the issue slot",
         _prompt is not None and _prompt.count("{issue}") >= 1)
if _prompt and _wv:
    c.expect("pattern", "J3: the baseline prompt carries no loop vocabulary (%s)"
             % ", ".join(_wv.loop_words(_prompt)), not _wv.loop_words(_prompt))
_doc = " ".join(read("evals/workflow-value.md").split()) \
    if os.path.exists(os.path.join(R, "evals", "workflow-value.md")) else ""
c.expect("pattern", "J3: the protocol says what the pilot does not establish",
         "What the pilot does not establish" in _doc)
c.expect("pattern", "J3: the protocol states the decision rule", "Decision rule" in _doc)
c.expect("pattern", "J3: Phase B is a protocol, with its scripted human",
         "Phase B" in _doc and "scripted human" in _doc)
