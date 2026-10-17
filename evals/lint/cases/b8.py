"""B8 · QA's level is pinned                                         (#140 ruling 6, 2.0.0)
Two adopters showed the two failure shapes: a Java-level port in a unit-test
file (#125) and a QA suite seeding a schema it was blind to (#78). The level
is now one rule on every surface QA reads: through the port only — the API
itself for an HTTP feature, the documented (possibly process-level) port
otherwise — in `<acceptance_dir>` under the project's `acceptance_layout`,
no unit tests, no implementation imports beyond the port's declared types,
Given-state through the port's control points. Conformance-only: the subject
is the prose.
"""

from lib.lintkit import src

META = {
    "id": 'B8',
    "title": "QA's level is pinned — through the port only, in `<acceptance_dir>`, no unit tests, "
             "no implementation imports beyond the port's declared types; the port is the API for "
             "an HTTP feature and never \"always HTTP\"",
    "tier": 'lint (#140, 2.0.0)',
    "ledger": None,
}

src("B8: the QA brief — the port is the only road", "references/qa-brief.md",
    "**The port is the only road.**")
src("B8: the QA brief — HTTP → the API itself", "references/qa-brief.md",
    "For an HTTP feature the port is the API\n  itself")
src("B8: the QA brief — process-level ports exist", "references/qa-brief.md",
    "which may be process-level")
src("B8: the QA brief — no unit test, no implementation import", "references/qa-brief.md",
    "Never a unit test,\n  never an import of an implementation class beyond the port's "
    "declared\n  types")
src("B8: the QA brief — Given-state through the port", "references/qa-brief.md",
    "Given-state goes through the port's\n  control points")
src("B8: the QA brief — the layout", "references/qa-brief.md",
    "`<acceptance_dir>/<feature>/`\n  (`<feature>` = the project's layout unit — config "
    "`acceptance_layout`")
src("B8: the QA brief — expected values come from the requirement", "references/qa-brief.md",
    "**Derive the expected value from the requirement, never from a run of the\n  code.**")
src("B8: workflow pins the level", "references/workflow.md", "**QA's level is\n  pinned**")
src("B8: workflow — never 'always HTTP'", "references/workflow.md",
    "\"the port is the API\" never\n  becomes \"the port is always HTTP\"")
src("B8: workflow — Given-state is part of the port", "references/workflow.md",
    "**Given-state is part of the port**")
src("B8: README's note — never 'always HTTP'", "README.md",
    "never becomes \"the port is always HTTP\"")
src("B8: README's note — QA never touches the persistence layer", "README.md",
    "QA never touches the persistence layer")
src("B8: the qa persona — never an edited assertion", "agents/qa.md",
    "an assertion is never edited to match what you observed")
src("B8: the implementer template — Given-state is part of the port", "templates/implementer.md",
    "Given-state is part of the port")
src("B8: the implementer template — the control points are the implementer's",
    "templates/implementer.md", "a seed/setup\n  control point in §5 that you implement")
