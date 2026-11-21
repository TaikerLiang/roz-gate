"""L24 · bot mode documents only the non-printing credential path     (#413)
The documented bot-mode forms put the credential in front of the agent:
`scripts/gh-app-token.sh` printed the installation token, `GH_TOKEN=<token>
gh …` / `GITLAB_TOKEN=<token> glab …` and `git push https://x-access-token:
<token>@…` put it in the command text every hook and the transcript keep.
`bin/roz-forge` obtains the credential and sets it in one child's
environment. This case holds the documentation to that one path — the
recommended commands only:
- both forge adapters' § Identity name `bin/roz-forge` for the forge call
  and for the push;
- `references/identity-github-app.md` and `README.md` § Agent identity name
  it, and the config examples carry `bot_app_id`;
- none of the four carries a credential-in-text form: `GH_TOKEN=<…`,
  `GITLAB_TOKEN=<…`, `x-access-token:<…`, a `:<token>@` URL, or the retired
  helper's name. A warning naming a variable without a value is no hit.
What green does not prove: that an agent uses the tool at runtime — no
replay case runs in bot mode.
Red-proofed by restoring `GH_TOKEN=<token> gh …` in forge-github's Identity
and by dropping `roz-forge` from forge-gitlab's Identity.
"""

import os
import re

from lib.lintkit import R, c, read

META = {
    "id": "L24",
    "title": "bot mode documents only the non-printing credential path",
    "tier": "lint (#413)",
    "ledger": "`references/forge-github.md` and `references/forge-gitlab.md` § Identity name "
              "`bin/roz-forge` for bot-mode forge calls and for `git push`; "
              "`references/identity-github-app.md` and `README.md` § Agent identity name it and "
              "carry `bot_app_id`; none of the four carries `GH_TOKEN=<…`, `GITLAB_TOKEN=<…`, "
              "`x-access-token:<…`, a `:<token>@` URL or `gh-app-token`, and "
              "`scripts/gh-app-token.sh` is gone (#413: the documented forms put the bot "
              "credential in command text, tool output and the transcript).",
}

LEAK = re.compile(r"GH_TOKEN=<|GITLAB_TOKEN=<|x-access-token:<|:<token>@|gh-app-token")


def section(rel, heading):
    text = read(rel)
    m = re.search(r"^## %s\n(.*?)(?=^## |\Z)" % re.escape(heading), text, re.S | re.M)
    return " ".join(m.group(1).split()) if m else ""


SURFACES = {
    "references/forge-github.md § Identity": section("references/forge-github.md", "Identity"),
    "references/forge-gitlab.md § Identity": section("references/forge-gitlab.md", "Identity"),
    "references/identity-github-app.md":
        " ".join(read("references/identity-github-app.md").split()),
    "README.md § Agent identity": section("README.md", "Agent identity"),
}

for _name, _text in SURFACES.items():
    c.expect("pattern", "L24: %s names bin/roz-forge" % _name, "roz-forge" in _text)
    _hits = sorted(set(LEAK.findall(_text)))
    c.expect("pattern", "L24: %s carries no credential-in-text form (%s)"
             % (_name, ", ".join(_hits) or "none"), not _hits)

for _name in ("references/forge-github.md § Identity", "references/forge-gitlab.md § Identity"):
    c.expect("pattern", "L24: %s pushes through roz-forge" % _name,
             "bin/roz-forge git push [-u] origin <branch>" in SURFACES[_name])

for _name in ("references/identity-github-app.md", "README.md § Agent identity"):
    c.expect("pattern", "L24: %s carries bot_app_id" % _name, "bot_app_id:" in SURFACES[_name])

c.expect("pattern", "L24: the printing helper scripts/gh-app-token.sh is gone",
         not os.path.exists(os.path.join(R, "scripts", "gh-app-token.sh")))
