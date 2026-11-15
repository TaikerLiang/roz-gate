"""D24 · a term used against its definition is a finding              (#197)
A seat that picks one meaning of a term ships the disagreement to
integration. `spec.md` may carry a must-read `## Glossary` (A3) — no longer
folded into the supplement — downstream seats use a term as defined, the
implementer builds to it, and QA's step zero reports a *term conflict*.
Replay D24 measures the run; this case holds the statements.
"""

import re

from lib.lintkit import c, read, src

META = {
    "id": "D24",
}

src("D24: A3 carries the Glossary rule", "references/next-stage-path-a.md",
    "**Glossary** (#197): `spec.md` may carry a must-read `## Glossary`")
src("D24: A3 — one line per term, in its shape", "references/next-stage-path-a.md",
    "`- <term> — <definition>`")
src("D24: A3 — a definition found wanting goes through the seat's own channel",
    "references/next-stage-path-a.md",
    "(the implementer's\n  question, QA's step-zero finding), never settled locally")
src("D24: the QA brief's step zero carries the term-conflict kind", "references/qa-brief.md",
    "a **term conflict**: a clause, a deviation or a scenario that uses a term\n"
    "  of `spec.md`'s `## Glossary` with another meaning")
src("D24: the implementer template builds to the Glossary", "templates/implementer.md",
    "Build to the terms of `spec.md`'s `## Glossary` as defined")

# the supplement list — "Everything else — … — is the **supplement**" — no
# longer names the glossary: a must-read section folded away is unread
_m = re.search(r"Everything\s+else — (.*?) — is the \*\*supplement\*\*",
               read("references/next-stage-path-a.md"), re.S)
c.expect("pattern", "D24: A3's supplement list exists", _m is not None)
c.expect("pattern", "D24: A3's supplement list does not fold the glossary away",
         _m is not None and not re.search(r"(?i)glossar", _m.group(1)))
