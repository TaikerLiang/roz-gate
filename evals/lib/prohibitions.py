"""The prohibition audit's one reader (#380).

`docs/prohibitions.json` records, for every prohibition the runtime prose
states, who enforces it. Lint L23 holds the data to the prose; `tools/
ledger.py` renders `docs/prose-inventory.md` § Prohibitions from it. Both
import this module — the word list and the 1 : 1 rule have one definition.

A HIT is one occurrence of a prohibition word in a scoped file. A SOURCE is
`{file, quote}`: `quote` is a literal piece of that file (whitespace
collapsed) that occurs exactly once in it and holds exactly one hit. Every
hit lies inside exactly one quote. So one source is one occurrence of one
clause — a long quote cannot hide a second prohibition behind one row
(#262: one prohibition clause, one decision question, one rule).

That is the lexical half. A RULE is a semantic thing, and one prohibition
word may govern more than one: "never deletes or force-pushes a remote
branch" is one hit and two independently violable decisions. So the same
`(file, quote)` may be a source of several rows when every one of those
sources carries a `clause` — a literal piece of the quote naming the part
that row owns — and the clauses differ. A hit still resolves to exactly one
quote; a quote resolves to one row, or to a set of `(row, clause)` pairs.
The scanner's token model does not set the rules' granularity.
"""

import glob
import json
import os
import re

DATA = "docs/prohibitions.json"
# never · cannot · do not · must not · forbidden · may not, their
# contractions, and `only … may` within one sentence. Case-insensitive.
# `only … may` is anchored on its `only`: the hit is that word, when a `may`
# (not `may not`) follows within the sentence. The span between them is not
# consumed, so a prohibition inside it is a hit of its own and a quote over
# the whole sentence holds two.
WORD = re.compile(
    r"\b(?:never|cannot|can't|do not|don't|must not|mustn't|forbidden|may not)\b"
    r"|\bonly\b(?=[^.]{0,80}?\bmay\b(?! not\b))", re.I)
CLASSES = ("hooked", "deterministic-candidate", "guarded-by-case", "prose-only", "not-a-rule")
PROSE_REASON = re.compile(r"\A(semantic|persona|authority|unguarded — \S)")


def flat(text):
    return " ".join(text.split())


def load(root):
    with open(os.path.join(root, DATA), encoding="utf-8") as f:
        return json.load(f)


def scoped_files(root, scope):
    out = []
    for d in scope:
        out += glob.glob(os.path.join(root, d, "**", "*.md"), recursive=True)
    return sorted(os.path.relpath(p, root) for p in out)


def hits(text):
    """[(start, end, word)] in flattened text."""
    return [(m.start(), m.end(), m.group(0)) for m in WORD.finditer(text)]


def survey(root, data):
    """Hold the data to the prose. Returns a dict of problem lists (each
    empty when clean) and the counts the renderer prints."""
    scope = data.get("scope", [])
    files = scoped_files(root, scope)
    texts = {}
    for rel in files:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            texts[rel] = flat(f.read())
    spans = {rel: [] for rel in files}   # rel -> [(a, b, row id)]
    bad = {k: [] for k in ("out_of_scope", "absent", "repeated", "no_hit", "many_hits",
                           "twice", "unclassified", "overlap", "clause")}
    seen = {}      # (rel, quote) -> [(row id, clause or None)]
    for row in data.get("rows", []):
        for s in row.get("sources", []):
            rel, quote = s.get("file", ""), flat(s.get("quote", ""))
            tag = "%s %s: %r" % (row.get("id"), rel, quote[:60])
            if rel not in texts:
                bad["out_of_scope"].append(tag)
                continue
            clause = s.get("clause")
            if clause is not None and not (clause.strip() and flat(clause) in quote):
                bad["clause"].append("%s: clause %r is not a piece of the quote" % (tag, clause))
            if (rel, quote) in seen:
                seen[(rel, quote)].append((row.get("id"), clause))
                continue
            seen[(rel, quote)] = [(row.get("id"), clause)]
            n = texts[rel].count(quote) if quote else 0
            if n == 0:
                bad["absent"].append(tag)
                continue
            if n > 1:
                bad["repeated"].append("%s ×%d" % (tag, n))
                continue
            a = texts[rel].index(quote)
            b = a + len(quote)
            inside = [h for h in hits(texts[rel]) if a <= h[0] and h[1] <= b]
            if not inside:
                bad["no_hit"].append(tag)
            elif len(inside) > 1:
                bad["many_hits"].append("%s holds %s" % (tag, [h[2] for h in inside]))
            spans[rel].append((a, b, row.get("id")))
    for (rel, quote), users in seen.items():
        tag = "%s %s: %r" % ("+".join(str(u[0]) for u in users), rel, quote[:60])
        clauses = [u[1] for u in users]
        if len(users) == 1:
            if clauses[0] is not None:
                bad["clause"].append("%s: a clause on a quote only one row uses" % tag)
        elif len({u[0] for u in users}) < len(users):
            bad["twice"].append("%s: one row registers the quote twice" % tag)
        elif None in clauses:
            bad["twice"].append("%s: a shared quote needs a clause on every source" % tag)
        elif len({flat(x) for x in clauses}) < len(clauses):
            bad["clause"].append("%s: two rows claim the same clause %s" % (tag, clauses))
    total = 0
    for rel in files:
        for a, b, word in hits(texts[rel]):
            total += 1
            owners = [rid for x, y, rid in spans[rel] if x <= a and b <= y]
            where = "%s: …%s…" % (rel, texts[rel][max(0, a - 40):b + 40])
            if not owners:
                bad["unclassified"].append(where)
            elif len(owners) > 1:
                bad["overlap"].append("%s in %s" % (where, owners))
    return {"bad": bad, "hits": total, "files": files}
