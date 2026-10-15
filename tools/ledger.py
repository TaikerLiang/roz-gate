#!/usr/bin/env python3
"""Regenerate evals/LEDGER.md and the eval counts in evals/README.md from the cases.

    python3 tools/ledger.py            # rewrite both files
    python3 tools/ledger.py --check    # exit 1 if either is stale

The cases are canonical; the ledger page is a rendering of them (the way
CHANGELOG.md renders the releases). One row has one source:
  - a lint-only case: `META` in `evals/lint/cases/<id>.py` — `id`, `title`,
    `tier`, `ledger` (`None` renders as `—`); parsed with `ast`, never
    imported, because importing a case runs its checks;
  - a replay case: `evals/replay/cases/<ID>/case.json` — `ledger` (`<ID> ·
    <title>`), `tier`, `ledger_text`; a lint file for the same ID carries
    `META = {"id": …}` and nothing else;
  - a case with no checker yet: `evals/ledger-deferred.json`.
Rows render in ID order within a family. The prose around the tables is
`evals/ledger-template.md`; a `<!-- rows A -->` line is where family A's
rows go (`<!-- rows J L -->` renders two lint-only families, three
columns). Never edit LEDGER.md by hand — edit the case, rerun this.
Stdlib-only; dev tooling (`docs/releasing.md`, `evals/CONTRIBUTING.md`).
"""

import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINT_CASES = os.path.join(ROOT, "evals", "lint", "cases")
REPLAY_CASES = os.path.join(ROOT, "evals", "replay", "cases")
JUDGMENT = os.path.join(ROOT, "evals", "judgment")
DEFERRED = os.path.join(ROOT, "evals", "ledger-deferred.json")
TEMPLATE = os.path.join(ROOT, "evals", "ledger-template.md")
LEDGER = os.path.join(ROOT, "evals", "LEDGER.md")
README = os.path.join(ROOT, "evals", "README.md")

CASE_FILE = re.compile(r"^([a-z])(\d+)\.py$")
ROWS_MARK = re.compile(r"^<!-- rows ((?:[A-Z] ?)+)-->$", re.M)
COUNTS = re.compile(r"<!-- counts -->\n(.*?)<!-- /counts -->", re.S)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def fail(msg):
    sys.exit("ledger: " + msg)


def lint_meta(path):
    """The `META = {...}` literal of one case file, without importing it."""
    for node in ast.parse(read(path)).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "META" for t in node.targets):
            return ast.literal_eval(node.value)
    fail("%s has no META" % os.path.relpath(path, ROOT))


def rows():
    """{id: {"title", "tier", "ledger"}} — one source per row, checked."""
    out, lint_ids = {}, set()
    for name in sorted(os.listdir(LINT_CASES)):
        m = CASE_FILE.match(name)
        if not m:
            continue
        meta = lint_meta(os.path.join(LINT_CASES, name))
        cid = meta.get("id")
        if cid != m.group(1).upper() + m.group(2):
            fail("%s: META id %r does not match the file name" % (name, cid))
        lint_ids.add(cid)
        if "title" in meta:
            if sorted(meta) != ["id", "ledger", "tier", "title"]:
                fail("%s: META keys must be id, title, tier, ledger" % name)
            out[cid] = {"title": meta["title"], "tier": meta["tier"], "ledger": meta["ledger"]}
    for d in sorted(os.listdir(REPLAY_CASES)):
        cj = os.path.join(REPLAY_CASES, d, "case.json")
        if not os.path.exists(cj):
            continue
        meta = json.loads(read(cj))
        cid, _, title = meta.get("ledger", "").partition(" · ")
        if cid != d or not title:
            fail("%s/case.json: `ledger` must read `%s · <title>`" % (d, d))
        if "tier" not in meta or "ledger_text" not in meta:
            fail("%s/case.json: needs `tier` and `ledger_text`" % d)
        if cid in out:
            fail("%s: two sources — case.json and the lint META both carry a row" % cid)
        out[cid] = {"title": title, "tier": meta["tier"], "ledger": meta["ledger_text"]}
    for meta in json.loads(read(DEFERRED))["cases"]:
        cid = meta["id"]
        if cid in out or cid in lint_ids:
            fail("%s: deferred row for a case that has a checker" % cid)
        out[cid] = {"title": meta["title"], "tier": meta["tier"], "ledger": meta["ledger"]}
    for cid in lint_ids - set(out):
        fail("%s: the lint META carries only an id and no replay or deferred row exists" % cid)
    return out


def ordered(ids, family):
    return sorted((i for i in ids if i[0] == family), key=lambda i: int(i[1:]))


def render_ledger(table):
    def block(m):
        families = m.group(1).split()
        lines = []
        for fam in families:
            for cid in ordered(table, fam):
                r = table[cid]
                cells = [cid, r["title"], r["tier"]]
                if len(families) == 1:  # the four-column families
                    cells.append("—" if r["ledger"] is None else r["ledger"])
                lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
    text, n = ROWS_MARK.subn(block, read(TEMPLATE))
    if n == 0:
        fail("the template has no `<!-- rows … -->` line")
    rendered = set()
    for m in ROWS_MARK.finditer(read(TEMPLATE)):
        rendered.update(m.group(1).split())
    missing = sorted(set(i[0] for i in table) - rendered)
    if missing:
        fail("the template has no rows line for family %s" % ", ".join(missing))
    return text


def counts():
    lint = sum(1 for n in os.listdir(LINT_CASES) if CASE_FILE.match(n))
    replay = sum(1 for d in os.listdir(REPLAY_CASES)
                 if os.path.exists(os.path.join(REPLAY_CASES, d, "case.json")))
    items = sum(1 for k in json.loads(read(os.path.join(JUDGMENT, "criteria.json")))
                if not k.startswith("_"))
    fixtures = sum(1 for d in os.listdir(os.path.join(JUDGMENT, "cases"))
                   if os.path.isdir(os.path.join(JUDGMENT, "cases", d)))
    return {"lint": str(lint), "replay": str(replay),
            "judgment": "%d items / %d fixtures" % (items, fixtures)}


def render_readme():
    text = read(README)
    m = COUNTS.search(text)
    if not m:
        fail("evals/README.md has no <!-- counts --> block")
    table = m.group(1)
    for tier, n in counts().items():
        table, k = re.subn(r"^(\| \*\*%s\*\* \| )[^|]*(\|)" % tier, r"\g<1>%s \2" % n, table,
                           flags=re.M)
        if k != 1:
            fail("evals/README.md: no `| **%s** |` row inside the counts block" % tier)
    return text[:m.start(1)] + table + text[m.end(1):]


def main(argv):
    ledger, readme = render_ledger(rows()), render_readme()
    if "--check" in argv:
        stale = [p for p, t in ((LEDGER, ledger), (README, readme)) if read(p) != t]
        for p in (LEDGER, README):
            print("%s is %s" % (os.path.relpath(p, ROOT),
                                "stale — run tools/ledger.py" if p in stale else "current"))
        return 1 if stale else 0
    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write(ledger)
    with open(README, "w", encoding="utf-8") as f:
        f.write(readme)
    c = counts()
    print("LEDGER.md: lint %s · replay %s · judgment %s" % (c["lint"], c["replay"], c["judgment"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
