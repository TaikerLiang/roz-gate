"""L17 · the replay instrument names no repository but the fixture's   (#250)
The forge stub printed `https://github.com/x/y/…` while every fixture's
sandbox is `acme/demo`: a URL a seat could not reconcile with the remote it
pushed to, and one a careful seat re-derived or dropped. The stub now builds
every URL from `state.json`'s `repo` (`web(st)`), and a `--json` field it
does not serve is UNKNOWN before anything prints (`json_want`). This case
holds the old literal out of the whole replay tier — stub, harness,
`replaylib`, every case — and the two helpers in the stub.
"""

import os

from lib.lintkit import R, c, read

META = {
    "id": "L17",
    "title": "the replay tier names no repository but the fixture's",
    "tier": "lint (#250)",
    "ledger": "No file under `evals/replay/` carries `github.com/x/y` or `repos/x/y`'s API "
              "host form; the forge stub builds URLs with `web(st)` from the fixture's `repo` "
              "and validates `--json` through `json_want` (#250: the stub's URLs named a "
              "repository the sandbox was not, and an unserved field printed a blank).",
}

OLD = ("github.com/" + "x/y", "api.github.com/repos/" + "x/y")
_hits = []
for _dir, _subs, _files in os.walk(os.path.join(R, "evals", "replay")):
    _subs[:] = [d for d in _subs if d != "__pycache__"]
    for _f in _files:
        _p = os.path.join(_dir, _f)
        try:
            with open(_p, encoding="utf-8") as _fh:
                _t = _fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if any(o in _t for o in OLD):
            _hits.append(os.path.relpath(_p, R))
c.expect("pattern", "L17: no `x/y` repository under evals/replay/ (%s)"
         % (", ".join(sorted(_hits)[:5]) or "none"), not _hits)

_stub = read("evals/replay/forge-stub/gh")
c.expect("pattern", "L17: the stub builds URLs from the fixture's repo",
         'return "https://github.com/" + repo_slug(st)' in _stub)
c.expect("pattern", "L17: an unserved --json field is UNKNOWN",
         'unknown("%s --json %s: not served by the stub"' in _stub)
c.expect("pattern", "L17: no route splits --json itself",
         '(flag_val(argv, "--json") or "").split(",")' not in _stub)
