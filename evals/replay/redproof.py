#!/usr/bin/env python3
"""The harness's own red-proof: the forge stub's routes and the runners'
resume rule score correctly. No model, no tokens — the stub runs against a
throwaway state, the resume rule against staged result.json files.

    python3 evals/replay/redproof.py

- ROUTES — each argv the stub must route, or refuse, with the journal
  route it must write. `issue close` (patrol's close-out, #41) is a write
  that journals `issue-close`; an absent id stays UNKNOWN. Identity by name
  (`/apps/<slug>`, `/users/<login>`,
  judgment k=2 on 1.17.0) is keyed on the fixture's agent_login: the bot's
  own slug/login is a canned view, any other name is an absent id and
  stays UNKNOWN, a POST to the same target stays UNKNOWN.
- RESUME — a result.json whose invalid_reason is the quota banner is not
  "done": the sweep stopped there and resumes there. Every other result,
  valid or invalid, is.

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only,
Python 3.9-compatible, like the hook suite.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replaylib as rl  # noqa: E402

GH = os.path.join(HERE, "forge-stub", "gh")
STATE = {"agent_login": "roz-gatekeeper",
         "issues": {"5": {"title": "x", "labels": []},
                    "6": {"title": "y", "labels": ["track: spec"], "state": "closed"}},
         "prs": {}}

# (name, argv after `gh`, expected journal route, a string stdout must carry)
ROUTES = [
    ("app by slug, --jq object", ["api", "/apps/roz-gatekeeper", "--jq", "{id,slug,name}"],
     "app-view", '"slug": "roz-gatekeeper"'),
    ("bot login, REST spelling",
     ["api", "/users/roz-gatekeeper%5Bbot%5D", "--jq", "{login,id,type}"],
     "user-view", '"type": "Bot"'),
    ("bot login, literal brackets", ["api", "users/roz-gatekeeper[bot]"],
     "user-view", '"login": "roz-gatekeeper[bot]"'),
    ("bare login, no slash", ["api", "users/roz-gatekeeper"], "user-view", '"type": "User"'),
    ("caller identity unchanged", ["api", "user"], "user-view", '"login": "roz-gatekeeper"'),
    ("another app slug", ["api", "/apps/other-app"], "UNKNOWN", ""),
    ("the bot's login as an app slug", ["api", "/apps/roz-gatekeeper%5Bbot%5D"], "UNKNOWN", ""),
    ("a human login", ["api", "/users/paul"], "UNKNOWN", ""),
    ("a sub-resource", ["api", "/users/roz-gatekeeper/repos"], "UNKNOWN", ""),
    ("POST to the bot's login", ["api", "-X", "POST", "/users/roz-gatekeeper"], "UNKNOWN", ""),
    ("issue close, in fixture", ["issue", "close", "5"], "issue-close", "Closed issue #5"),
    ("issue close, absent id", ["issue", "close", "9"], "UNKNOWN", ""),
    ("closed issues wearing a track label (the close-out scan)",
     ["issue", "list", "--state", "closed", "--label", "track: spec", "--json", "number,labels"],
     "issue-list", '"number": 6'),
]

# (name, result.json content or None for absent, iteration_done)
RESUME = [
    ("no result.json", None, False),
    ("quota banner", {"valid": False, "invalid_reason": "quota-exhausted"}, False),
    ("valid", {"valid": True}, True),
    ("cut short", {"valid": False, "invalid_reason": "session cut short: " + rl.TIMEOUT_NOTE % 900},
     True),
    ("UNKNOWN route", {"valid": False, "invalid_reason": "forge stub hit 1 UNKNOWN route(s)"},
     True),
    ("unreadable", "not json", False),
    ("JSON but not a result", "null", False),
    ("JSON list", "[]", False),
]


def run_route(argv):
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(STATE, f)
        p = subprocess.run([sys.executable, GH] + argv, capture_output=True, text=True,
                           env={**os.environ, "FORGE_STATE": d})
        routes = [json.loads(line)["route"]
                  for line in open(os.path.join(d, "journal.jsonl")) if line.strip()]
        return p.returncode, p.stdout, routes
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    passed = failed = 0
    for name, argv, route, needle in ROUTES:
        rc, out, routes = run_route(argv)
        ok = routes == [route] and (rc == 64) == (route == "UNKNOWN")
        if route != "UNKNOWN":
            try:
                shown = json.dumps(json.loads(out), indent=1)
            except ValueError:
                shown = out   # a write route answers in gh's prose, not JSON
            ok = ok and rc == 0 and needle in shown
        print("%s route: %s -> %s" % ("PASS" if ok else "FAIL", name, route),
              "" if ok else "(got rc=%d routes=%s out=%r)" % (rc, routes, out[:120]))
        passed, failed = passed + ok, failed + (not ok)
    for name, content, want in RESUME:
        d = tempfile.mkdtemp()
        try:
            if content is not None:
                with open(os.path.join(d, "result.json"), "w") as f:
                    f.write(content if isinstance(content, str) else json.dumps(content))
            got = rl.iteration_done(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        ok = got is want
        print("%s resume: %s -> %s" % ("PASS" if ok else "FAIL", name,
                                        "done" if want else "re-run"))
        passed, failed = passed + ok, failed + (not ok)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
