"""L1 · one stage map                                        (preventive)
The loop diagram is ONE file, images/loop-stage-map.svg, inlined by the
Pages site (and the learner page when it lands) between SVG markers — a
second copy of the loop's shape is the B3 defect class. Red-proofed by
editing one character of the inlined copy.
"""

import re

from lib.lintkit import c, read

META = {
    "id": 'L1',
    "title": 'one stage map',
    "tier": 'lint (preventive)',
    "ledger": None,
}

_svg = read("images/loop-stage-map.svg").strip("\n")
for _page in ("docs/index.html", "docs/onboarding.html"):
    _m = re.search(r"<!-- SVG:images/loop-stage-map\.svg -->\n(.*?)\n<!-- /SVG -->",
                   read(_page), re.S)
    c.expect("images/loop-stage-map.svg is the one loop diagram",
             "L1: %s inlines images/loop-stage-map.svg byte-for-byte" % _page,
             _m is not None and _m.group(1) == _svg)
