"""B9 · the reserved-word registry is the single source          (#154, 2.2.0)
`references/reserved-words.json` lists the loop's reserved words, one entry
per word (its rule: `reserved-words.md` beside it). Every listed word has
its whole-word gate grep in Path B and promote, and appears in the four
English-as-code directories' Markdown only in code formatting. Before
#154 the one word, `unverified`, was restated at two command sites and
used bare twice in the runtime prose under a green suite
(`references/workflow.md`, the Path B heading); a second word would have
meant five hand edits and nothing to say which sites.
"""

import json
import os
import re

from lib.lintkit import R, c, dir_files, fixture, read

META = {
    "id": 'B9',
    "title":
        'the reserved-word registry is the single source — every word in '
        '`references/reserved-words.json` has a whole-word gate grep in Path B and promote, and '
        'appears in the Markdown of `agents commands references templates` only in code '
        'formatting; a bare use, a missing grep or an empty registry is red',
    "tier": 'lint (#154, 2.2.0)',
    "ledger": None,
}

REGISTRY = "references/reserved-words.json"
RUNTIME_DIRS = ("agents", "commands", "references", "templates")
GREP_SITES = ("commands/next-stage.md", "commands/spec-answers.md")
FENCE = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1[^\n]*$", re.M | re.S)
# CommonMark code span: a backtick run closes only at a run of the same length,
# and never across a blank line — a span is inline, it cannot leave its block.
CODE = re.compile(r"(?<!`)(`+)(?!`)((?:(?!\n[ \t]*\n).)+?)(?<!`)\1(?!`)", re.S)


def _blank(m):
    """Same length, newlines kept, so line numbers survive the masking."""
    return re.sub(r"[^\n]", " ", m.group(0))


def masked(text):
    return CODE.sub(_blank, FENCE.sub(_blank, text))


def bare_hits(word, text):
    """(line, text-of-line) for every whole-word, any-case hit outside code formatting."""
    m = masked(text)
    out = []
    for hit in re.finditer(r"(?i)\b%s\b" % re.escape(word), m):
        line = m.count("\n", 0, hit.start()) + 1
        out.append((line, text.splitlines()[line - 1].strip()))
    return out


entries = json.loads(read(REGISTRY)).get("words", [])
words = [e["word"] for e in entries if isinstance(e, dict) and e.get("word")]
c.expect("pattern", "B9 registry: at least one word is listed", len(words) >= 1)
c.expect("pattern", "B9 registry: every entry carries word, reserved_for, form, since, ruling",
         all({"word", "reserved_for", "form", "since", "ruling"} <= set(e) for e in entries))
c.expect("pattern", "B9 registry: `unverified` is a row", "unverified" in words)

# the masker itself, red-proofed on fixtures
c.expect("pattern", "B9 masker: three bare uses (prose, heading, bold) are three hits",
         len(bare_hits("unverified", fixture("b9_bare.md"))) == 3)
c.expect("pattern", "B9 masker: code span, fence, unverifiable, verified — zero hits",
         bare_hits("unverified", fixture("b9_code.md")) == [])
c.expect("pattern", "B9 masker: unmatched backticks in other paragraphs do not hide the word",
         len(bare_hits("unverified", fixture("b9_cross.md"))) == 1)

for word in words:
    for site in GREP_SITES:
        literal = "grep -nwi %s <specs_dir>/<n>/*.md" % word
        name = "B9 gate: %s carries the whole-word grep for `%s`" % (site, word)
        if literal in read(site):
            c.passed += 1
            c.ok(name)
        else:
            c.fails += 1
            c.fail(name, "%s lacks the literal: %s" % (site, literal))
    hits = []
    for path in dir_files(*RUNTIME_DIRS):
        if not path.endswith(".md"):
            continue  # the registry itself is data, not prose
        with open(path, encoding="utf-8") as f:
            text = f.read()
        rel = os.path.relpath(path, R)
        hits += ["%s:%d: %s" % (rel, ln, txt) for ln, txt in bare_hits(word, text)]
    name = "B9 prose: `%s` appears bare nowhere in %s" % (word, " ".join(RUNTIME_DIRS))
    if hits:
        c.fails += 1
        c.fail(name, "bare use of a reserved word — reword or code-format:\n  " + "\n  ".join(hits))
    else:
        c.passed += 1
        c.ok(name)
