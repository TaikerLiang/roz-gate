"""C14 · the fix-and-rerun cap is `fix_rounds`, and the cap STOP carries the
ledger and the three doors                          (defect: 1.30.0-, #78)
The cap was a literal 3 in two commands, anchored nowhere, and the
STOP at the cap had no shape beyond the generic one; a target repo
hit it after four harness fixes with nothing to turn.
"""

import re

from lib.lintkit import c, must_not_match, read, section, src

META = {
    "id": 'C14',
    "title":
        'the fix-and-rerun cap is `fix_rounds`, and the cap STOP carries the ledger and the '
        'three doors',
    "tier": 'lint (defect 1.30.0-, #78)',
    "ledger": None,
}

_ig = read("commands/integrate.md")
_ra = read("commands/review-answers.md")
_ig0 = re.sub(r"\s+", " ", section(_ig, r"^## 0\. ", r"^## 1\. "))
_ra0 = re.sub(r"\s+", " ", section(_ra, r"^## 0\. ", r"^## 1\. "))
_ig5 = re.sub(r"\s+", " ", section(_ig, r"^## 5\. ", r"^## 6\. "))
_ig6 = re.sub(r"\s+", " ", section(_ig, r"^## 6\. ", r"^## 7\. "))
_ig7 = re.sub(r"\s+", " ", section(_ig, r"^## 7\. ", r"(?!)"))  # to the end
_READ_RULE = ("**absent → 3; any other value → stop here, before the lock**, a config error "
              "like a missing block")
for _nm, _s in (("integrate", _ig0), ("review-answers", _ra0)):
    c.expect("pattern", "C14: %s §0 reads `fix_rounds` from the block" % _nm,
             "`acceptance_dir`, `fix_rounds`)" in _s)
    c.expect("pattern", "C14: %s §0 — absent is 3, anything else is a config error, never a "
             "default" % _nm, _READ_RULE in _s)
c.expect("pattern", "C14: integrate step 5 caps by config `fix_rounds`",
         "Cap: config **`fix_rounds`** fix-and-rerun rounds (absent → 3; `0` → every RED is a "
         "STOP at once" in _ig5)
c.expect("pattern", "C14: the budget is per run — a cleared run starts at round 1",
         "counted **per run** — a run cleared from `blocked` starts at round 1" in _ig5)
c.expect("pattern", "C14: the cap STOP names the pattern and the three doors",
         "**The cap STOP**" in _ig6 and "*N rounds · class · file*" in _ig6
         and "**clear `blocked`**" in _ig6 and "**raise `fix_rounds`**" in _ig6
         and "**send it back**" in _ig6 and "information, not bad luck" in _ig6)
c.expect("pattern", "C14: the round ledger folds in the Evidence block",
         "`round · class · fixed · branch · sha · first failing line`" in _ig6
         and "Inside the Evidence block" in _ig6)
# codex review, PR #88: `fix_rounds: 0` has no fix round, so the ledger opens with the run
# that went red, and the pattern line degrades to that run's classification.
c.expect("pattern", "C14: the ledger opens with round 0 — the run that went red before any fix",
         "**round 0 — the run that went red before any fix**" in _ig6
         and "*0 of 0 — every RED stops at once*" in _ig6)
c.expect("pattern", "C14: the report names the rounds spent",
         "**rounds spent**" in _ig7)
c.expect("pattern", "C14: review-answers §6 caps by config `fix_rounds`",
         "Cap: config `fix_rounds` attempts (absent → 3;" in re.sub(r"\s+", " ", _ra))
for _f in ("commands/integrate.md", "commands/review-answers.md"):
    must_not_match("C14: %s carries no literal cap" % _f,
                   r"Cap: \*\*3\*\*|Cap: 3 attempts", read(_f))
src("C14: init documents `fix_rounds`", "commands/init.md",
    "- `fix_rounds` — optional: the fix-and-rerun budget on a red suite at (6)")
src("C14: README's block carries `fix_rounds`", "README.md",
    "- fix_rounds: 3                   # optional — fix-and-rerun rounds at (6) and in a (7) "
    "hand-back; absent = 3, 0 = every red stops")
src("C14: the onboarding builder offers `fix_rounds`", "docs/onboarding.html",
    "['fix_rounds',      () => $('f_rounds').value.trim()],")
