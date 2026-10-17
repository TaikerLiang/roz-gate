"""L7 · the wire spec and the client agree                      (preventive)
docs/protocol.md is protocol v1 — the page a foreign agent implements
against (#142) — and roz-gate is its reference client, so the page must say
what the client does: the labels it tables are exactly the state machine's
(both directions), the STOP title + resume line and the summary rule are
the client's own literals, no reference-client internal (a branch, a seat,
a command) is bound as a MUST, both pages open with the front matter Pages
renders and carry the stamp and their cross-link, and every entry point —
README's intro, the site's nav, the intake footer — links the pages.
Red-proofed by deleting a §1 row, adding a MUST on spec/<n>, and dropping
the front matter.
"""

import re

from lib.lintkit import c, must_match, must_not_match, read, section, src

META = {
    "id": 'L7',
    "title":
        'the wire spec names exactly the labels the state machine has, states the STOP and '
        "summary rules in the client's literals, binds no reference-client internal as a "
        'MUST, and every entry point links the pages',
    "tier": 'lint (preventive)',
    "ledger": None,
}

_wf = read("references/workflow.md")
_sm = section(_wf, r"^## Label state machine", r"^## The main agent")
_proto = read("docs/protocol.md")
_part = read("docs/participating.md")

# (a) the label set, both directions — derived from § Label state machine's backticked
# label words and from protocol §1's table rows, never from a list written here.
_words = set(re.findall(r"`([a-z]+(?:-[a-z]+)*)`", _sm)) | set(
    re.findall(r"`(?:status|track): ([a-z]+(?:-[a-z]+)*)`", _sm))
_wf_track = {w for w in _words if w in ("spec", "fast")}
_wf_status = _words - _wf_track
_tbl = section(_proto, r"^## 1\. Labels", r"^## 2\. ")
_p_track = set(re.findall(r"^\| `track: ([a-z]+(?:-[a-z]+)*)` \|", _tbl, re.M))
_p_status = set(re.findall(r"^\| `status: ([a-z]+(?:-[a-z]+)*)` \|", _tbl, re.M))
c.expect("docs/protocol.md",
         "L7: §1 tables every status label the state machine names, and no other",
         bool(_wf_status) and _p_status == _wf_status)
c.expect("docs/protocol.md", "L7: §1 tables both tracks and no other",
         _p_track == _wf_track == {"spec", "fast"})

# (b) the STOP comment: the title and the resume line are the client's literals
for _f in ("references/workflow.md", "docs/protocol.md", "docs/participating.md"):
    src("L7: %s carries the STOP title" % _f, _f, "`**[<command>] · blocked**`")
for _f, _t in (("references/workflow.md", _wf), ("docs/protocol.md", _proto)):
    must_match("L7: %s carries the resume line" % _f,
               r"\*\*To resume:\*\* clear `status: blocked`, apply\s+`status: <phase>`", _t)
src("L7: participating names the resume line", "docs/participating.md", "**To resume:**")

# (c) the summary rule, in the intake brief's words
for _f, _t in (("references/intake-brief.md", read("references/intake-brief.md")),
               ("docs/protocol.md", _proto)):
    must_match("L7: %s states the summary rule" % _f,
               r"first or last\s+non-empty line is exactly `summary`", _t)

# (d) no reference-client internal is bound as a MUST: the MUST lines plus the
# checklist that follows a line ending in "MUST:".
_lines = _proto.splitlines()
_must = [ln for ln in _lines if "MUST" in ln]
for _i, ln in enumerate(_lines):
    if ln.rstrip().endswith("MUST:"):
        _started = False
        for nxt in _lines[_i + 1:]:
            if not nxt.strip():
                if _started:
                    break
                continue
            _started = True
            _must.append(nxt)
c.expect("docs/protocol.md", "L7: the page has an interop checklist", len(_must) >= 7)
must_not_match("L7: no MUST binds a branch, a seat or a command of the reference client",
               r"spec/|feat/|qa/|fast/|roz-gate:|\b(?:product|em|implementer|qa|reviewer)\b",
               "\n".join(_must))

# (e) Pages renders both pages; each carries the stamp and links the other
for _f, _t in (("docs/protocol.md", _proto), ("docs/participating.md", _part)):
    c.expect(_f, "L7: %s opens with the front matter Pages renders" % _f,
             _t.startswith("---\ntitle: ") and _t.split("\n")[2] == "---")
    src("L7: %s carries the protocol v1 stamp" % _f, _f, "protocol v1")
    must_not_match("L7: %s carries no Liquid for Jekyll to eat" % _f, r"\{\{|\{%", _t)
src("L7: protocol links participating", "docs/protocol.md", "(participating.md)")
src("L7: participating links protocol", "docs/participating.md", "(protocol.md)")

# (f) every entry point links the pages
_PROTO = "https://taikerliang.github.io/roz-gate/protocol.html"
_PART = "https://taikerliang.github.io/roz-gate/participating.html"
src("L7: README's intro links protocol v1", "README.md", "[protocol v1](%s)" % _PROTO)
src("L7: README's intro links the participating guide", "README.md",
    "[the participating guide](%s)" % _PART)
src("L7: the site's nav links protocol", "docs/index.html", 'href="protocol.html"')
src("L7: the site's nav links participating", "docs/index.html", 'href="participating.html"')
src("L7: the intake summary footer links the participating guide",
    "references/intake-brief.md", _PART)
