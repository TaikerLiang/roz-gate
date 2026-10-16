"""D1 · the reviewer receives the claim it reviews against   (defect: 1.8.0-)
"""

from lib.lintkit import c, read, section

META = {
    "id": 'D1',
    "title": 'the reviewer receives the claim it reviews against',
    "tier": 'lint (defect 1.8.0-)',
    "ledger": None,
}

b5 = section(read("commands/next-stage.md"), r"^### B5\. ", r"^### B5b\. ")
c.expect("pattern", "D1: stage-(5) dispatch attaches spec.md",
         "spec.md" in b5)
c.expect("pattern", "D1: stage-(5) dispatch attaches technical-spec.md",
         "technical-spec.md" in b5)
c.expect("pattern", "D1: attachment is stated as receiving the claim, not inferring it",
         "inference of intent" in b5)
