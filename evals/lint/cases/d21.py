"""D21 · a step that lists what a dispatch carries names the seat's R&R row   (#294)
Every command's preamble says a dispatch attaches the seat's R&R row from
`references/workflow.md`. D3 (replay) scores it on patrol's intake dispatch
— and Haiku 5.5 went 0/3: it built the payload from the intake step's own
list, "(async mode, with `…/intake-brief.md`, the issue body, and all
comments)", which is complete as written and leaves the row out. A rule
stated once in a preamble does not survive a step that enumerates the
contents in full (the #99 lesson: anchor on the step, not the general
statement). This case holds the row inside each such enumeration — the
sites found by auditing every dispatch in `commands/` — never in the
preamble. The rule itself stays `workflow.md`'s; each site is a pointer.
"""

from lib.lintkit import c, read

META = {
    "id": "D21",
    "title": "A step that lists what a dispatch carries names the seat's R&R row",
    "tier": "lint (#294)",
    "ledger": "In `commands/patrol.md`, `to-issues.md` and `next-stage.md`, every step that "
              "enumerates a dispatch's contents — the intake dispatch, the relay loop, the "
              "code-review and fast-track reviewer dispatches, the QA and fidelity dispatches "
              "— names the seat's R&R row inside that enumeration (#294: D3 0/3 on Haiku; a "
              "complete-looking local list overrode the preamble).",
}


def flat(path):
    return " ".join(read(path).split())


# (file, what the step is, the enumeration as it must read — whitespace-flattened)
SITES = [
    ("commands/patrol.md", "the intake dispatch",
     "(async mode, with the seat's R&R row from `workflow.md`, "
     "`${CLAUDE_PLUGIN_ROOT}/references/intake-brief.md`, the issue body, and all comments)"),
    ("commands/patrol.md", "the code-review dispatch on a CR at (5)",
     "the CR's diff against its base, the seat's R&R row, `<specs_dir>/<n>/spec.md` and "
     "`technical-spec.md` attached"),
    ("commands/patrol.md", "the fidelity dispatch",
     "`${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md` as its contract and the seat's "
     "R&R row, in the `<qa-branch>` worktree"),
    ("commands/to-issues.md", "the relay loop's product dispatch",
     "in **live mode** with: the seat's R&R row, the intake brief, the raw idea, and the "
     "full Q&A so far"),
    ("references/next-stage-path-b.md", "B5, the code-review dispatch",
     "**attaching the seat's R&R row, `<specs_dir>/<n>/spec.md` and `technical-spec.md`**"),
    ("references/next-stage-path-b2.md", "B2.4, the QA dispatch",
     "`${CLAUDE_PLUGIN_ROOT}/references/qa-brief.md` as its contract, the seat's R&R row, "
     "the two lists and the `Test port:` line"),
    ("references/next-stage-path-b2.md", "B2.7, the fidelity dispatch",
     "`${CLAUDE_PLUGIN_ROOT}/references/fidelity-brief.md` as its contract and the seat's "
     "R&R row, in the `<qa-branch>` worktree"),
    ("references/next-stage-path-c.md", "the fast track's reviewer dispatch",
     "**attaching the seat's R&R row and the issue body**"),
]

_cache = {}
for _path, _what, _literal in SITES:
    _text = _cache.setdefault(_path, flat(_path))
    c.expect("pattern", "D21: %s — %s names the R&R row in its own list" % (_path, _what),
             _literal in _text)
