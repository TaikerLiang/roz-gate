"""L19 · the documents say what the instrument measured, and no more   (#280)
The root README kept a baseline headline — "replay 17/18 cases at 100%
(k=5)" — measured at v1.14–1.16, while the tier grew from 18 cases to 62;
the replay README said "F1–F5 k=10" when every `case.json` said 5; `pass^k`
named a probability the runner never reports; ROADMAP's "Current state" was
two months old; § Why promised a blindness the 2.0.0 topology no longer
gives. The recorded baselines are now data (`evals/replay/baselines.json`)
and their summary is rendered into `evals/README.md` by `tools/ledger.py`.
This case holds the data file honest about what the record does not say,
and holds the retired phrasings out.
"""

import json
import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "L19",
    "title": "the documents say what the instrument measured, and no more",
    "tier": "lint (#280)",
    "ledger": "Every batch in `evals/replay/baselines.json` names its source, an exact "
              "`plugin` or a `plugin_range`, an exact `date` or a `date_range`, and per case "
              "either counts (`passed ≤ valid ≤ k`) or the record's own `reported` words; the "
              "rendered block counts cases with at least one recorded baseline and picks no "
              "winner; the root README carries no baseline figure and no `never sees the "
              "implementation`; no page says `pass^k` or `k=10`; ROADMAP has no `Current "
              "state` heading (#280: prose headlines outlived the measurements behind them).",
}

PATH = "evals/replay/baselines.json"
_have = os.path.exists(os.path.join(R, PATH))
c.expect("pattern", "L19: %s exists" % PATH, _have)
_data = json.loads(read(PATH)) if _have else {}
_cases = {d for d in os.listdir(os.path.join(R, "evals", "replay", "cases"))
          if os.path.exists(os.path.join(R, "evals", "replay", "cases", d, "case.json"))}
_suts = set(re.findall(r"^(\w+):\s*\{", read("evals/replay/models.yaml"), re.M))
_bad = []
for _b in _data.get("replay", []):
    _id = _b.get("id", "?")
    if not _b.get("source"):
        _bad.append("%s: no source" % _id)
    if _b.get("sut") not in _suts:
        _bad.append("%s: sut %r is not a models.yaml row" % (_id, _b.get("sut")))
    for _exact, _range in (("plugin", "plugin_range"), ("date", "date_range")):
        if bool(_b.get(_exact)) == bool(_b.get(_range)):
            _bad.append("%s: exactly one of %s / %s" % (_id, _exact, _range))
    if _b.get("date") and not re.match(r"^\d{4}-\d{2}-\d{2}$", _b["date"]):
        _bad.append("%s: date is not YYYY-MM-DD" % _id)
    if not isinstance(_b.get("k"), int):
        _bad.append("%s: k is not an integer" % _id)
    for _r in _b.get("results", []):
        _w = "%s/%s" % (_id, _r.get("case"))
        if _r.get("case") not in _cases:
            _bad.append("%s: not a replay case" % _w)
        _counts = "valid" in _r or "passed" in _r
        if _counts == bool(_r.get("reported")):
            _bad.append("%s: counts (valid, passed) or `reported`, never both or neither" % _w)
        elif _counts and not (isinstance(_r.get("valid"), int) and isinstance(_r.get("passed"), int)
                              and 0 <= _r["passed"] <= _r["valid"] <= _b.get("k", 0)):
            _bad.append("%s: passed ≤ valid ≤ k does not hold" % _w)
    if not _b.get("results"):
        _bad.append("%s: no results" % _id)
c.expect("pattern", "L19: the baseline batches are honest and well-formed%s"
         % ("" if not _bad else " — " + "; ".join(_bad[:6])), _have and not _bad)
c.expect("pattern", "L19: there is at least one replay batch and the judgment entry",
         bool(_data.get("replay")) and bool(_data.get("judgment")))

_evals = read("evals/README.md")
_block = re.search(r"<!-- baselines -->\n(.*?)<!-- /baselines -->", _evals, re.S)
c.expect("pattern", "L19: evals/README.md has the rendered baselines block", bool(_block))
c.expect("pattern", "L19: the headline counts cases with at least one recorded baseline",
         bool(_block) and "at least one recorded SUT baseline" in _block.group(1))
c.expect("pattern", "L19: the block names the cases with no recorded baseline",
         bool(_block) and "No recorded baseline (" in _block.group(1))
c.expect("pattern", "L19: F6 reads as a detection limit",
         "no decay detected at n=3 sessions" in " ".join(_evals.split())
         and "no in-session decay observed" not in _evals)

_root = read("README.md")
_how = re.search(r"^## How we know it works\s*$(.*?)(?=^## )", _root, re.M | re.S)
_how = _how.group(1) if _how else ""
_figs = re.findall(r"\b\d+/\d+\b", _how)
c.expect("pattern", "L19: README § How we know it works carries no baseline figure (%s)"
         % ", ".join(_figs), bool(_how) and not _figs)
c.expect("pattern", "L19: README § How we know it works points at the rendered block",
         "evals/README.md" in _how and "Recorded baselines" in _how)
c.expect("pattern", "L19: README § Why no longer promises a blindness by topology",
         "never sees the implementation" not in _root and "hook rule E" in _root)

for _p in ("README.md", "evals/README.md", "evals/replay/README.md",
           "evals/ledger-template.md", "evals/LEDGER.md"):
    c.expect("pattern", "L19: %s does not say pass^k" % _p, "pass^k" not in read(_p))
_ks = sorted({json.loads(read(os.path.join("evals/replay/cases", d, "case.json"))).get("k")
              for d in _cases})
c.expect("pattern", "L19: the replay README does not claim k=10 (the cases say %s)" % _ks,
         "k=10" not in read("evals/replay/README.md") and 10 not in _ks)
c.expect("pattern", "L19: ROADMAP has no section that claims to be current",
         not re.search(r"^## Current state", read("docs/ROADMAP.md"), re.M))

# codex review, PR #289 — an instrument-only case has no pass mark: its
# driver writes a curve and the runner keeps it out of every pass count and
# interval. A baseline row may quote what the record says about it; it may
# not give it `passed / valid`, which the renderer would turn into a rate.
_curve = sorted(d for d in _cases if any(
    "instrument_only" in read(os.path.join("evals/replay/cases", d, f))
    for f in os.listdir(os.path.join(R, "evals", "replay", "cases", d)) if f.endswith(".py")))
c.expect("pattern", "L19: the instrument-only cases are found from their drivers (%s)"
         % ", ".join(_curve), bool(_curve))
_counted = sorted({_r["case"] for _b in _data.get("replay", []) for _r in _b.get("results", [])
                   if _r.get("case") in _curve and ("valid" in _r or "passed" in _r)})
c.expect("pattern", "L19: no instrument-only case is given a pass count (%s)"
         % ", ".join(_counted), _have and not _counted)
c.expect("pattern", "L19: the rendered block gives no instrument-only case an interval",
         bool(_block) and not any(re.search(r"\d+/\d+ \[[^\]]*\]: [^·|]*\b%s\b" % d,
                                            _block.group(1)) for d in _curve))
