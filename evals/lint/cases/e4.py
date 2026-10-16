"""E4 · the stage-(5) reviewer has the same route            (defect: 1.12.0-)
"""

from lib.lintkit import c, read, section

META = {
    "id": 'E4',
    "title": 'the stage-(5) reviewer has the same route',
    "tier": 'lint (defect 1.12.0-)',
    "ledger": None,
}

b5 = section(read("commands/next-stage.md"), r"^### B5\. ", r"^### B5b\. ")
c.expect("pattern", "E4: a contract-ambiguity finding routes to the spec CR",
         "contract ambiguity routes to a spec-CR" in b5)
c.expect("pattern", "E4: reviewer-to-implementer settlement is forbidden explicitly",
         "never settled" in b5)
