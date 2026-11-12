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
  - a case with no checker yet: `evals/ledger-deferred.json`;
  - a rule a hook alone enforces, proven in `hooks/tests/`:
    `evals/ledger-hook.json` — `rule` names the letter in `hooks/README.md`'s
    rule table (#189). Every letter in that table must appear in some row's
    tier as `rule X`, or the check fails: a hook rule cannot land unindexed.
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
HOOK = os.path.join(ROOT, "evals", "ledger-hook.json")
HOOKS_README = os.path.join(ROOT, "hooks", "README.md")
TEMPLATE = os.path.join(ROOT, "evals", "ledger-template.md")
LEDGER = os.path.join(ROOT, "evals", "LEDGER.md")
README = os.path.join(ROOT, "evals", "README.md")

CASE_FILE = re.compile(r"^([a-z])(\d+)\.py$")
ROWS_MARK = re.compile(r"^<!-- rows ((?:[A-Z] ?)+)-->$", re.M)
COUNTS = re.compile(r"<!-- counts -->\n(.*?)<!-- /counts -->", re.S)
BASELINES = os.path.join(ROOT, "evals", "replay", "baselines.json")
BASELINES_MARK = re.compile(r"<!-- baselines -->\n(.*?)<!-- /baselines -->", re.S)
HOOK_RULE_ROW = re.compile(r"^\| \*\*([A-Z])\*\* ", re.M)  # hooks/README.md's rule table
TIER_RULE = re.compile(r"\brule ([A-Z])\b")


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
    for meta in hook_cases():
        cid = meta["id"]
        if cid in out or cid in lint_ids:
            fail("%s: two sources — a hook row and a lint, replay or deferred row" % cid)
        if "rule %s" % meta["rule"] not in meta["tier"]:
            fail("%s: the hook row's tier must name `rule %s`" % (cid, meta["rule"]))
        out[cid] = {"title": meta["title"], "tier": meta["tier"], "ledger": meta["ledger"]}
    for cid in lint_ids - set(out):
        fail("%s: the lint META carries only an id and no replay or deferred row exists" % cid)
    check_hook_rules_indexed(out)
    return out


def hook_cases():
    return json.loads(read(HOOK))["cases"]


def check_hook_rules_indexed(table):
    """Every rule letter in hooks/README.md's table appears in some row's tier."""
    letters = set(HOOK_RULE_ROW.findall(read(HOOKS_README)))
    if not letters:
        fail("hooks/README.md has no `| **X** …` rule rows")
    indexed = set()
    for r in table.values():
        indexed.update(TIER_RULE.findall(r["tier"]))
    missing = sorted(letters - indexed)
    if missing:
        fail("hook rule %s in hooks/README.md has no ledger row naming it — add one to "
             "evals/ledger-hook.json or a case's tier" % ", ".join(missing))


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
    v1_items = os.path.join(JUDGMENT, "v1", "items")
    v1 = sum(1 for n in os.listdir(v1_items) if n.endswith(".json")) \
        if os.path.isdir(v1_items) else 0
    return {"lint": str(lint), "replay": str(replay), "hook": str(len(hook_cases())),
            "judgment": "%d items / %d fixtures · V1: %d decisions" % (items, fixtures, v1)}


def wilson90(passed, valid):
    """The runner's own interval (evals/replay/run_replay.py) — imported,
    so the page and a run's report can never disagree on the formula."""
    import importlib.util
    path = os.path.join(ROOT, "evals", "replay", "run_replay.py")
    sys.path[:0] = [os.path.dirname(path), os.path.join(ROOT, "evals")]
    spec = importlib.util.spec_from_file_location("run_replay", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.wilson90(passed, valid)


def when(b):
    return b["date"] or "sweep %s" % b["date_range"]


def render_baselines():
    """evals/README.md's <!-- baselines --> block, from baselines.json (#280).
    Recorded history, listed as recorded: the headline counts cases with at
    least one batch and picks no winner among batches; a result with counts
    gets the runner's Wilson interval, one the record only described is
    printed in the record's words."""
    data = json.loads(read(BASELINES))
    cases = sorted((d for d in os.listdir(REPLAY_CASES)
                    if os.path.exists(os.path.join(REPLAY_CASES, d, "case.json"))),
                   key=lambda c: (c[0], int(c[1:])))
    measured = {r["case"] for b in data["replay"] for r in b["results"]}
    unknown = sorted(measured - set(cases))
    if unknown:
        fail("baselines.json names %s, not a replay case" % ", ".join(unknown))
    none = [c for c in cases if c not in measured]
    out = ["**%d of %d replay cases have at least one recorded SUT baseline; %d have none.** "
           "*Recorded* is not *current*: a batch below is a measurement of the case as it "
           "was then, and a later seed or checker change may have superseded it — where the "
           "record says so, the row does."
           % (len(cases) - len(none), len(cases), len(none)), "",
           "| batch | SUT | plugin | when | k | results | source |",
           "|---|---|---|---|---|---|---|"]
    for b in data["replay"]:
        for key in ("id", "sut", "k", "source", "results"):
            if not b.get(key):
                fail("baselines.json: batch %s has no %s" % (b.get("id", "?"), key))
        groups = {}
        for r in b["results"]:
            if r.get("reported"):
                key = "reported — %s" % r["reported"]
            else:
                lo, hi = wilson90(r["passed"], r["valid"])
                key = "%d/%d [%.0f%%, %.0f%%]" % (r["passed"], r["valid"], 100 * lo, 100 * hi)
            groups.setdefault(key, []).append(r["case"])
        cells = ["%s: %s" % (k, ", ".join(v)) for k, v in groups.items()]
        sup = [("%s — %s" % (r["case"], r["superseded"])) for r in b["results"]
               if r.get("superseded")]
        if b.get("superseded"):
            sup.insert(0, "the batch — " + b["superseded"])
        if sup:
            cells.append("*superseded:* " + "; ".join(sup))
        out.append("| `%s` | %s | %s | %s | %d | %s | %s |"
                   % (b["id"], b["sut"], b["plugin"] or b["plugin_range"], when(b), b["k"],
                      " · ".join(cells).replace("|", "\\|"), b["source"].replace("|", "\\|")))
    out += ["", "Wilson 90%% intervals, the runner's formula. No recorded baseline (%d): %s."
            % (len(none), ", ".join(none)), ""]
    j = data["judgment"]
    out.append("**Judgment:** the last recorded sweep is %s SUT, %s judge, plugin %s, %s, "
               "k=%d — %s. Judgment V1 and the Workflow Value pilot have no recorded run."
               % (j["sut"], j["judge"], j["plugin"] or j.get("plugin_range"), when(j), j["k"],
                  j["note"]))
    return "\n".join(out) + "\n"


def render_readme():
    text = read(README)
    b = BASELINES_MARK.search(text)
    if not b:
        fail("evals/README.md has no <!-- baselines --> block")
    text = text[:b.start(1)] + render_baselines() + text[b.end(1):]
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
    print("LEDGER.md: lint %s · replay %s · hook %s · judgment %s"
          % (c["lint"], c["replay"], c["hook"], c["judgment"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
