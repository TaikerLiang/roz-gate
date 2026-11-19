"""L23 · every runtime prohibition is classified                        (#380)
"Only a human may apply a gate label. In a prompt, the agent decides whether
to obey. With a hook, the call is blocked every time." Rule B lives by that
sentence; most of the prose's prohibitions had no such backing and nothing
recorded which did. About 510 `never` / `cannot` / `must not` … sat in the
runtime prose, and the cheapest edit was to write one more.

`docs/prohibitions.json` now records, per distinct rule, its class
(`hooked`, `deterministic-candidate`, `guarded-by-case`, `prose-only`,
`not-a-rule`),
its owner, and the evidence for the class. This case holds the data to the
prose, in the directories the data scopes (it grows PR by PR: `agents/` and
`templates/` first, then `commands/`, then `references/`):

- every prohibition word lies inside exactly one registered quote;
- a quote occurs exactly once in its file and holds exactly one prohibition
  word — one source is one occurrence of one clause, so a long quote cannot
  classify two independent prohibitions (#262), and a `not-a-rule` group is
  a shared reason over explicit fragments, never a pattern;
- `owner` and `evidence` are separate and each resolves: a `hooked` row
  names a rule `hooks/README.md` lists and hook-test cases that exist; a
  `guarded-by-case` row ids the ledger lists; a `deterministic-candidate`
  row its follow-up issue (where the owner is chosen — a hook is one of
  five possible answers, and the last tried); `prose-only` and `not-a-rule` rows a reason.

What it does not do: judge whether a classification is right, or whether
the evidence is enough (that is review); find a prohibition spelled with
none of these words ("no force-push").

Red-proofed by appending an unclassified `never` sentence to an agent file;
editing a registered clause in the prose (stale quote); widening a quote
over a second `never`; a quote that matches twice; two rows quoting
overlapping text; `hook Z`; a hook-test case that does not exist; a ledger
id that does not exist; a `deterministic-candidate` with no issue; a `prose-only`
row with no reason; a new file with a `never` under a scoped directory.
"""

import os
import re

from lib import prohibitions as P
from lib.lintkit import R, c, read

META = {
    "id": "L23",
    "title": "every runtime prohibition is classified",
    "tier": "lint (#380)",
    "ledger": "Every prohibition word (`never`, `cannot`, `do not`, `must not`, `forbidden`, "
              "`may not`, `only … may`, and their contractions) in the `*.md` files of the "
              "directories `docs/prohibitions.json` scopes lies inside exactly one quote a row "
              "registers for that file; every quote occurs exactly once in its file and holds "
              "exactly one prohibition word; a `hooked` row names a rule `hooks/README.md` "
              "lists and hook-test cases that exist, a `guarded-by-case` row ids the ledger "
              "lists, a `deterministic-candidate` row its owner-selection issue, a "
              "`prose-only` or `not-a-rule` row a "
              "reason — `owner` and `evidence` are separate fields (#380: about 510 "
              "prohibitions, and for most nothing recorded who enforces them).",
}

SRC = "docs/prohibitions.json"
DATA = P.load(R)
S = P.survey(R, DATA)
BAD = S["bad"]


def show(items, n=4):
    return "; ".join(items[:n]) + (" … +%d" % (len(items) - n) if len(items) > n else "")


c.expect(SRC, "L23: the data scopes at least one runtime directory, and only runtime "
         "directories (%s)" % DATA.get("scope"),
         bool(DATA.get("scope")) and set(DATA["scope"]) <= {
             "agents", "commands", "references", "templates"})
c.expect(SRC, "L23: every prohibition word in %d scoped files (%d hits) lies inside a "
         "registered quote%s" % (len(S["files"]), S["hits"],
                                 " — unclassified: " + show(BAD["unclassified"])
                                 if BAD["unclassified"] else ""),
         not BAD["unclassified"] and S["hits"] > 0)
c.expect(SRC, "L23: no prohibition word lies inside two quotes%s"
         % (" — " + show(BAD["overlap"]) if BAD["overlap"] else ""), not BAD["overlap"])
c.expect(SRC, "L23: every quote is in its file%s"
         % (" — stale: " + show(BAD["absent"]) if BAD["absent"] else ""), not BAD["absent"])
c.expect(SRC, "L23: every quote occurs exactly once in its file%s"
         % (" — " + show(BAD["repeated"]) if BAD["repeated"] else ""), not BAD["repeated"])
c.expect(SRC, "L23: every quote holds exactly one prohibition word%s"
         % (" — " + show(BAD["no_hit"] + BAD["many_hits"])
            if BAD["no_hit"] or BAD["many_hits"] else ""),
         not BAD["no_hit"] and not BAD["many_hits"])
c.expect(SRC, "L23: no quote is registered twice, and every source is a scoped file%s"
         % (" — " + show(BAD["twice"] + BAD["out_of_scope"])
            if BAD["twice"] or BAD["out_of_scope"] else ""),
         not BAD["twice"] and not BAD["out_of_scope"])

HOOKS = set(re.findall(r"^\| \*\*([A-Z])\*\* ", read("hooks/README.md"), re.M))
LEDGER = set(re.findall(r"^\| ([A-Z]\d+) \|", read("evals/LEDGER.md"), re.M))
shape, owner, evidence, reason = [], [], [], []
ids = [r.get("id") for r in DATA.get("rows", [])]
for row in DATA.get("rows", []):
    rid, cls = row.get("id"), row.get("class")
    ev = row.get("evidence", [])
    if not (re.fullmatch(r"P\d{3}", rid or "") and cls in P.CLASSES
            and (row.get("rule") or "").strip() and row.get("sources")
            and isinstance(ev, list)):
        shape.append(str(rid))
        continue
    if cls == "hooked":
        m = re.fullmatch(r"hook ([A-Z])", row.get("owner") or "")
        if not (m and m.group(1) in HOOKS):
            owner.append("%s: %r" % (rid, row.get("owner")))
        for e in ev:
            path, _, name = e.partition("::")
            if not (name and os.path.isfile(os.path.join(R, path)) and name in read(path)):
                evidence.append("%s: %s" % (rid, e))
        if not ev:
            evidence.append("%s: none" % rid)
    elif cls == "guarded-by-case":
        if not (row.get("owner") or "").strip():
            owner.append("%s: no owner" % rid)
        if not ev or any(e not in LEDGER for e in ev):
            evidence.append("%s: %s" % (rid, ev))
    elif cls == "deterministic-candidate":
        if row.get("owner") != "none yet":
            owner.append("%s: %r" % (rid, row.get("owner")))
        if not ev or any(not re.fullmatch(r"#\d+", e) for e in ev):
            evidence.append("%s: %s" % (rid, ev))
    else:
        want = "prose" if cls == "prose-only" else "—"
        if row.get("owner") != want:
            owner.append("%s: %r" % (rid, row.get("owner")))
        if ev:
            evidence.append("%s: %s" % (rid, ev))
        why = row.get("reason") or ""
        if not (P.PROSE_REASON.match(why) if cls == "prose-only" else why.strip()):
            reason.append("%s: %r" % (rid, why))
    if cls not in ("prose-only", "not-a-rule") and row.get("reason"):
        reason.append("%s: a reason on a %s row" % (rid, cls))
c.expect(SRC, "L23: every row has an id `P<nnn>` used once, a class, a rule and sources%s"
         % (" — " + show(shape) if shape else ""),
         not shape and len(ids) == len(set(ids)))
c.expect(SRC, "L23: every owner fits its class — `hook <rule>` that hooks/README.md lists, "
         "`none yet` for a candidate, `prose`, `—`%s" % (" — " + show(owner) if owner else ""),
         not owner)
c.expect(SRC, "L23: every evidence pointer resolves — hook-test cases, ledger ids, an issue "
         "— and is present exactly where the class needs one%s"
         % (" — " + show(evidence) if evidence else ""), not evidence)
c.expect(SRC, "L23: every `prose-only` row says why (semantic, persona, authority, or "
         "`unguarded — <what would guard it>`) and every `not-a-rule` row its reason%s"
         % (" — " + show(reason) if reason else ""), not reason)
