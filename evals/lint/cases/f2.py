"""F2 · an answered item is posted `· answer`, a decision ask apart       (#384)
review-answers' rule 1 allowed `· answer`, `· question` or `· addressed` and
never said which one an item gets when it is answered and also needs a
decision. F2/run-2 (2026-11-17/18 sweep) answered review 501 with the fact at
a SHA, posted it as `· question` because it also asked three decisions, and
replay F2 (which counts `· answer` replies) went red. Ruled (b): the answer
goes first as `· answer`; the decision ask is a separate `· question`. This
case pins both clauses, each on its own, inside rule 1 of § 3's write rules.
Red-proofed by deleting the sentence, swapping `· answer` for `· question` in
its first clause, and moving it out of rule 1.
"""

import re

from lib.lintkit import c, read

META = {"id": "F2"}

_rule1 = re.search(r"^1\. It starts literally with .*?(?=^2\. )",
                   read("commands/review-answers.md"), re.S | re.M)
_rule1 = " ".join(_rule1.group(0).split()) if _rule1 else ""
for _clause in ("An item you can answer gets `· answer` first;",
                "a decision ask is a separate `· question`."):
    c.expect("pattern", "F2: review-answers § 3 rule 1 says: %s" % _clause, _clause in _rule1)
