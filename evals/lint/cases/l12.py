"""L12 · every page's script parses                               (#215)
docs/index.html:409 carried one unescaped apostrophe inside a single-quoted
string (`patrol's`); the whole <script> block failed to parse and every
interactive feature on the live page — language toggle, track tabs, stage
map, label cards, simulator, wizard — was dead from 2026-10-21 (#174) to
#215. No check read the pages' JavaScript: L1 holds the inlined SVG, the
other docs lints anchor prose. This case extracts every <script> block of
every `.html` under docs/ and runs `node --check` on it; a block that does
not parse fails with node's first error line. `node` is required (the
gate's other steps need it too — `claude plugin test`); when it is absent
the case FAILS rather than skips, so the dependency is explicit.
Red-proofed by the defect itself (index.html before the fix) and by a
stray quote planted in onboarding.html.
"""

import os
import re
import shutil
import subprocess
import tempfile

from lib.lintkit import R, c

META = {
    "id": "L12",
    "title": "every page's script parses",
    "tier": "lint (#215)",
    "ledger": "each `<script>` block of every `docs/**/*.html` passes `node --check`; one "
              "unescaped apostrophe had silenced the whole live page for two weeks.",
}

_SCRIPT = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.S | re.I)
_node = shutil.which("node")
c.expect("pattern", "L12: `node` is on PATH (the gate needs it; a missing node is a failure, "
         "not a skip)", _node is not None)

_pages = []
for _base, _, _names in os.walk(os.path.join(R, "docs")):
    for _n in sorted(_names):
        if _n.endswith(".html"):
            _pages.append(os.path.relpath(os.path.join(_base, _n), R))

for _page in sorted(_pages):
    with open(os.path.join(R, _page), encoding="utf-8") as _f:
        _html = _f.read()
    _blocks = [m for m in _SCRIPT.finditer(_html)
               if "src=" not in (m.group(0).split(">", 1)[0])]
    for _i, _m in enumerate(_blocks, 1):
        _line = _html[:_m.start(1)].count("\n") + 1
        _ok, _why = False, "node missing"
        if _node:
            _tmp = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
            try:
                _tmp.write(_m.group(1))
                _tmp.close()
                _p = subprocess.run([_node, "--check", _tmp.name], capture_output=True, text=True)
                _ok = _p.returncode == 0
                _err = [ln for ln in _p.stderr.splitlines() if ln.strip()]
                _msg = next((ln for ln in _err if "Error" in ln), _err[0] if _err else "")
                _loc = next((ln for ln in _err if _tmp.name in ln), "")
                _rel = re.search(r":(\d+)\s*$", _loc)
                _at = ""
                if _rel:
                    _at = " (block line %s → %s:%d)" % (_rel.group(1), _page,
                                                        _line + int(_rel.group(1)) - 1)
                _why = (_msg + _at).strip()
            finally:
                os.unlink(_tmp.name)
        c.expect("pattern", "L12: %s <script> block %d (from line %d) parses — %s"
                 % (_page, _i, _line, "node --check" if _ok else _why), _ok)
