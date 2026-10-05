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
         "prs": {"101": {"number": 101, "title": "Spec: #5", "state": "OPEN", "isDraft": False,
                         "headRefName": "spec/5", "baseRefName": "main"}},
         "issues": {"5": {"title": "x", "labels": []},
                    "6": {"title": "y", "labels": ["track: spec"], "state": "closed"}}}

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


def run_route(argv, cwd=None):
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(STATE, f)
        p = subprocess.run([sys.executable, GH] + argv, capture_output=True, text=True,
                           env={**os.environ, "FORGE_STATE": d}, cwd=cwd)
        routes = [json.loads(line)["route"]
                  for line in open(os.path.join(d, "journal.jsonl")) if line.strip()]
        return p.returncode, p.stdout, routes
    finally:
        shutil.rmtree(d, ignore_errors=True)


def git_sandbox():
    """A work repo whose origin (a bare remote) has main and spec/5 — the
    shape every replay sandbox has; the git-ref route reads it."""
    tmp = tempfile.mkdtemp()
    work = os.path.join(tmp, "work")
    env = dict(os.environ, GIT_AUTHOR_NAME="a", GIT_AUTHOR_EMAIL="a@a",
               GIT_COMMITTER_NAME="a", GIT_COMMITTER_EMAIL="a@a")
    for cmd, cwd in (("git init -q --bare origin.git", tmp),
                     ("git init -q -b main work", tmp),
                     ("git commit -q --allow-empty -m seed && git checkout -q -b spec/5 "
                      "&& mkdir -p docs/specs/5 && echo '# Spec #5' > docs/specs/5/spec.md "
                      "&& echo '# Tech' > docs/specs/5/technical-spec.md && git add -A "
                      "&& git commit -qm spec && git checkout -q main "
                      "&& git remote add origin ../origin.git && git push -q origin --all", work)):
        subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env, check=True, capture_output=True)
    return tmp, work


# (name, argv, cwd kind, expected route, exit code, stdout needle)
REF_ROUTES = [
    ("branch present → its SHA",
     ["api", "repos/acme/demo/git/ref/heads/spec%2F5", "--jq", ".object.sha"],
     "work", "git-ref", 0, None),
    ("branch present, refs/ spelling, unencoded", ["api", "repos/acme/demo/git/refs/heads/spec/5"],
     "work", "git-ref", 0, '"ref": "refs/heads/spec/5"'),
    ("branch absent → 404, still a routed read", ["api", "repos/acme/demo/git/ref/heads/spec%2F9"],
     "work", "git-ref", 1, ""),
    ("leading slash accepted",
     ["api", "/repos/acme/demo/git/ref/heads/spec%2F5", "--jq", ".object.sha"],
     "work", "git-ref", 0, None),
    ("a tail of another branch is absent (heads/5 vs spec/5)",
     ["api", "repos/acme/demo/git/ref/heads/5"], "work", "git-ref", 1, ""),
    ("contents: a directory on a branch",
     ["api", "repos/acme/demo/contents/docs/specs/5?ref=spec/5", "--jq", ".[].path"],
     "work", "contents", 0, "docs/specs/5/spec.md"),
    ("contents: a file on a branch (base64)",
     ["api", "repos/acme/demo/contents/docs/specs/5/spec.md?ref=spec/5", "--jq", ".encoding"],
     "work", "contents", 0, "base64"),
    ("contents: absent path → 404, routed",
     ["api", "repos/acme/demo/contents/docs/nope?ref=spec/5"],
     "work", "contents", 1, ""),
    ("contents: absent ref → 404, routed", ["api", "repos/acme/demo/contents/docs?ref=spec/9"],
     "work", "contents", 1, ""),
    ("pulls/<n>: REST view, head.sha from the objects",
     ["api", "repos/acme/demo/pulls/101", "--jq", ".head.sha"], "work", "pr-view", 0, None),
    ("pulls/<n>: absent number → UNKNOWN", ["api", "repos/acme/demo/pulls/999"],
     "work", "UNKNOWN", 64, ""),
    ("pulls/<n>: PATCH stays UNKNOWN", ["api", "-X", "PATCH", "repos/acme/demo/pulls/101"],
     "work", "UNKNOWN", 64, ""),
    ("commits/<ref>: the ref's SHA", ["api", "repos/acme/demo/commits/spec/5", "--jq", ".sha"],
     "work", "commit-view", 0, None),
    ("commits/<ref>: unknown ref → 422, routed", ["api", "repos/acme/demo/commits/nope"],
     "work", "commit-view", 1, ""),
    ("PUT to contents stays UNKNOWN", ["api", "-X", "PUT", "repos/acme/demo/contents/docs/x.md"],
     "work", "UNKNOWN", 64, ""),
    ("POST to a ref stays UNKNOWN",
     ["api", "-X", "POST", "repos/acme/demo/git/refs/heads/spec%2F5"],
     "work", "UNKNOWN", 64, ""),
]


def main():
    passed = failed = 0
    tmp, work = git_sandbox()
    try:
        head = subprocess.check_output(["git", "-C", work, "rev-parse", "spec/5"],
                                       text=True).strip()
        for name, argv, _, route, rc_want, needle in REF_ROUTES:
            rc, out, routes = run_route(argv, cwd=work)
            ok = routes == [route] and rc == rc_want
            if rc_want == 0:
                ok = ok and (needle in out if needle else out.strip() == head)
            print("%s route: %s -> %s" % ("PASS" if ok else "FAIL", name, route),
                  "" if ok else "(got rc=%d routes=%s out=%r)" % (rc, routes, out[:120]))
            passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
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
