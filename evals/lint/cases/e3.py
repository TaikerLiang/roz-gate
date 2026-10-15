"""E3 · the implementer can stop and ask at stage (3)        (defect: 1.12.0-)
"""

from lib.lintkit import c, read, section

META = {
    "id": 'E3',
    "title": 'the implementer can stop and ask at stage (3)',
    "tier": 'lint (defect 1.12.0-)',
    "ledger": None,
}

b3 = section(read("commands/next-stage.md"), r"^### B3\. Dispatch", r"^### B4\. ")
c.expect("pattern", "E3: stage-(3) dispatch states the contract-gap stop route",
         "A contract gap you cannot resolve" in b3)
c.expect("pattern", "E3: unilateral in-code decisions are forbidden explicitly",
         "never decide unilaterally" in b3)
