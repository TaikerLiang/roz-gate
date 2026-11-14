"""L21 · runtime prose stays within its caps                           (#278)
The agent-loaded prose grew from about 12,000 words at 1.16.3 to 49,772 at
2.16.0, and nothing pushed back: deleting a sentence means moving its
anchors, so the cheapest legal edit was to add one. Two caps, frozen at the
measured value with no headroom:
- the repo's runtime prose total — every `*.md` under `commands/`,
  `references/` and `agents/`, plus `templates/implementer.md` (a rule, not
  a list: a new reference file is counted without anyone registering it);
- each `commands/` file's word count — a slash command injects its file
  whole. Every command file has a cap and every cap names a command file.
A word is a whitespace-separated token (`len(text.split())`, what `wc -w`
prints). A cap is a ceiling: when it was set, one more word turned it red;
after a cut the room stays, and lowering a cap is the maintainer's, at
release. Raising one happens in the PR that needs it, with a release-note
line (`evals/CONTRIBUTING.md` § Prose caps). These constants are the one
source; `tools/ledger.py` renders them into `evals/README.md`.
"""

import os

from lib.lintkit import R, c

META = {
    "id": "L21",
    "title": "runtime prose stays within its caps",
    "tier": "lint (#278)",
    "ledger": "the repo's runtime prose total — every `*.md` under `commands/`, `references/`, "
              "`agents/`, plus `templates/implementer.md` — is at most `TOTAL_CAP` words, and "
              "each `commands/` file at most its own cap; every command file has a cap and "
              "every cap names a command file (#278: about 12,000 words at 1.16.3, 49,772 at "
              "2.16.0 — the cheapest legal edit was to add a sentence).",
}

SET_AT = "2ee634c"  # the main commit the caps were measured on (#279 merged)
TOTAL_CAP = 52040
COMMAND_CAPS = {
    "commands/config.md": 540,
    "commands/init.md": 1351,
    "commands/integrate.md": 2494,
    "commands/next-stage.md": 1076,
    "commands/patrol.md": 3917,
    "commands/review-answers.md": 1822,
    "commands/spec-answers.md": 3333,
    "commands/tip.md": 2586,
    "commands/to-issues.md": 504,
    "commands/uninit.md": 444,
}
DIRS = ("commands", "references", "agents")
EXTRA = ("templates/implementer.md",)


def counted():
    """Repo-relative paths of the runtime prose set, sorted."""
    out = [p for p in EXTRA if os.path.exists(os.path.join(R, p))]
    for d in DIRS:
        for base, _, names in os.walk(os.path.join(R, d)):
            out += [os.path.relpath(os.path.join(base, n), R) for n in names if n.endswith(".md")]
    return sorted(out)


def words(relpath):
    with open(os.path.join(R, relpath), encoding="utf-8") as f:
        return len(f.read().split())


_files = counted()
_words = {p: words(p) for p in _files}
_total = sum(_words.values())
_largest = ", ".join("%s %d" % (p, n) for p, n in
                     sorted(_words.items(), key=lambda kv: -kv[1])[:5])
c.expect("pattern", "L21: repo runtime prose total %d words <= cap %d (%d files; largest: %s)"
         % (_total, TOTAL_CAP, len(_files), _largest), _total <= TOTAL_CAP)

_commands = sorted(p for p in _files if p.startswith("commands/"))
c.expect("pattern", "L21: every command file has a cap (uncapped: %s)"
         % (", ".join(sorted(set(_commands) - set(COMMAND_CAPS))) or "none"),
         set(_commands) <= set(COMMAND_CAPS))
c.expect("pattern", "L21: every cap names a command file (unknown: %s)"
         % (", ".join(sorted(set(COMMAND_CAPS) - set(_commands))) or "none"),
         set(COMMAND_CAPS) <= set(_commands))
for _p in _commands:
    if _p in COMMAND_CAPS:
        c.expect("pattern", "L21: command file %s %d words <= cap %d"
                 % (_p, _words[_p], COMMAND_CAPS[_p]), _words[_p] <= COMMAND_CAPS[_p])
