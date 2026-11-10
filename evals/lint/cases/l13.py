"""L13 · the executable-prose inventory stays honest                (#260)
`docs/prose-inventory.md` classifies every ledger- or hook-guarded rule of
the loop's prose by owner — observation, mechanical policy, semantic
judgment, authority — and tracks each mechanical row through a fixed
lifecycle. A catalogue nobody checks drifts the first time the prose is
rewritten, so this case holds it to its own rules:
- every ledger ID appears in a table, and every ID in a table is a ledger ID;
- every hook rule A–K owns at least one row;
- every anchor is still a literal of its source (unless the row is
  `migrated <sha>`);
- classes, owners and statuses come from the fixed vocabularies;
- a `ready` / `shadow` / `authoritative` / `migrated` row has every
  readiness field filled (`on_unknown` required for observations), a
  `not_ready` row has at least one `—` — that field is its blocker — and a
  `shadow` row names a signal;
- every unguarded section it lists still exists.
"""

import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "L13",
    "title": "the executable-prose inventory stays honest",
    "tier": "lint (#260)",
    "ledger": "every ledger ID is in `docs/prose-inventory.md`, every hook rule A–K owns a row, "
              "every anchor is still a literal of its source, and every status agrees with its "
              "readiness fields — `not_ready` names its blocker by leaving it `—`.",
}

PAGE = "docs/prose-inventory.md"
OBS, POL, SEM, AUTH = "OBSERVATION", "MECHANICAL POLICY", "SEMANTIC JUDGMENT", "AUTHORITY"
STATUS = re.compile(r"\A(identified|not_ready|ready|shadow|authoritative"
                    r"|migrated [0-9a-f]{7,40})\Z")
OWNER = re.compile(r"\A(roz-branch|roz-state|roz-check|hook [A-Za-z][\w-]*|code \S+"
                   r"|none yet — .+)\Z")
EMPTY = ("—", "", "-")


def flat(s):
    return " ".join(s.split())


def rows(text, heading):
    """The data rows of the first table under `## heading`, as cell lists."""
    m = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(heading), text, re.M | re.S)
    if not m:
        return None
    out = []
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line.startswith("|") or re.match(r"^\|[-\s|]+\|$", line):
            continue
        cells = [x.strip().replace("\\|", "|") for x in re.split(r"(?<!\\)\|", line)[1:-1]]
        out.append(cells)
    return out[1:]                                  # drop the header row


def ids(cell):
    """'C22 (obs)' → {C22}; 'D9–D19, E12' → {D9 … D19, E12}; '—' → {}."""
    out = set()
    for part in cell.split(","):
        part = re.sub(r"\(.*?\)", "", part).strip()
        m = re.fullmatch(r"([A-Z])(\d+)\s*[–-]\s*\1?(\d+)", part)
        if m:
            lo, hi = int(m.group(2)), int(m.group(3))
            out.update("%s%d" % (m.group(1), k) for k in range(lo, hi + 1))
        elif re.fullmatch(r"[A-Z]\d+", part):
            out.add(part)
    return out


_page = os.path.exists(os.path.join(R, PAGE))
c.expect("pattern", "L13: %s exists" % PAGE, _page)
_text = read(PAGE) if _page else ""
_ledger = set(re.findall(r"^\| ([A-Z]\d+) \|", read("evals/LEDGER.md"), re.M))
_hooks = set(re.findall(r"^\| \*\*([A-Z])\*\* ", read("hooks/README.md"), re.M))

_mech = rows(_text, "Mechanical rules") or []
_kept = rows(_text, "Kept in prose") or []
_fcases = rows(_text, "End-to-end cases") or []
_excl = rows(_text, "Not classified") or []
c.expect("pattern", "L13: the four tables are present and non-empty",
         all((_mech, _kept, _fcases, _excl)))

_seen = set()
for r in _mech + _kept + _excl:
    _seen |= ids(r[0])
for r in _fcases:
    _seen |= ids(r[0])
c.expect("pattern", "L13: every ledger ID appears in the inventory (missing: %s)"
         % (", ".join(sorted(_ledger - _seen)) or "none"), _ledger <= _seen)
c.expect("pattern", "L13: every ID in the inventory is a ledger ID (unknown: %s)"
         % (", ".join(sorted(_seen - _ledger)) or "none"), _seen <= _ledger)

_owned = {m.group(1) for r in _mech if len(r) == 12
          for m in [re.match(r"hook ([A-Z])\Z", r[5])] if m}
c.expect("pattern", "L13: every hook rule A–K owns a row (missing: %s)"
         % (", ".join(sorted(_hooks - _owned)) or "none"), _hooks and _hooks <= _owned)


def anchor_ok(src, anchor):
    path = os.path.join(R, src)
    return os.path.exists(path) and flat(anchor) in flat(read(src))


for r in _mech:
    if len(r) != 12:
        c.expect("pattern", "L13: mechanical row %r has 12 cells" % r[:1], False)
        continue
    rid, src, anc, _q, cls, owner, _dep, inputs, unk, oracle, shadow, status = r
    tag = "L13: mechanical row %s" % rid
    c.expect("pattern", "%s — class is OBSERVATION or MECHANICAL POLICY" % tag, cls in (OBS, POL))
    c.expect("pattern", "%s — owner from the vocabulary (%s)" % (tag, owner[:40]),
             OWNER.match(owner) is not None)
    c.expect("pattern", "%s — status from the six (%s)" % (tag, status),
             STATUS.match(status) is not None)
    if not status.startswith("migrated"):
        c.expect("pattern", "%s — its anchor is still a literal of %s" % (tag, src),
                 anchor_ok(src, anc))
    required = [inputs, oracle, shadow] + ([unk] if cls == OBS else [])
    filled = all(x not in EMPTY for x in required)
    if status in ("ready", "shadow", "authoritative") or status.startswith("migrated"):
        c.expect("pattern", "%s — %s needs every readiness field filled" % (tag, status), filled)
    if status == "not_ready":
        c.expect("pattern", "%s — not_ready leaves its blocker `—`" % tag, not filled)
    if status == "shadow":
        c.expect("pattern", "%s — a shadow row names its signal" % tag,
                 shadow not in EMPTY and not shadow.startswith("not required"))

for r in _kept:
    if len(r) != 6:
        c.expect("pattern", "L13: kept row %r has 6 cells" % r[:1], False)
        continue
    rid, src, anc, _q, cls, why = r
    c.expect("pattern", "L13: kept row %s — class is SEMANTIC JUDGMENT or AUTHORITY" % rid,
             cls in (SEM, AUTH))
    c.expect("pattern", "L13: kept row %s — its anchor is still a literal of %s" % (rid, src),
             anchor_ok(src, anc))
    c.expect("pattern", "L13: kept row %s — says why it needs a model or a human" % rid,
             why not in EMPTY)

for r in rows(_text, "Unguarded executable prose") or []:
    m = re.match(r"`([^`]+)`\s*§\s*(.+)", r[0])
    if not m:
        continue
    src, secs = m.group(1), [s.strip() for s in m.group(2).split(", §")]
    body = read(src) if os.path.exists(os.path.join(R, src)) else ""
    for s in secs:
        c.expect("pattern", "L13: unguarded section %s § %s still exists" % (src, s[:40]),
                 re.search(r"^#{2,3} %s\s*$" % re.escape(s), body, re.M) is not None)
