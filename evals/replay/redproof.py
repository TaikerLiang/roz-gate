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
- EXPORT — the Langfuse exporter's mapping (#80) on a staged run dir: one
  trace per run with the case's session and verdict tag, a generation per
  API call (events sharing a message id merged, tool results interleaved)
  carrying its usage, a tool span ended by its matched
  tool_result, the sub-agent event nested under its Agent span, journal
  writes (not reads) as events — a write stamped `ts` under the innermost
  tool span holding it, the rest after the transcript's end (#190) — the
  verdict and every claim as scores, the run's `case_fp` / `plugin_sha`
  and the `stale` tag from result.json, and the marker rule (an exported
  run dir is refused, Langfuse v4 appends) — with no network: `build()`
  is called directly.
- MARKER (#190) — a send that fails after its first post leaves
  `langfuse.json` pending; the next export is refused as partial, and
  `--force` sends again and marks it done. `post` is stubbed.
- FINGERPRINT (#190) — `aggregate()` over staged result.json files: a run
  whose `case_fp` differs from the case's current one is stale and out of
  the rate, a run without one is unknown and in, and a case whose valid
  runs are all stale reports no rate. The stub's journal entries carry
  the clock.
- VARIANT (#199) — `variant_plugin("B")` is a copy of the plugin root that
  differs from the checkout in exactly `references/qa-brief.md`, carrying
  B.md's hash; `variant_plugin("A")` is the checkout itself; the stamp
  records the hash read back from the plugin dir; `aggregate()` counts a run
  whose `brief_sha256` differs from the variant file's current hash as stale
  (like a fingerprint mismatch) and scores a `<case>@<V>` dir under its
  case with the variant named; a checker's exit 3 (`replaylib.invalid`) is
  an invalid iteration carrying the checker's reason, never a FAIL; the
  fingerprint follows a case's shared fixture tree (`"fixture"`).

Run by evals/replay/run_redproofs.py (pre-push and CI). Stdlib only,
Python 3.9-compatible, like the hook suite.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export_langfuse as ex  # noqa: E402
import replaylib as rl  # noqa: E402
import run_replay as rr  # noqa: E402

GH = os.path.join(HERE, "forge-stub", "gh")
STATE = {"agent_login": "roz-gatekeeper",
         "prs": {"101": {"number": 101, "title": "Spec: #5", "state": "OPEN", "isDraft": False,
                         "headRefName": "spec/5", "baseRefName": "main",
                         "comments": [{"id": 1, "author": "paul",
                                       "created_at": "2026-08-23T10:00:00Z",
                                       "body": "**[reviewer] · code-review** — nit 0\n"
                                               "reviewed-sha: {{sha:spec/5}}"}],
                         "threads": [{"path": "tests/acceptance/test_x.py", "line": 3,
                                      "comments": [{"databaseId": 9101, "author": "paul",
                                                    "body": "**[reviewer] · fidelity** — q",
                                                    "createdAt": "2026-08-23T10:00:00Z"}]}]}},
         "issues": {"5": {"title": "x", "labels": []},
                    "6": {"title": "y", "labels": ["track: spec"], "state": "closed"},
                    # #205: blocked by open #5 and closed #6; #8's lookup refused
                    "7": {"title": "z", "labels": [], "blocked_by": [5, 6]},
                    "8": {"title": "w", "labels": [], "blocked_by_error": 403}}}

# (name, argv after `gh`, expected journal route, a string stdout must carry)
ROUTES = [
    # #205 — ISSUE-BLOCKED-BY, read only
    ("blocked_by: an open and a closed blocker, each with its own state",
     ["api", "repos/acme/demo/issues/7/dependencies/blocked_by"], "issue-blocked-by",
     '"state": "closed"'),
    ("blocked_by: the doc's --jq projection, --paginate (codex review, PR #249)",
     ["api", "--paginate", "repos/{owner}/{repo}/issues/7/dependencies/blocked_by", "--jq",
      "[.[] | {number, state, url: .html_url}]"], "issue-blocked-by", '"url": "https://github.com/acme/demo/issues/5"'),
    ("blocked_by: no blockers is an empty list, not an error",
     ["api", "repos/acme/demo/issues/5/dependencies/blocked_by"], "issue-blocked-by", "[]"),
    ("blocked_by: an issue not in the fixture → UNKNOWN",
     ["api", "repos/acme/demo/issues/99/dependencies/blocked_by"], "UNKNOWN", ""),
    ("blocked_by: a POST (patrol never writes relationships) → UNKNOWN",
     ["api", "-X", "POST", "repos/acme/demo/issues/7/dependencies/blocked_by",
      "-F", "issue_id=1"], "UNKNOWN", ""),
    ("blocked_by: a DELETE → UNKNOWN",
     ["api", "-X", "DELETE", "repos/acme/demo/issues/7/dependencies/blocked_by/5"], "UNKNOWN", ""),
    # #225: the PR number of a reviewThreads query comes from whatever variable
    # the seat named — `$p` in D12's run, not only `pr` / `number`.
    ("graphql threads, PR number in a seat-named variable ($p)",
     ["api", "graphql", "-f",
      "query=query($o:String!,$r:String!,$p:Int!){repository(owner:$o,name:$r)"
      "{pullRequest(number:$p){reviewThreads(first:100){nodes{id isResolved path line}}}}}",
      "-F", "o=acme", "-F", "r=demo", "-F", "p=101",
      "--jq", ".data.repository.pullRequest.reviewThreads"],
     "threads-list", '"nodes"'),
    ("graphql threads, PR number in `pr` (the doc's form)",
     ["api", "graphql", "-f",
      "query=query($pr:Int!){repository(owner:\"acme\",name:\"demo\")"
      "{pullRequest(number:$pr){reviewThreads(first:100){nodes{id}}}}}",
      "-F", "pr=101", "--jq", ".data.repository.pullRequest.reviewThreads"],
     "threads-list", '"nodes"'),
    ("graphql threads, the variable no field supplies -> UNKNOWN",
     ["api", "graphql", "-f",
      "query=query($p:Int!){repository(owner:\"acme\",name:\"demo\")"
      "{pullRequest(number:$p){reviewThreads(first:100){nodes{id}}}}}",
      "-F", "pr=101"],
     "UNKNOWN", None),
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
    # #219 — a seat's free-form --jq (string interpolation, a slice, `//`, an
    # object with an expression value) is outside the evaluated subset and
    # was UNKNOWN: 8 of the #199 pilot's 13 iterations. The system jq answers.
    ("free-form --jq: D10's interpolation + slice",
     ["api", "repos/acme/demo/pulls/101/comments", "--jq",
      '.[] | "\\(.id) \\(.path):\\(.line) \\(.body[0:46])"'],
     "review-comments-list", "9101 tests/acceptance/test_x.py:3 **[reviewer]"),
    ("free-form --jq: D13@B's `//` default and a literal newline",
     ["api", "repos/acme/demo/pulls/101/comments", "--jq",
      '.[] | "--- id=\\(.id) in_reply_to=\\(.in_reply_to_id // "-")\\n\\(.body)"'],
     "review-comments-list", "in_reply_to=-\n**[reviewer]"),
    ("free-form --jq: D15's object with an expression value",
     ["api", "repos/acme/demo/pulls/101/comments", "--jq",
      ".[] | {id, path, line, opens: (.body[0:30])}"],
     "review-comments-list", '"opens"'),
    ("pr edit: title + inline body, in fixture", ["pr", "edit", "101", "--title", "T2",
                                                  "--body", "B2"], "pr-edit", ""),
    ("pr edit: absent number", ["pr", "edit", "999", "--body", "x"], "UNKNOWN", ""),
    # codex, PR #223: a flag the stub does not perform must not journal a write
    ("pr edit: --base is not performed → UNKNOWN", ["pr", "edit", "101", "--base", "other"],
     "UNKNOWN", ""),
    ("pr edit: nothing to edit → UNKNOWN", ["pr", "edit", "101"], "UNKNOWN", ""),
    # haiku55 k=3 (#199): labels on a PR are performed
    ("pr edit: --add-label of a repo label", ["pr", "edit", "101", "--add-label",
                                              "status: blocked"], "pr-edit", ""),
    ("pr edit: --remove-label beside a body", ["pr", "edit", "101", "--body", "x",
                                               "--remove-label", "track: spec"],
     "pr-edit", ""),
    ("pr edit: comma-separated labels in one value (codex review, PR #242)",
     ["pr", "edit", "101", "--add-label", "track: spec,status: blocked"], "pr-edit", ""),
    # #237 — the forms Haiku's seats wrote in the k=3 top-up (19 of 44
    # iterations INVALID on them); every one is a call gh performs.
    ("implied POST: inline comment with -f fields and no -X (gh's rule)",
     ["api", "repos/acme/demo/pulls/101/comments", "-f", "body=**[qa] x", "-f",
      "path=tests/acceptance/test_x.py", "-F", "line=3", "-f", "side=RIGHT", "-f",
      "commit_id=abc", "--jq", ".id"],
     "thread-post-inline", ""),
    ("--method POST, the long form", ["api", "--method", "POST",
                                      "repos/acme/demo/pulls/101/comments", "-f", "body=y",
                                      "-f", "path=p", "-F", "line=1"],
     "thread-post-inline", '"id"'),
    ("implied POST: a top-level comment through REST with no -X",
     ["api", "repos/acme/demo/issues/101/comments", "-f", "body=hi"], "pr-comment", '"id"'),
    ("--method PATCH on a top-level comment",
     ["api", "--method", "PATCH", "repos/acme/demo/issues/comments/1", "-f", "body=edited"],
     "comment-edit", '"id": 1'),
    ("review comment by id (no PR number), GET",
     ["api", "repos/acme/demo/pulls/comments/9101", "--jq", "{id, path, line}"],
     "review-comment-view", '"id": 9101'),
    ("review comment by id, PATCH",
     ["api", "-X", "PATCH", "repos/acme/demo/pulls/comments/9101", "-F", "body=fixed"],
     "review-comment-edit", '"body": "fixed"'),
    ("review comment by id, DELETE",
     ["api", "-X", "DELETE", "repos/acme/demo/pulls/comments/9101"], "review-comment-delete", ""),
    ("review comment by id, absent -> UNKNOWN",
     ["api", "repos/acme/demo/pulls/comments/4242"], "UNKNOWN", ""),
    ("top-level comment DELETE", ["api", "-X", "DELETE", "repos/acme/demo/issues/comments/1"],
     "comment-delete", ""),
    ("issue labels through REST, {owner}/{repo} placeholders",
     ["api", "repos/{owner}/{repo}/issues/6/labels", "--jq", ".[].name"],
     "issue-labels", "track: spec"),
    ("issue labels through REST, :owner/:repo placeholders",
     ["api", "repos/:owner/:repo/issues/5/labels"], "issue-labels", "[]"),
    ("graphql: the repository's node id alone",
     ["api", "graphql", "-f", "query=query{repository(owner:\"acme\",name:\"demo\"){ id }}"],
     "graphql-repo-id", '"id"'),
    ("pr ready --undo: back to draft", ["pr", "ready", "101", "--undo"], "pr-draft", ""),
    # haiku55 k=3 resume (2026-11-08): a leading slash on a write route
    ("leading slash on an inline-comment POST",
     ["api", "-X", "POST", "/repos/acme/demo/pulls/101/comments", "-f", "body=x", "-f",
      "path=p", "-F", "line=1"], "thread-post-inline", '"id"'),
]

# (also) graphql aliases: two PRs' threads in one query, each under its alias
ALIASED_Q = ("query=query{repository(owner:\"acme\",name:\"demo\"){"
             "a1:pullRequest(number:101){reviewThreads(first:100){nodes{path}}} "
             "a2:pullRequest(number:101){reviewThreads(first:100){nodes{isResolved}}}}}")
# codex, PR #238: every answer honours --jq like the REST reads do — the
# exact stdout, since the envelope would also *contain* the needle:
# (name, argv, expected route, exact stdout)
JQ_EXACT = [
    ("graphql repo id, --jq to the scalar",
     ["api", "graphql", "-f", "query=query{repository(owner:\"acme\",name:\"demo\"){ id }}",
      "--jq", ".data.repository.id"],
     "graphql-repo-id", "R_kgDOTqtK8g"),
    ("graphql threads, --jq to the thread paths",
     ["api", "graphql", "-f",
      "query=query{repository(owner:\"acme\",name:\"demo\")"
      "{pullRequest(number:101){reviewThreads(first:100){nodes{path}}}}}",
      "--jq", ".data.repository.pullRequest.reviewThreads.nodes[].path"],
     "threads-list", "tests/acceptance/test_x.py"),
    ("graphql threads under aliases (two pullRequest fields in one query)",
     ["api", "graphql", "-f", ALIASED_Q, "--jq",
      "[.data.repository.a1.reviewThreads.nodes[0].path,"
      " .data.repository.a2.reviewThreads.nodes[0].isResolved] | @csv"],
     "threads-list", '"tests/acceptance/test_x.py",false'),
    # codex, PR #238 round 2: the write answers too — Haiku's seats wrote
    # `--jq .id` / `--jq .html_url` on the POST and the PATCH.
    ("inline comment POST, --jq .path", ["api", "repos/acme/demo/pulls/101/comments", "-f",
                                        "body=x", "-f", "path=tests/acceptance/test_x.py",
                                        "-F", "line=3", "--jq", ".path"],
     "thread-post-inline", "tests/acceptance/test_x.py"),
    ("review comment PATCH, --jq .id", ["api", "-X", "PATCH",
                                       "repos/acme/demo/pulls/comments/9101", "-f",
                                       "body=fixed", "--jq", ".id"],
     "review-comment-edit", "9101"),
    ("top-level comment PATCH, --jq .id", ["api", "-X", "PATCH",
                                          "repos/acme/demo/issues/comments/1", "-f",
                                          "body=e", "--jq", ".id"],
     "comment-edit", "1"),
    ("top-level comment POST through REST, --jq .html_url",
     ["api", "repos/acme/demo/issues/101/comments", "-f", "body=hi", "--jq", ".html_url"],
     "pr-comment", "https://github.com/acme/demo/pull/101#issuecomment-1001"),   # next_id
    ("thread reply, --jq .id is a number",
     ["api", "-X", "POST", "repos/acme/demo/pulls/101/comments/9101/replies", "-f", "body=r",
      "--jq", ".in_reply_to_id"],
     "thread-reply", "9101"),
]

# #237 ruling 1 — a target gh itself refuses answers as gh does (exit 1, the
# journal names the HTTP error), not UNKNOWN: (name, argv, expected route)
GH_ERRORS = [
    ("#205: the blocker lookup refused (an older GHES / no scope) — gh's HTTP 403",
     ["api", "repos/acme/demo/issues/8/dependencies/blocked_by"], "http-403"),
    # haiku55 k=3 resume: the number segment is a pasted JSON fragment, or empty
    ("a JSON fragment as the PR number",
     ["api", 'repos/:owner/:repo/issues/[{"number": 102}]/comments', "--jq", ".[]"], "http-404"),
    ("a fragment's tail as the PR number", ["api", "repos/{owner}/{repo}/pulls/101},/comments"],
     "http-404"),
    ("an empty id segment (trailing slash)",
     ["api", "-X", "DELETE", "repos/acme/demo/pulls/comments/"], "http-404"),
    ("PATCH on an issue's labels — GitHub has no such endpoint",
     ["api", "-X", "PATCH", "repos/{owner}/{repo}/issues/5/labels"], "http-404"),
    ("pr ready --undo with no selector, the current branch has no PR",
     ["pr", "ready", "--undo"], "gh-error"),
    ("pr ready with a JSON fragment as the selector (gh reads it as a branch)",
     ["pr", "ready", '[{"number": 103}]'], "gh-error"),
    ("pr edit --add-label of a label the repo does not have (gh: 'x' not found)",
     ["pr", "edit", "101", "--add-label", "x"], "gh-error"),
    ("a JSON fragment pasted as owner/repo, `//` in the path",
     ["api", 'repos/{"owner": {"login": "acme"}, "name": "demo"}//issues/1', "--jq", ".[]"],
     "http-404"),
    ("a JSON fragment as owner, one slash",
     ["api", 'repos/{"owner": {"login": "acme"}, "name": "demo"}/pulls/101/comments'],
     "http-404"),
    ("graphql with a placeholder left in owner",
     ["api", "graphql", "-f", 'query=query{repository(owner:"{o}",name:"x"){id}}'],
     "graphql-error"),
    ("graphql with a JSON fragment as owner",
     ["api", "graphql", "-f",
      'query=query{repository(owner:"{"owner": {"login": "acme"}}",name:"demo")'
      '{pullRequest(number:101){reviewThreads(first:100){nodes{id}}}}}'],
     "graphql-error"),
]

# #250 — the stub's URLs name the fixture's repository, and a `--json` field
# the stub does not serve is UNKNOWN before anything is printed. The fixture
# is NOT the default repository: a hard-coded `acme/demo` is as red here as
# the `x/y` it replaced. (name, argv, route, needles stdout must carry —
# for UNKNOWN: the field the journal note must name)
OCTO = "https://github.com/octo/widgets"
REPO_ROUTES = [
    ("issue view --json url names the fixture's repository",
     ["issue", "view", "5", "--json", "url"], "issue-view", ['"url": "%s/issues/5"' % OCTO]),
    ("issue view --json state,closed — an open issue",
     ["issue", "view", "5", "--json", "state,closed"], "issue-view",
     ['"state": "OPEN"', '"closed": false']),
    ("issue view --json state,closed — a closed issue",
     ["issue", "view", "6", "--json", "state,closed"], "issue-view",
     ['"state": "CLOSED"', '"closed": true']),
    ("issue list --json number,url",
     ["issue", "list", "--json", "number,url"], "issue-list", ['"url": "%s/issues/5"' % OCTO]),
    ("pr view --json url,closed",
     ["pr", "view", "101", "--json", "url,closed"], "pr-view",
     ['"url": "%s/pull/101"' % OCTO, '"closed": false']),
    ("pr list --json number,url",
     ["pr", "list", "--json", "number,url"], "pr-list", ['"url": "%s/pull/101"' % OCTO]),
    ("repo view --json nameWithOwner,url — and only those",
     ["repo", "view", "--json", "nameWithOwner,url"], "repo-view",
     ['{"nameWithOwner": "octo/widgets", "url": "%s"}' % OCTO]),
    ("repo view --json owner,name still answers",
     ["repo", "view", "--json", "owner,name"], "repo-view",
     ['{"owner": {"login": "octo"}, "name": "widgets"}']),
    ("a printed URL (pr comment)",
     ["pr", "comment", "101", "--body", "hi"], "pr-comment", ["%s/pull/101#issuecomment-" % OCTO]),
    ("an html_url (blocked_by)",
     ["api", "repos/{owner}/{repo}/issues/7/dependencies/blocked_by", "--jq", ".[0].html_url"],
     "issue-blocked-by", ["%s/issues/5" % OCTO]),
    # one unserved field makes the whole command UNKNOWN — no partial JSON
    ("issue view --json url,updatedAt (served beside unserved)",
     ["issue", "view", "5", "--json", "url,updatedAt"], "UNKNOWN", ["updatedAt"]),
    ("issue list --json number,updatedAt",
     ["issue", "list", "--json", "number,updatedAt"], "UNKNOWN", ["updatedAt"]),
    ("pr view --json url,statusCheckRollup",
     ["pr", "view", "101", "--json", "url,statusCheckRollup"], "UNKNOWN", ["statusCheckRollup"]),
    ("pr list --json number,statusCheckRollup",
     ["pr", "list", "--json", "number,statusCheckRollup"], "UNKNOWN", ["statusCheckRollup"]),
    ("repo view --json name,description",
     ["repo", "view", "--json", "name,description"], "UNKNOWN", ["description"]),
    ("issue view --json bogus (a field gh itself lacks is unserved too)",
     ["issue", "view", "5", "--json", "bogus"], "UNKNOWN", ["bogus"]),
]

# #291 — the `--json` fields a Haiku seat asks for. Each is served only from
# what the fixture states or the sandbox proves; where neither does, the
# call stays UNKNOWN and its note names the field. Never a default.
def fields_sandbox():
    """origin (HEAD → main) with: spec/5, open against main; feat/7, merged
    into main by a true merge commit; feat/8, squashed onto main; ren/9, a
    pure rename of app.txt."""
    tmp = tempfile.mkdtemp()
    work = os.path.join(tmp, "work")
    env = dict(os.environ, GIT_AUTHOR_NAME="a", GIT_AUTHOR_EMAIL="a@a",
               GIT_COMMITTER_NAME="a", GIT_COMMITTER_EMAIL="a@a")
    for cmd, cwd in (
            ("git init -q --bare -b main origin.git", tmp),
            ("git init -q -b main work", tmp),
            ("echo demo > app.txt && git add -A && git commit -qm seed"
             " && git checkout -qb feat/7 && echo seven > seven.txt && git add -A"
             " && git commit -qm seven && git checkout -q main"
             " && git merge -q --no-ff -m 'merge feat/7' feat/7"
             " && git checkout -qb feat/8 && echo eight > eight.txt && git add -A"
             " && git commit -qm eight && git checkout -q main"
             " && git merge -q --squash feat/8 && git commit -qm 'squash feat/8'"
             " && git checkout -qb spec/5 && mkdir -p docs && printf 'a\\nb\\n' > docs/spec.md"
             " && echo more >> app.txt && git add -A && git commit -qm spec"
             " && git checkout -q main && git checkout -qb ren/9"
             " && git mv app.txt 'renamed app.txt' && git commit -qm rename"
             " && git checkout -q main && git remote add origin ../origin.git"
             " && git push -q origin --all", work)):
        subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env, check=True, capture_output=True)
    return tmp, work


def stub(argv, state, cwd=None, state_dir=None):
    """(rc, stdout, stderr, journal entries) for one call."""
    d = state_dir or tempfile.mkdtemp()
    try:
        if not os.path.exists(os.path.join(d, "state.json")):
            with open(os.path.join(d, "state.json"), "w") as f:
                json.dump(state, f)
        p = subprocess.run([sys.executable, GH] + argv, capture_output=True, text=True,
                           env={**os.environ, "FORGE_STATE": d}, cwd=cwd, input="")
        path = os.path.join(d, "journal.jsonl")
        entries = [json.loads(line) for line in open(path) if line.strip()] \
            if os.path.exists(path) else []
        return p.returncode, p.stdout, p.stderr, entries
    finally:
        if not state_dir:
            shutil.rmtree(d, ignore_errors=True)


def fields_rows():
    """[(name, ok)] — #291."""
    def pr(**kw):
        base = {"number": 101, "title": "Spec: #5", "state": "OPEN", "isDraft": False,
                "headRefName": "spec/5", "baseRefName": "main", "threads": [], "reviews": [],
                "comments": [{"id": 1, "author": "paul", "created_at": "2026-08-23T10:00:00Z",
                              "body": "first"}]}
        base.update(kw)
        return base

    def rv(author, state, at):
        return {"id": at, "author": author, "state": state, "body": "",
                "submitted_at": "2026-08-%sT10:00:00Z" % at}

    def st(prs=None, issues=None, **kw):
        s = {"agent_login": "roz-gatekeeper", "prs": prs or {"101": pr()},
             "issues": issues or {
                 "5": {"title": "x", "labels": [], "createdAt": "2026-08-20T09:00:00Z"},
                 "6": {"title": "y", "labels": ["track: spec"], "state": "closed"}}}
        s.update(kw)
        return s

    rows = []
    tmp, work = fields_sandbox()

    def served(name, state, argv, route, *needles, cwd=None):
        rc, out, err, j = stub(argv, state, cwd=cwd or work)
        rows.append((name, rc == 0 and [e["route"] for e in j] == [route]
                     and all(n in out for n in needles)))

    def unknown(name, state, argv, field, cwd=None):
        rc, out, err, j = stub(argv, state, cwd=cwd or work)
        rows.append((name, rc == 64 and [e["route"] for e in j] == ["UNKNOWN"] and out == ""
                     and field in j[-1].get("note", "")))

    try:
        merge7 = subprocess.check_output(
            ["git", "-C", work, "log", "--merges", "--format=%H", "-1", "main"], text=True).strip()
        V = ["pr", "view", "101", "--json"]
        served("pr view --json comments: the fixture's comments", st(), V + ["comments"], "pr-view",
               '"body": "first"', '"author": {"login": "paul"}',
               '"createdAt": "2026-08-23T10:00:00Z"')
        served("pr view --json comments,reviews: no reviews is an empty list", st(),
               V + ["comments,reviews"], "pr-view", '"reviews": []', '"body": "first"')
        served("pr view --json reviews: state, author, submittedAt",
               st({"101": pr(reviews=[rv("ann", "CHANGES_REQUESTED", "24")])}), V + ["reviews"],
               "pr-view", '"state": "CHANGES_REQUESTED"', '"author": {"login": "ann"}',
               '"submittedAt": "2026-08-24T10:00:00Z"')
        for name, reviews, want in (
                ("no reviews", [], '""'),
                ("an approval", [rv("ann", "APPROVED", "24")], '"APPROVED"'),
                ("a change request", [rv("ann", "CHANGES_REQUESTED", "24")], '"CHANGES_REQUESTED"'),
                ("a later approval supersedes the same author's change request",
                 [rv("ann", "CHANGES_REQUESTED", "24"), rv("ann", "APPROVED", "25")], '"APPROVED"'),
                ("one author approves, another requests changes",
                 [rv("ann", "APPROVED", "24"), rv("bob", "CHANGES_REQUESTED", "25")],
                 '"CHANGES_REQUESTED"'),
                ("a later comment does not undo an approval",
                 [rv("ann", "APPROVED", "24"), rv("ann", "COMMENTED", "25")], '"APPROVED"')):
            served("pr view --json reviewDecision: %s" % name, st({"101": pr(reviews=reviews)}),
                   V + ["reviewDecision"], "pr-view", '"reviewDecision": %s' % want)
        unknown("pr view --json reviewDecision: a review state the corpus never carried",
                st({"101": pr(reviews=[rv("ann", "DISMISSED", "24")])}), V + ["reviewDecision"],
                "reviewDecision")
        served("pr view --json mergeCommit: an open PR has none", st(), V + ["mergeCommit"],
               "pr-view", '"mergeCommit": null')
        served("pr view --json mergeCommit: the fixture states it",
               st({"101": pr(state="MERGED", mergeCommit="abc123")}), V + ["mergeCommit"],
               "pr-view", '"mergeCommit": {"oid": "abc123"}')
        served("pr view --json mergeCommit: the one merge commit on the base with the head "
               "as a parent",
               st({"101": pr(state="MERGED", headRefName="feat/7")}), V + ["mergeCommit"],
               "pr-view", '"mergeCommit": {"oid": "%s"}' % merge7)
        unknown("pr view --json mergeCommit: a squash leaves no such commit — not guessed",
                st({"101": pr(state="MERGED", headRefName="feat/8")}), V + ["mergeCommit"],
                "mergeCommit")
        unknown("pr view --json comments,mergeCommit: one unanswerable field, nothing printed",
                st({"101": pr(state="MERGED", headRefName="feat/8")}),
                V + ["comments,mergeCommit"], "mergeCommit")
        served("pr view --json files: an open PR's diff against its base", st(), V + ["files"],
               "pr-view", '{"path": "docs/spec.md", "additions": 2, "deletions": 0, '
               '"changeType": "ADDED"}', '{"path": "app.txt", "additions": 1, "deletions": 0, '
               '"changeType": "MODIFIED"}')
        # codex review, PR #297 — the same evidence as the REST routes give
        head5 = subprocess.check_output(["git", "-C", work, "rev-parse", "spec/5"],
                                        text=True).strip()
        served("pr view --json comments: a fixture's {{sha:<ref>}} is the sandbox's SHA",
               st({"101": pr(comments=[{"id": 1, "author": "paul",
                                        "created_at": "2026-08-23T10:00:00Z",
                                        "body": "reviewed-sha: {{sha:spec/5}}"}])}),
               V + ["comments"], "pr-view", '"body": "reviewed-sha: %s"' % head5)
        served("pr view --json reviews: the same expansion in a review's body",
               st({"101": pr(reviews=[dict(rv("ann", "APPROVED", "24"),
                                           body="at {{sha:spec/5}}")])}),
               V + ["reviews"], "pr-view", '"body": "at %s"' % head5)
        served("pr view --json files: a rename is the new path, RENAMED",
               st({"101": pr(headRefName="ren/9")}), V + ["files"], "pr-view",
               '[{"path": "renamed app.txt", "additions": 0, "deletions": 0, '
               '"changeType": "RENAMED"}]')
        unknown("pr view --json files: a merged PR's files are not the sandbox's diff",
                st({"101": pr(state="MERGED", headRefName="feat/7")}), V + ["files"], "files")
        served("pr view --json author: the fixture states it", st({"101": pr(author="ann")}),
               V + ["author"], "pr-view", '"author": {"login": "ann"}')
        unknown("pr view --json author: a fixture PR with no author — no viewer fallback",
                st(), V + ["author"], "author")
        unknown("pr list --json author: one PR without an author makes the list unanswerable",
                st({"101": pr(author="ann"), "102": pr(number=102, headRefName="feat/7")}),
                ["pr", "list", "--json", "number,author"], "author")
        d = tempfile.mkdtemp()
        try:
            stub(["pr", "create", "--head", "feat/7", "--base", "main", "--title", "t",
                  "--body", "b"], st(), cwd=work, state_dir=d)
            rc, out, err, j = stub(["pr", "view", "102", "--json", "author"], None, cwd=work,
                                   state_dir=d)
            rows.append(("pr view --json author: a PR created in this run carries its creator",
                         rc == 0 and '"author": {"login": "roz-gatekeeper"}' in out))
        finally:
            shutil.rmtree(d, ignore_errors=True)
        IV = ["issue", "view", "5", "--json"]
        unknown("issue view --json updatedAt: not derived from other timestamps", st(),
                IV + ["updatedAt"], "updatedAt")
        served("issue view --json updatedAt: the fixture states it",
               st(issues={"5": {"title": "x", "labels": [], "updatedAt": "2026-08-22T09:00:00Z"}}),
               IV + ["updatedAt"], "issue-view", '"updatedAt": "2026-08-22T09:00:00Z"')
        served("issue view --json stateReason,closedAt: an open issue", st(),
               IV + ["stateReason,closedAt"], "issue-view", '"stateReason": ""', '"closedAt": null')
        unknown("issue view --json stateReason: a closed issue whose fixture gives no reason",
                st(), ["issue", "view", "6", "--json", "stateReason"], "stateReason")
        served("issue view --json stateReason,closedAt: a closed issue that states them",
               st(issues={"6": {"title": "y", "labels": [], "state": "closed",
                                "stateReason": "COMPLETED", "closedAt": "2026-08-21T09:00:00Z"}}),
               ["issue", "view", "6", "--json", "stateReason,closedAt"], "issue-view",
               '"stateReason": "COMPLETED"', '"closedAt": "2026-08-21T09:00:00Z"')
        # codex review, PR #297 (second pass) — a stated fact is evidence about
        # the issue as seeded; once the run writes to the issue it is stale
        def after(writes, read, state):
            d = tempfile.mkdtemp()
            try:
                for w in writes:
                    stub(w, state, cwd=work, state_dir=d)
                rc, out, err, j = stub(read, state, cwd=work, state_dir=d)
                return rc, out, [e["route"] for e in j][-1], j[-1].get("note", "")
            finally:
                shutil.rmtree(d, ignore_errors=True)

        dated = st(issues={
            "5": {"title": "x", "labels": [], "updatedAt": "2026-08-22T09:00:00Z",
                  "comments": []},
            "9": {"title": "z", "labels": [], "updatedAt": "2026-08-22T09:00:00Z"}})
        for name, write in (
                ("an edit", ["issue", "edit", "5", "--add-label", "status: blocked"]),
                ("a comment", ["issue", "comment", "5", "--body", "hi"]),
                ("a close", ["issue", "close", "5"])):
            rc, out, route, note = after([write], IV + ["updatedAt"], dated)
            rows.append(("issue view --json updatedAt: stale after %s in this run → UNKNOWN"
                         % name, rc == 64 and out == "" and route == "UNKNOWN"
                         and "updatedAt" in note))
        rc, out, route, note = after([["issue", "edit", "9", "--add-label", "x"]],
                                     IV + ["updatedAt"], dated)
        rows.append(("issue view --json updatedAt: another issue's write leaves this one's",
                     rc == 0 and '"updatedAt": "2026-08-22T09:00:00Z"' in out))
        served("issue view --json stateReason: an open issue that states REOPENED keeps it",
               st(issues={"5": {"title": "x", "labels": [], "stateReason": "REOPENED"}}),
               IV + ["stateReason,closedAt"], "issue-view", '"stateReason": "REOPENED"',
               '"closedAt": null')
        rc, out, route, note = after(
            [["issue", "close", "5"]], IV + ["stateReason"],
            st(issues={"5": {"title": "x", "labels": [], "stateReason": "REOPENED"}}))
        rows.append(("issue view --json stateReason: closed in this run, the seeded reason "
                     "is not the answer → UNKNOWN",
                     rc == 64 and out == "" and route == "UNKNOWN" and "stateReason" in note))
        served("issue list --json number,closedAt: open issues", st(),
               ["issue", "list", "--json", "number,closedAt"], "issue-list", '"closedAt": null')
        served("repo view --json defaultBranchRef: the remote's HEAD", st(),
               ["repo", "view", "--json", "defaultBranchRef"], "repo-view",
               '"defaultBranchRef": {"name": "main"}')
        bare = tempfile.mkdtemp()    # not `tmp`: git would read ./origin.git as `origin`
        try:
            unknown("repo view --json defaultBranchRef: no remote to read it from", st(),
                    ["repo", "view", "--json", "defaultBranchRef"], "defaultBranchRef", cwd=bare)
            served("repo view --json defaultBranchRef: the fixture states it",
                   st(repo={"owner": "acme", "name": "demo", "default_branch": "trunk"}),
                   ["repo", "view", "--json", "defaultBranchRef"], "repo-view",
                   '"defaultBranchRef": {"name": "trunk"}', cwd=bare)
        finally:
            shutil.rmtree(bare, ignore_errors=True)
        # a field gh itself rejects: gh's error, scored — not UNKNOWN
        rc, out, err, j = stub(V + ["comments,reviewThreads"], st(), cwd=work)
        rows.append(("pr view --json comments,reviewThreads: gh's Unknown JSON field, exit 1",
                     rc == 1 and out == "" and 'Unknown JSON field: "reviewThreads"' in err
                     and [e["route"] for e in j] == ["json-field-rejected"]))
        rc, out, err, j = stub(["pr", "list", "--json", "number,reviewThreads"], st(), cwd=work)
        rows.append(("pr list --json reviewThreads: the same",
                     rc == 1 and out == "" and [e["route"] for e in j] == ["json-field-rejected"]))
        unknown("pr view --json bogus: a field nobody verified gh rejects stays UNKNOWN", st(),
                V + ["bogus"], "bogus")
        # a number with no pull request: gh's own answer
        rc, out, err, j = stub(["pr", "view", "5", "--json", "number,title"], st(), cwd=work)
        rows.append(("pr view <a number with no PR>: gh's GraphQL error, exit 1",
                     rc == 1 and out == "" and [e["route"] for e in j] == ["graphql-error"]
                     and "GraphQL: Could not resolve to a PullRequest with the number of 5. "
                         "(repository.pullRequest)" in err))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rows


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


def run_route(argv, cwd=None, env=None, state_dir=None, stdin="", state=None, notes=None):
    """One stub call against a throwaway state — or `state_dir`, kept
    between calls so a write can be read back. `env` overrides the
    inherited environment (the PATH-without-jq row, #219); `stdin` is
    what a `--body-file -` reads (empty by default, so no row can hang)."""
    d = state_dir or tempfile.mkdtemp()
    try:
        if not state_dir:
            with open(os.path.join(d, "state.json"), "w") as f:
                json.dump(state or STATE, f)
        p = subprocess.run([sys.executable, GH] + argv, capture_output=True, text=True,
                           env={**(env if env is not None else os.environ), "FORGE_STATE": d},
                           cwd=cwd, input=stdin)
        routes = [json.loads(line)["route"]
                  for line in open(os.path.join(d, "journal.jsonl")) if line.strip()]
        if notes is not None:   # the journal's notes, for a row that reads why
            notes.extend(json.loads(line).get("note", "")
                         for line in open(os.path.join(d, "journal.jsonl")) if line.strip())
        return p.returncode, p.stdout, routes
    finally:
        if not state_dir:
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
                     ("printf x > 'notes,old [v2].md' && git add -A && git commit -q -m seed "
                      "&& git checkout -q -b spec/5 "
                      "&& mkdir -p docs/specs/5 && echo '# Spec #5' > docs/specs/5/spec.md "
                      "&& echo '# Tech' > docs/specs/5/technical-spec.md && git add -A "
                      "&& git commit -qm spec && git checkout -q main "
                      "&& git remote add origin ../origin.git && git push -q origin --all", work)):
        subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env, check=True, capture_output=True)
    return tmp, work


# (name, argv, cwd kind, expected route, exit code, stdout needle)
REF_ROUTES = [
    # codex, PR #242: a file path is not an id — commas, quotes and brackets
    # are legal in a filename, so the malformed-segment rule stops at contents/
    ("contents of a file whose name carries a comma and brackets",
     ["api", "repos/acme/demo/contents/notes,old [v2].md", "--jq", ".path"],
     "work", "contents", 0, "notes,old [v2].md"),
    ("graphql: a PR's headRefOid, number in a variable",
     ["api", "graphql", "-f",
      "query=query($owner:String!,$repo:String!,$pr:Int!){ repository(owner:$owner,name:$repo)"
      "{ pullRequest(number:$pr){ headRefOid } } }",
      "-F", "owner=acme", "-F", "repo=demo", "-F", "pr=101",
      "--jq", ".data.repository.pullRequest.headRefOid"],
     "work", "graphql-pr-head", 0, None),
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
    # #219 — D13@B read the CR's changed files; the sandbox's base...head diff answers.
    ("pulls/<n>/files: the CR's changed files from base...head",
     ["api", "repos/acme/demo/pulls/101/files"], "work", "pr-files", 0,
     '"filename": "docs/specs/5/spec.md"'),
    ("pulls/<n>/files with --jq .[].filename", ["api", "repos/acme/demo/pulls/101/files",
                                                "--jq", ".[].filename"],
     "work", "pr-files", 0, "docs/specs/5/technical-spec.md"),
    ("pulls/<n>/files: absent number → UNKNOWN", ["api", "repos/acme/demo/pulls/999/files"],
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


# ---- EXPORT: a staged run dir ----------------------------------------------
T = ["2026-10-11T01:00:%02d.000Z" % i for i in range(13)]
TOOL_OUT = "## Development Workflow (Roz Gate)\nplain text tool output"
TRANSCRIPT = [
    {"type": "system", "subtype": "init", "session_id": "sess-x"},
    {"type": "assistant", "timestamp": T[1], "message": {
        "id": "m1", "model": "claude-test", "stop_reason": "tool_use",
        "usage": {"input_tokens": 2, "output_tokens": 9, "cache_read_input_tokens": 100,
                  "cache_creation_input_tokens": 50},
        "content": [{"type": "thinking", "thinking": "look first"},
                    {"type": "tool_use", "id": "tu-bash", "name": "Bash",
                     "input": {"command": "cat CLAUDE.md"}}]}},
    {"type": "user", "timestamp": T[2], "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "tu-bash", "content": TOOL_OUT}]}},
    {"type": "assistant", "timestamp": T[3], "message": {
        "id": "m2", "model": "claude-test", "stop_reason": "tool_use",
        "usage": {"input_tokens": 1, "output_tokens": 4, "cache_read_input_tokens": 150,
                  "cache_creation_input_tokens": 0},
        "content": [{"type": "tool_use", "id": "tu-agent", "name": "Agent",
                     "input": {"prompt": "do the sub-task"}}]}},
    # the sub-agent runs its own Bash (a forge write happens inside it)
    {"type": "assistant", "timestamp": T[4], "parent_tool_use_id": "tu-agent", "message": {
        "id": "m3", "model": "claude-test", "stop_reason": "tool_use",
        "usage": {"input_tokens": 3, "output_tokens": 2, "cache_read_input_tokens": 0,
                  "cache_creation_input_tokens": 10},
        "content": [{"type": "text", "text": "sub-agent says hi"},
                    {"type": "tool_use", "id": "tu-sub", "name": "Bash",
                     "input": {"command": "gh pr comment 101 --body hi"}}]}},
    {"type": "user", "timestamp": T[6], "parent_tool_use_id": "tu-agent", "message": {
        "role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "tu-sub", "content": "ok"}]}},
    {"type": "user", "timestamp": T[7], "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "tu-agent", "content": "sub-agent says hi"}]}},
    # the stream really arrives one event per content block, all sharing the
    # message id, with tool results interleaved: m2's second block lands
    # after the Agent's result, and m4 streams as two events
    {"type": "assistant", "timestamp": T[8], "message": {
        "id": "m2", "model": "claude-test", "stop_reason": None,
        "usage": {"input_tokens": 1, "output_tokens": 4, "cache_read_input_tokens": 150,
                  "cache_creation_input_tokens": 0},
        "content": [{"type": "text", "text": "after the agent"}]}},
    {"type": "assistant", "timestamp": T[9], "message": {
        "id": "m4", "model": "claude-test", "stop_reason": None,
        "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 160,
                  "cache_creation_input_tokens": 0},
        "content": [{"type": "thinking", "thinking": "wrap up"}]}},
    {"type": "assistant", "timestamp": T[10], "message": {
        "id": "m4", "model": "claude-test", "stop_reason": None,
        "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 160,
                  "cache_creation_input_tokens": 0},
        "content": [{"type": "text", "text": "done"}]}},
    # two Bash tools launched in parallel from one message: same start, and
    # both results land in one user message — their windows are identical
    {"type": "assistant", "timestamp": T[11], "message": {
        "id": "m5", "model": "claude-test", "stop_reason": "tool_use",
        "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 160,
                  "cache_creation_input_tokens": 0},
        "content": [{"type": "tool_use", "id": "tu-p1", "name": "Bash",
                     "input": {"command": "gh issue close 5"}},
                    {"type": "tool_use", "id": "tu-p2", "name": "Bash",
                     "input": {"command": "gh issue view 6"}}]}},
    {"type": "user", "timestamp": T[12], "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "tu-p1", "content": "closed"},
        {"type": "tool_result", "tool_use_id": "tu-p2", "content": "{}"}]}},
    {"type": "result", "subtype": "success", "session_id": "sess-x", "duration_ms": 6000,
     "num_turns": 5, "total_cost_usd": 0.5, "result": "done"},
]


def epoch(stamp, plus=0.0):
    return ex.ts_ns(stamp) / 1e9 + plus


# One write without a clock (a run from before #190), one stamped inside the
# main Bash, one inside the sub-agent's Bash (also inside the Agent span:
# the innermost wins), one inside the two parallel Bash tools' shared
# window, one stamped after the transcript's end.
JOURNAL = [{"route": "issue-view", "write": False, "argv": ["issue", "view", "5"]},
           {"route": "issue-comment", "write": True, "argv": ["issue", "comment", "5"],
            "body": "**[gate] hello"},
           {"route": "issue-edit", "write": True, "argv": ["issue", "edit", "5"],
            "ts": epoch(T[1], 0.5)},
           {"route": "pr-comment", "write": True, "argv": ["pr", "comment", "101"],
            "body": "hi", "ts": epoch(T[5])},
           {"route": "issue-close", "write": True, "argv": ["issue", "close", "5"],
            "ts": epoch(T[11], 0.5)},
           {"route": "thread-resolve", "write": True, "argv": ["api", "graphql"],
            "ts": epoch(T[12], 30)}]
CHECK_LOG = "ok   a claim that held\nFAIL a claim that did not  [source: ledger X]\n"
RESULT = {"valid": True, "pass": False, "tokens": {"in": 7, "out": 16}, "cost": {"usd": 0.5}}


def stage_run(case="X", result=RESULT):
    d = tempfile.mkdtemp()
    rdir = os.path.join(d, "report", "sut", case, "run-1")
    os.makedirs(os.path.join(rdir, "forge"))
    with open(os.path.join(rdir, "transcript.jsonl"), "w") as f:
        f.write("".join(json.dumps(e) + "\n" for e in TRANSCRIPT))
    with open(os.path.join(rdir, "forge", "journal.jsonl"), "w") as f:
        f.write("".join(json.dumps(e) + "\n" for e in JOURNAL))
    with open(os.path.join(rdir, "check.log"), "w") as f:
        f.write(CHECK_LOG)
    with open(os.path.join(rdir, "result.json"), "w") as f:
        json.dump(result, f)
    return d, rdir


def _marker_refused():
    d, rdir = stage_run()
    try:
        with open(os.path.join(rdir, ex.MARKER), "w") as f:
            json.dump({"trace_id": "x", "url": "http://nowhere"}, f)
        cfg = {"LANGFUSE_HOST": "http://127.0.0.1:9", "LANGFUSE_PUBLIC_KEY": "pk",
               "LANGFUSE_SECRET_KEY": "sk"}   # a dead port: any send would fail loudly
        try:
            ex.export_run(rdir, "X", "sut", "1", "p", cfg)
            return False
        except ex.AlreadyExported:
            return True
        except ex.ExportError:
            return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _marker_pending():
    """(pending after a failed send, refused as partial, done after --force)."""
    d, rdir = stage_run()
    real_post = ex.post
    cfg = {"LANGFUSE_HOST": "http://127.0.0.1:9", "LANGFUSE_PUBLIC_KEY": "pk",
           "LANGFUSE_SECRET_KEY": "sk"}
    calls = []

    def failing_post(cfg, path, body):   # the traces go in, the first score is refused
        calls.append(path)
        if path != "/api/public/otel/v1/traces":
            raise ex.ExportError("%s → HTTP 500" % path)

    try:
        ex.post = failing_post
        try:
            ex.export_run(rdir, "X", "sut", "1", "p", cfg)
            return (False, False, False)
        except ex.AlreadyExported:
            return (False, False, False)
        except ex.ExportError:
            pass
        after_fail = ex.exported(rdir) or {}
        pending = (after_fail.get("status") == "pending" and after_fail.get("name") == "X/run-1"
                   and "/api/public/otel/v1/traces" in calls)
        ex.post = lambda cfg, path, body: None
        try:
            ex.export_run(rdir, "X", "sut", "1", "p", cfg)
            refused = False
        except ex.AlreadyExported as e:
            refused = "partial" in str(e) and "--force" in str(e)
        s = ex.export_run(rdir, "X", "sut", "1", "p", cfg, force=True)
        done = s.get("status") == "done" and (ex.exported(rdir) or {}).get("status") == "done"
        return (pending, refused, done)
    finally:
        ex.post = real_post
        shutil.rmtree(d, ignore_errors=True)


def _journal_has_clock():
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(STATE, f)
        subprocess.run([sys.executable, GH, "issue", "view", "5", "--json", "title"],
                       capture_output=True, text=True, env={**os.environ, "FORGE_STATE": d})
        entries = [json.loads(line) for line in open(os.path.join(d, "journal.jsonl"))
                   if line.strip()]
        return bool(entries) and all(isinstance(e.get("ts"), float) and e["ts"] > 1.7e9
                                     for e in entries)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def attrs(s):
    out = {}
    for a in s["attributes"]:
        v = a["value"]
        out[a["key"]] = (v.get("stringValue") if "stringValue" in v else
                         [x.get("stringValue") for x in v["arrayValue"]["values"]]
                         if "arrayValue" in v else v.get("intValue", v.get("boolValue")))
    return out


def _fingerprint_meta():
    """(a current fp is not stale; a differing one is tagged stale; plugin_sha
    comes from result.json even on a backfill) — built against a real case
    dir (C5), read only."""
    cdir = os.path.join(HERE, "cases", "C5")
    current = rl.case_fingerprint(cdir)
    out = []
    for fp, sha in ((current, "abc1234"), ("0000000000000000", "")):
        d, rdir = stage_run("C5", {**RESULT, "case_fp": fp, **({"plugin_sha": sha} if sha else {})})
        try:
            root = ex.build(rdir, "C5", "sut", "1", "p", backfilled=True)[0][0]
        finally:
            shutil.rmtree(d, ignore_errors=True)
        out.append(attrs(root))
    cur, old = out
    return (cur.get("langfuse.trace.metadata.case_fp") == current
            and cur.get("langfuse.trace.metadata.stale") is False
            and cur.get("langfuse.trace.tags") == ["C5", "sut", "fail"]
            and cur.get("langfuse.trace.metadata.plugin_sha") == "abc1234"
            and old.get("langfuse.trace.metadata.stale") is True
            and old.get("langfuse.trace.tags") == ["C5", "sut", "fail", "stale"]
            and "langfuse.trace.metadata.plugin_sha" not in old)


# (name, result.json files by run, expected row fields) — staged under a real
# case dir's name (C5) so aggregate() has a current fingerprint to compare.
def _aggregate(results, key="C5"):
    d = tempfile.mkdtemp()
    try:
        report = os.path.join(d, "sut")
        for i, r in enumerate(results, 1):
            run = os.path.join(report, key, "run-%d" % i)
            os.makedirs(run)
            with open(os.path.join(run, "result.json"), "w") as f:
                json.dump(r, f)
        with contextlib.redirect_stdout(io.StringIO()):
            rr.aggregate({"name": "sut", "model": "m", "mode": "subscription"}, report)
        rows = json.load(open(os.path.join(report, "report.json")))["cases"]
        return next((r for r in rows if r["case"] == key), None)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def fingerprint_checks():
    current = rl.case_fingerprint(os.path.join(HERE, "cases", "C5"))
    ok = {"valid": True, "pass": True, "tokens": {"in": 1, "out": 1}}
    ko = {**ok, "pass": False}
    mixed = _aggregate([{**ok, "case_fp": current}, {**ko, "case_fp": current},
                        {**ok, "case_fp": "0000000000000000"}, ok,
                        {"valid": False, "invalid_reason": "x", "case_fp": "0000000000000000"}])
    all_stale = _aggregate([{**ok, "case_fp": "0000000000000000"},
                            {**ok, "case_fp": "1111111111111111"}])
    return [
        ("a stale run is counted and left out of the rate; an unknown one is counted and in",
         mixed is not None and mixed["runs"] == 3 and mixed["passes"] == 2
         and mixed.get("stale") == 2 and mixed.get("unknown") == 1 and mixed["invalid"] == 0
         and mixed["rate"] == round(2 / 3, 3)),
        ("a case whose runs are all stale reports no rate, and says why",
         all_stale is not None and all_stale["rate"] is None and all_stale["runs"] == 0
         and all_stale.get("stale") == 2
         and all_stale["note"] == "unavailable — every iteration is stale under the current case"),
        ("the fingerprint moves with the checker, the metadata, the seed and the state",
         _fingerprint_moves()),
        ("every journal entry the stub writes carries its clock", _journal_has_clock()),
    ]


def _fingerprint_moves():
    base = {"check.py": "c", "case.json": "{}", "seed.sh": "s", "state.json": "{}"}
    d = tempfile.mkdtemp()
    try:
        def fp(files):
            for n in os.listdir(d):
                os.remove(os.path.join(d, n))
            for n, text in files.items():
                with open(os.path.join(d, n), "w") as f:
                    f.write(text)
            return rl.case_fingerprint(d)
        ref = fp(base)
        changed = [fp({**base, n: base[n] + "x"}) for n in base]
        absent = fp({k: v for k, v in base.items() if k != "seed.sh"})
        driver = fp({**base, "case.json": '{"driver": "drive.py"}', "drive.py": "d"})
        driver2 = fp({**base, "case.json": '{"driver": "drive.py"}', "drive.py": "dd"})
        return (fp(base) == ref and len(ref) == 16 and all(c != ref for c in changed)
                and len(set(changed)) == 4 and absent != ref and driver != driver2)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _score(check_src):
    """rr.score() on a staged case dir whose check.py is `check_src`."""
    d = tempfile.mkdtemp()
    try:
        cdir, rdir = os.path.join(d, "case"), os.path.join(d, "run")
        os.makedirs(cdir)
        os.makedirs(rdir)
        with open(os.path.join(cdir, "check.py"), "w") as f:
            f.write(check_src)
        return rr.score(cdir, rdir, d, d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _fixture_fingerprint_moves():
    """A case naming a fixture tree hashes its files: a change under fx/ moves
    the fingerprint; an unnamed tree does not."""
    d = tempfile.mkdtemp(dir=rr.S)
    try:
        cdir = os.path.join(d, "case")
        fx = os.path.join(d, "fx-x")
        os.makedirs(cdir)
        os.makedirs(fx)
        rel = os.path.relpath(fx, rr.S)
        for n, text in (("check.py", "c"), ("seed.sh", "s"), ("state.json", "{}")):
            with open(os.path.join(cdir, n), "w") as f:
                f.write(text)
        with open(os.path.join(cdir, "case.json"), "w") as f:
            json.dump({"fixture": rel}, f)
        with open(os.path.join(fx, "a.py"), "w") as f:
            f.write("x = 1\n")
        before = rl.case_fingerprint(cdir)
        with open(os.path.join(fx, "a.py"), "w") as f:
            f.write("x = 2\n")
        after = rl.case_fingerprint(cdir)
        with open(os.path.join(cdir, "case.json"), "w") as f:
            json.dump({}, f)
        unnamed = rl.case_fingerprint(cdir)
        with open(os.path.join(fx, "a.py"), "w") as f:
            f.write("x = 3\n")
        unnamed_still = rl.case_fingerprint(cdir)
        # the list form: a tree and a single shared file (codex review, PR #217)
        shared = os.path.join(d, "frame.py")
        with open(shared, "w") as f:
            f.write("v = 1\n")
        with open(os.path.join(cdir, "case.json"), "w") as f:
            json.dump({"fixture": [rel, os.path.relpath(shared, rr.S)]}, f)
        listed = rl.case_fingerprint(cdir)
        with open(shared, "w") as f:
            f.write("v = 2\n")
        listed_after = rl.case_fingerprint(cdir)
        return (before != after and unnamed == unnamed_still and listed != listed_after
                and listed != after)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def variant_checks():
    plugin = rr.variant_plugin("B")
    diff = rr.variant_diff(plugin)
    b_hash = rl.brief_sha256(os.path.join(rr.VARIANTS, "B.md"))
    a_hash = rl.brief_sha256(os.path.join(rr.ROOT, rr.BRIEF_REL))
    c5 = os.path.join(HERE, "cases", "C5")
    stamp_b = rr.case_stamp(c5, "B", plugin)
    stamp_a = rr.case_stamp(c5)
    current = rl.case_fingerprint(c5)
    ok = {"valid": True, "pass": True, "tokens": {"in": 1, "out": 1}, "case_fp": current}
    row = _aggregate([{**ok, "brief_sha256": b_hash, "variant": "B"},
                      {**ok, "pass": False, "brief_sha256": "0" * 64, "variant": "B"},
                      {**ok, "variant": "B"}], key="C5@B")
    row_a = _aggregate([{**ok, "brief_sha256": a_hash}, {**ok, "brief_sha256": "0" * 64}])
    row_sig = _aggregate([{**ok, "brief_sha256": b_hash, "variant": "B", "suite_pushed": 1,
                           "attempts_denied": 2, "signals": ["attempts_denied", "suite_pushed"]}],
                         key="C5@B")
    # #290 — a result as the 2026-11-12 sweep left it on disk: a shadow
    # count AND its detail dict, both listed in `signals`. aggregate() must
    # return the count's column and never try to sum the dict.
    def _safe(fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — the crash is the defect under test
            return "RAISED %s" % type(e).__name__
    row_detail = _safe(lambda: _aggregate(
        [{**ok, "brief_sha256": a_hash, "shadow_state_mismatch": 1,
          "shadow_state_detail": {"qa.cr": ["absent", "observed"]},
          "signals": ["shadow_state_detail", "shadow_state_mismatch"]},
         {**ok, "brief_sha256": a_hash, "shadow_state_mismatch": 2,
          "shadow_state_detail": {}, "signals": ["shadow_state_detail", "shadow_state_mismatch"]}]))
    split = _safe(lambda: rr.split_attempts(
        {"attempts_denied": 2, "shadow_branch_detail": {"spec": "x"}, "rows": [1, 2],
         "flag": True, "ratio": 0.5, "note": "text", "zero": 0}))
    inv = _score("import sys\nprint('INVALID the brief was never exercised')\nsys.exit(3)\n")
    return [
        ("#290 a detail dict listed beside a count aggregates: the count is summed, the "
         "dict is not a column",
         isinstance(row_detail, dict) and row_detail.get("shadow_state_mismatch") == 3
         and "shadow_state_detail" not in row_detail),
        ("#290 only an int is a signal — a dict, a list, a bool, a float and a string are "
         "details",
         split == (["attempts_denied", "zero"],
                   ["flag", "note", "ratio", "rows", "shadow_branch_detail"])),
        ("the variant plugin copy differs from the checkout in exactly references/qa-brief.md",
         plugin != rr.ROOT and diff == [rr.BRIEF_REL]),
        ("the copy's brief is the variant file, hash for hash; A is the checkout itself",
         rl.brief_sha256(os.path.join(plugin, rr.BRIEF_REL)) == b_hash != a_hash
         and rr.variant_plugin("A") == rr.ROOT),
        ("the stamp carries the variant and the hash read back from the plugin dir",
         stamp_b["variant"] == "B" and stamp_b["brief_sha256"] == b_hash
         and stamp_a["variant"] == "A" and stamp_a["brief_sha256"] == a_hash
         and {"case_fp", "plugin_sha"} <= set(stamp_b)),
        ("a <case>@<V> report dir scores under its case with the variant named; a run whose brief "
         "hash differs is stale and out of the rate; one without a hash stays in",
         row is not None and row.get("variant") == "B" and row["runs"] == 2
         and row["passes"] == 2 and row.get("stale") == 1 and row["rate"] == 1.0),
        ("A's runs are measured against the checkout's brief: an old hash is stale",
         row_a is not None and row_a.get("variant") == "A" and row_a["runs"] == 1
         and row_a.get("stale") == 1),
        ("a row with signal columns keeps its case key (codex review, PR #217)",
         row_sig is not None and row_sig["case"] == "C5@B" and row_sig.get("variant") == "B"
         and row_sig.get("attempts_denied") == 2 and row_sig.get("suite_pushed") == 1),
        ("a checker's exit 3 is an invalid iteration carrying its INVALID line, never a FAIL",
         inv == ("invalid", "checker: the brief was never exercised")
         and _score("import sys\nsys.exit(0)\n") == ("pass", None)
         and _score("import sys\nsys.exit(1)\n") == ("fail", None)),
        ("the fingerprint follows a case's fixture tree and every listed shared file",
         _fixture_fingerprint_moves()),
        ("the report key splits into case and variant; a plain key is A",
         rr.split_key("D10@B") == ("D10", "B") and rr.split_key("D10") == ("D10", "A")
         and rr.case_key("D10", "A") == "D10" and rr.case_key("D10", "C") == "D10@C"),
    ]


def export_checks():
    """(name, ok) over the staged run's build() output."""
    d, rdir = stage_run()
    try:
        spans, scores, summary = ex.build(rdir, "X", "sut", "1", "the prompt")
        again = ex.build(rdir, "X", "sut", "1", "the prompt")[0]
        backfilled_root = ex.build(rdir, "X", "sut", "1", "the prompt", backfilled=True)[0][0]
    finally:
        shutil.rmtree(d, ignore_errors=True)

    by_type = {}
    for s in spans:
        by_type.setdefault(attrs(s).get("langfuse.observation.type"), []).append(s)
    root = spans[0]
    ra = attrs(root)
    gens = by_type.get("generation", [])
    tools = {attrs(s)["langfuse.observation.metadata.tool_use_id"]: s
             for s in by_type.get("tool", [])}
    bash, agent, sub_bash = tools.get("tu-bash"), tools.get("tu-agent"), tools.get("tu-sub")
    events = {s["name"]: s for s in by_type.get("event", [])}
    pending, refused, done = _marker_pending()
    sub = [g for g in gens if attrs(g).get("langfuse.observation.metadata.message_id") == "m3"]
    m4 = [g for g in gens if attrs(g).get("langfuse.observation.metadata.message_id") == "m4"]
    m2 = [g for g in gens if attrs(g).get("langfuse.observation.metadata.message_id") == "m2"]
    m1 = [g for g in gens if attrs(g).get("langfuse.observation.metadata.message_id") == "m1"]
    usage_ok = all(set(json.loads(attrs(g)["langfuse.observation.usage_details"]))
                   >= {"input", "output", "cache_read_input_tokens",
                       "cache_creation_input_tokens"} for g in gens)
    names = [sc["name"] for sc in scores]
    return [
        ("one root span named after the run, in the case's session, tagged with the verdict",
         root["name"] == "X/run-1" and "parentSpanId" not in root
         and ra.get("langfuse.session.id") == "sut/X"
         and ra.get("langfuse.trace.tags") == ["X", "sut", "fail"]
         and ra.get("langfuse.trace.input") == "the prompt"
         and ra.get("langfuse.trace.output") == "done"),
        ("a generation per API call (the sub-agent's too), each carrying usage with the "
         "cache keys",
         len(gens) == 5 and usage_ok and summary["generations"] == 5),
        ("two events sharing a message id are one generation: both blocks, the later end",
         len(m4) == 1 and attrs(m4[0]).get("langfuse.observation.output")
         == json.dumps([{"type": "thinking", "thinking": "wrap up"},
                        {"type": "text", "text": "done"}], ensure_ascii=False)
         and m4[0]["endTimeUnixNano"] == str(ex.ts_ns(T[10]))),
        ("a block arriving after an interleaved tool result still joins its API call",
         len(m2) == 1 and "after the agent" in attrs(m2[0]).get("langfuse.observation.output", "")
         and m2[0]["endTimeUnixNano"] == str(ex.ts_ns(T[8]))),
        ("a run dir already exported is refused before any network, unless forced",
         _marker_refused()),
        ("a send that fails after its first post leaves the marker pending",
         pending),
        ("a pending run dir is refused as a partial export, naming --force", refused),
        ("--force on a pending run dir sends again and marks it done", done),
        ("the first call's input is the case prompt; a sub-agent's first call's input is "
         "its Agent tool's input",
         len(m1) == 1 and attrs(m1[0]).get("langfuse.observation.input") == "the prompt"
         and len(sub) == 1 and attrs(sub[0]).get("langfuse.observation.input")
         == json.dumps({"prompt": "do the sub-task"}, ensure_ascii=False)),
        ("a backfill carries no plugin_sha unless result.json recorded one",
         "langfuse.trace.metadata.plugin_sha" not in attrs(backfilled_root)
         and attrs(backfilled_root).get("langfuse.trace.metadata.backfilled") is True),
        ("the run's case_fp and plugin_sha come from result.json; a fingerprint that differs "
         "from the current case tags the trace stale", _fingerprint_meta()),
        ("the Bash span's output is its tool_result and it ends at that user message",
         bash is not None and attrs(bash).get("langfuse.observation.output") == TOOL_OUT
         and bash["endTimeUnixNano"] == str(ex.ts_ns(T[2]))),
        ("the sub-agent's generation nests under the Agent span",
         agent is not None and len(sub) == 1 and sub[0].get("parentSpanId") == agent["spanId"]),
        ("every span starts no later than it ends",
         all(int(s["startTimeUnixNano"]) <= int(s["endTimeUnixNano"]) for s in spans)),
        ("journal writes are events, reads are not",
         len(events) == 5 and set(events) == {"journal:issue-comment", "journal:issue-edit",
                                              "journal:pr-comment", "journal:issue-close",
                                              "journal:thread-resolve"}),
        ("a write inside the window two parallel tools share goes under their parent, at "
         "its time — never under whichever came first",
         {"tu-p1", "tu-p2"} <= set(tools)
         and tools["tu-p1"]["startTimeUnixNano"] == tools["tu-p2"]["startTimeUnixNano"]
         and tools["tu-p1"]["endTimeUnixNano"] == tools["tu-p2"]["endTimeUnixNano"]
         and events["journal:issue-close"].get("parentSpanId") == root["spanId"]
         and events["journal:issue-close"]["startTimeUnixNano"]
         == str(ex.ts_ns(T[11]) + 500 * 10**6)),
        ("a write stamped inside a tool call nests under that call, at its time",
         bash is not None and events["journal:issue-edit"].get("parentSpanId") == bash["spanId"]
         and events["journal:issue-edit"]["startTimeUnixNano"]
         == str(ex.ts_ns(T[1]) + 500 * 10**6)),
        ("a write stamped inside a sub-agent's Bash nests under that Bash, not the Agent",
         sub_bash is not None and sub_bash.get("parentSpanId") == agent["spanId"]
         and events["journal:pr-comment"].get("parentSpanId") == sub_bash["spanId"]),
        ("a write without a clock, or stamped outside every tool call, sits under the root "
         "after the transcript's end",
         all(events[n].get("parentSpanId") == root["spanId"]
             and int(events[n]["startTimeUnixNano"]) > ex.ts_ns(T[12])
             for n in ("journal:issue-comment", "journal:thread-resolve"))
         and int(root["endTimeUnixNano"])
         >= int(events["journal:thread-resolve"]["startTimeUnixNano"])),
        ("scores: pass, valid, cost_usd and one per claim, with the FAIL's source",
         names == ["pass", "valid", "cost_usd", "a claim that held", "a claim that did not"]
         and [sc["value"] for sc in scores] == [0, 1, 0.5, 1, 0]
         and scores[-1]["comment"] == "source: ledger X"),
        ("ids are deterministic — a second build is byte-identical",
         json.dumps(again) == json.dumps(spans)),
    ]


def persona_checks():
    """#267: the QA persona is the seat's system prompt; a run under another
    persona is a measurement of another seat — stale, exactly like a run
    under another brief, but only for a case that declares it dispatches the
    QA seat (`"seats": ["qa"]`), so a persona edit leaves other cases alone."""
    persona_rel = getattr(rr, "PERSONA_REL", "agents/qa.md")
    now = rl.brief_sha256(os.path.join(rr.ROOT, persona_rel))
    old = "0" * 64
    seat, other = os.path.join(HERE, "cases", "D18"), os.path.join(HERE, "cases", "C5")
    seat_ok = {"valid": True, "pass": True, "tokens": {"in": 1, "out": 1},
               "case_fp": rl.case_fingerprint(seat)}
    other_ok = {**seat_ok, "case_fp": rl.case_fingerprint(other)}
    row_seat = _aggregate([{**seat_ok, "persona_sha256": now},
                           {**seat_ok, "pass": False, "persona_sha256": old},
                           {**seat_ok}], key="D18")
    row_other = _aggregate([{**other_ok, "persona_sha256": old}], key="C5")
    # a plugin dir whose persona differs from the checkout's: the stamp must
    # read the dir the session ran, never the checkout
    plugin = tempfile.mkdtemp()
    try:
        for rel, body in ((rr.BRIEF_REL, b"brief\n"), (persona_rel, b"another persona\n")):
            os.makedirs(os.path.dirname(os.path.join(plugin, rel)), exist_ok=True)
            with open(os.path.join(plugin, rel), "wb") as f:
                f.write(body)
        stamp_b, stamp_a = rr.case_stamp(other, "B", plugin), rr.case_stamp(other)
        theirs = rl.brief_sha256(os.path.join(plugin, persona_rel))
    finally:
        shutil.rmtree(plugin, ignore_errors=True)
    seats = json.load(open(os.path.join(seat, "case.json"))).get("seats")
    return [
        ("a QA-seat case declares it: D18's case.json carries \"seats\": [\"qa\"]",
         seats == ["qa"]),
        ("a seat case's run under another persona hash is stale and out of the rate; the current "
         "hash scores; a run without the field stays in (the case_fp precedent, #190)",
         row_seat is not None and row_seat["runs"] == 2 and row_seat["passes"] == 2
         and row_seat.get("stale") == 1),
        ("a case that never dispatches the QA seat scores a run under another persona",
         row_other is not None and row_other["runs"] == 1 and not row_other.get("stale")),
        ("the stamp carries the persona hash read back from the plugin dir the session ran",
         stamp_b.get("persona_sha256") == theirs != now
         and stamp_a.get("persona_sha256") == now),
    ]


def _seed_run(cdir):
    """(sandbox dir, Run, template) for a case's seeded state — no SUT."""
    sbx, bare = rl.seed_sandbox(cdir)       # with a git identity: CI runners have none
    if not sbx:
        return None, None, None
    work = os.path.join(sbx, "work")
    rdir = os.path.join(sbx, "run")
    os.makedirs(os.path.join(rdir, "forge"))
    shutil.copy(os.path.join(cdir, "state.json"), os.path.join(rdir, "forge", "state.json"))
    run = rl.Run(rdir)
    run.bare = bare
    template = None
    try:
        with open(os.path.join(work, ".claude", "roz-gate.local.json"), encoding="utf-8") as f:
            template = (json.load(f).get("branch_template") or None)
    except (OSError, ValueError):
        pass
    return sbx, run, template


STATE_MATRIX = ("a missing CR", "an open CR", "a draft CR", "a merged CR",
                "a merged CR whose head branch was deleted", "a re-spec ({seq} > 1)",
                "an implementation CR on the current spec branch",
                "an implementation CR on another base", "zero review threads",
                "no audit marker on a QA CR", "a completed clean audit", "one open dependency",
                "several dependencies", "an unavailable forge observation")


def _cells(truth, state, shas, n, template):
    """The cells of references/roz-state.md's scenario matrix a truth hits."""
    f, out = truth.get("facts") or {}, set()
    crs = [f.get(k) for k in ("spec.cr", "implementation.cr", "qa.cr")]
    for st, v in [c for c in crs if c]:
        if st == "absent":
            out.add("a missing CR")
        elif st == "observed":
            out.add("a draft CR" if v["state"] == "open" and v["draft"] else
                    "an open CR" if v["state"] == "open" else
                    "a merged CR" if v["state"] == "merged" else "a closed CR")
    for b, cr in (("branches.spec", "spec.cr"), ("branches.implementation", "implementation.cr"),
                  ("branches.qa", "qa.cr")):
        if f.get(b, (None,))[0] == "absent" and f.get(cr, (None,))[0] == "observed":
            out.add("a merged CR whose head branch was deleted")
    spec = f.get("branches.spec", (None, None))
    if spec[0] == "observed":
        import branch_names as bn
        m = bn.match_heads(bn.snapshot_from_heads(shas), template, kind="spec", n=str(n))
        if m["outcome"] == "MULTIPLE_SEQ":
            out.add("a re-spec ({seq} > 1)")
        impl = f.get("implementation.cr", (None, None))
        if impl[0] == "observed":
            out.add("an implementation CR on the current spec branch"
                    if impl[1]["base"] == spec[1]["name"] else
                    "an implementation CR on another base")
    if f.get("implementation.open_review_threads") == ("observed", 0):
        out.add("zero review threads")
    if f.get("qa.cr", (None,))[0] == "observed":
        mk, th = f["qa.fidelity_marker"], f["qa.open_fidelity_threads"]
        if mk[0] == "absent":
            out.add("no audit marker on a QA CR")
        elif mk[0] == "observed" and th == ("observed", 0):
            out.add("a completed clean audit")
    dep = f.get("dependencies.blocked_by", (None, None))
    if dep[0] == "unknown":
        out.add("an unavailable forge observation")
    elif dep[0] == "observed":
        opens = [b for b in dep[1] if b["state"] == "open"]
        if len(dep[1]) > 1:
            out.add("several dependencies")
        if len(opens) == 1:
            out.add("one open dependency")
    return out


def state_checks():
    """#133: bin/roz-state in shadow. (1) the seed sweep — for every replay
    case's seeded forge state and every issue in it, the collector against
    stub truth, no model call; (2) shadow_state and (3) shadow_scan
    discriminate: they agree on a faithful snapshot and count exactly the
    fact that was changed — and nothing in a column that is the scanner's
    interpretation."""
    sys.path.insert(0, os.path.join(rr.ROOT, "hooks"))
    cases = sorted(d for d in os.listdir(os.path.join(HERE, "cases"))
                   if os.path.exists(os.path.join(HERE, "cases", d, "state.json")))
    issues, bad, invalid, hit, where = 0, [], [], set(), {}
    calls, writes = 0, []
    for cid in cases:
        cdir = os.path.join(HERE, "cases", cid)
        sbx, run, template = _seed_run(cdir)
        if not sbx:
            bad.append("%s: seed failed" % cid)
            continue
        try:
            state, shas = run.state(), run.remote_shas()
            for n in sorted(state.get("issues") or {}, key=int):
                issues += 1
                rc, obj = run.roz_state(n, template)
                calls += len(run.state_journal)
                writes += ["%s#%s %s" % (cid, n, e.get("route")) for e in run.state_journal
                           if e.get("write") or e.get("route") == "UNKNOWN"]
                truth = rl.state_truth(state, shas, n, template)
                import state_contract as sc
                errs = (sc.validate(obj) if rc == 0 else sc.validate_failure(obj) if rc == 2
                        else ["exit %s" % rc])
                if errs:
                    invalid.append("%s#%s: %s" % (cid, n, errs[0]))
                    continue
                for d in rl.state_diff(obj, truth):
                    bad.append("%s#%s %s" % (cid, n, d))
                for cell in _cells(truth, state, shas, n, template):
                    hit.add(cell)
                    where.setdefault(cell, []).append("%s#%s" % (cid, n))
        finally:
            shutil.rmtree(sbx, ignore_errors=True)
    for cell in STATE_MATRIX:
        print("NOTE  state matrix: %-48s %s" % (cell, ", ".join(where.get(cell, [])[:6])
                                                 or "UNCOVERED by any seed"))
    checks = [
        ("seed sweep: %d issues over %d case seeds — every roz-state output is a valid "
         "snapshot or a typed failure (%s)" % (issues, len(cases), "; ".join(invalid[:3]) or "ok"),
         issues > 0 and not invalid),
        ("seed sweep: roz-state equals stub truth on every fact (%s)"
         % ("; ".join(bad[:4]) or "0 mismatches"), issues > 0 and not bad),
        ("seed sweep: the forge stub journalled %d calls from roz-state — every one a read on a "
         "known route (%s)" % (calls, "; ".join(writes[:4]) or "no write, no UNKNOWN"),
         calls > 0 and not writes),
    ]

    # (2) and (3) on one seed with a CR, threads and a scanner-shaped row
    cdir = os.path.join(HERE, "cases", "F9")
    sbx, run, template = _seed_run(cdir)
    try:
        real = {}

        def collect(n, tpl):
            if n not in real:
                real[n] = run.roz_state(n, tpl)
            return real[n][0], json.loads(json.dumps(real[n][1]))

        def doctored(change):
            def f(n, tpl):
                rc, obj = collect(n, tpl)
                change(obj)
                return rc, obj
            return f

        def sig(key):
            with open(os.path.join(run.dir, "attempts.json"), encoding="utf-8") as fh:
                return json.load(fh).get(key)

        run.shadow_state(["5"], template, _collect=collect)
        agree = (sig("shadow_state_mismatch"), sig("shadow_state_invalid"))
        run.shadow_state(["5"], template, _collect=doctored(
            lambda o: o["spec"]["cr"]["value"].update(state="merged")))
        one = (sig("shadow_state_mismatch"), sig("shadow_state_invalid"))
        run.shadow_state(["5"], template, _collect=doctored(
            lambda o: o["dependencies"].update(blocked_by=0)))
        inv = (sig("shadow_state_mismatch"), sig("shadow_state_invalid"))
        run.shadow_state(["5"], template, _collect=doctored(lambda o: o.update(status="in-dev")))
        plain = sig("shadow_state_mismatch")
        checks += [
            ("shadow_state agrees on a faithful snapshot (0 mismatches, 0 invalid)",
             agree == (0, 0)),
            ("shadow_state counts exactly the one fact changed (a CR state)", one == (1, 0)),
            ("shadow_state counts a contract-invalid snapshot as invalid, not as a mismatch",
             inv == (0, 1)),
            ("shadow_state compares the plain values too (status)", plain == 1),
        ]

        row = ("| #5 Offer expiry | spec | `status: in-user-review` | paul | #101 open %s "
               "| 1 | %s | %s |")
        url = "https://github.com/acme/demo/pull/101"

        def scan(cells_row):
            run.shadow_scan(["5"], cdir, template,
                            table="| issue | track |\n|---|---|\n" + cells_row, _collect=collect)
            return sig("shadow_scan_mismatch"), sig("shadow_scan_rows")
        ok = scan(row % (url, "hand-off: in-user-review", "thread url"))
        verdict = scan(row % (url, "waiting on: #9, #12", "blockers unknown (HTTP 404)"))
        st = scan(row.replace("in-user-review` |", "in-dev` |", 1)
                  % (url, "hand-off: in-user-review", "x"))
        tr = scan(row.replace("| spec |", "| fast |") % (url, "hand-off: in-user-review", "x"))
        crn = scan(row.replace("#101 open", "#999 open") % (url, "hand-off: in-user-review", "x"))
        crs = scan(row.replace("#101 open", "#101 merged") % (url, "hand-off: in-user-review", "x"))
        none = scan(row.replace("#101 open %s", "none%s") % ("", "hand-off: in-user-review", "x"))
        gone = scan("| #7 other | — | — | paul | none | 0 | intake | x |")
        checks += [
            ("shadow_scan agrees on a row whose track, status and cr match the snapshot",
             ok == (0, 1)),
            ("shadow_scan ignores the scanner's interpretation: another verdict, a `waiting on`, "
             "other evidence change nothing", verdict == (0, 1)),
            ("shadow_scan counts a differing status", st == (1, 1)),
            ("shadow_scan counts a differing track", tr == (1, 1)),
            ("shadow_scan counts a CR number the snapshot does not have", crn == (1, 1)),
            ("shadow_scan counts a CR state that differs", crs == (1, 1)),
            ("shadow_scan counts `none` against an open CR", none == (1, 1)),
            ("shadow_scan compares no row it was not given (0 rows, 0 mismatches)",
             gone == (0, 0)),
        ]

        # the scan's moment, not the run's end (codex review, PR #273): after a
        # faithful table the pass takes the lock on #5 — the final state says
        # `processing`, the table (rightly) does not
        faithful = "| issue |\n|---|\n" + row % (url, "hand-off: in-user-review", "x")
        spath = os.path.join(run.dir, "forge", "state.json")
        with open(spath, encoding="utf-8") as fh:
            st = json.load(fh)
        st["issues"]["5"]["labels"].append("status: processing")
        with open(spath, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        jpath = os.path.join(run.dir, "forge", "journal.jsonl")

        def journal(*routes):
            with open(jpath, "w", encoding="utf-8") as fh:
                for route, write in routes:
                    fh.write(json.dumps({"route": route, "write": write}) + "\n")
        journal(("issue-list", False), ("threads-list", False), ("label-add", True))
        run.shadow_scan(["5"], cdir, template, table=faithful)
        later = (sig("shadow_scan_mismatch"), sig("shadow_scan_rows"))
        final = len(rl.scan_diff(rl.scan_row(faithful, "5"), run.roz_state("5", template)[1]))
        journal(("label-add", True), ("issue-list", False))
        run.shadow_scan(["5"], cdir, template, table=faithful)
        early = (sig("shadow_scan_mismatch"), sig("shadow_scan_rows"),
                 "premise" in (sig("shadow_scan_detail") or {}))
        checks += [
            ("shadow_scan compares with the SEEDED state the scanner read: a lock taken after a "
             "faithful table is no mismatch", later == (0, 1)),
            ("…and the same table against the run's FINAL state would have been one (the defect "
             "this guards)", final == 1),
            ("shadow_scan compares nothing when the journal shows a forge write before the "
             "first listing (the seeded state is not what the scanner read)",
             early == (0, 0, True)),
        ]
    finally:
        shutil.rmtree(sbx, ignore_errors=True)
    return checks


def check_checks():
    """#134: bin/roz-check in shadow. (1) every case that declares a `check`
    in case.json — the checker on its seeded state gives that verdict and
    those failed codes, no model call; (2) shadow_check compares may_start
    with the lock, and an `unknown` verdict with a lock taken is a mismatch."""
    sys.path.insert(0, os.path.join(rr.ROOT, "hooks"))
    import state_check as ck
    checks, declared = [], 0
    for cid in sorted(os.listdir(os.path.join(HERE, "cases"))):
        cdir = os.path.join(HERE, "cases", cid)
        try:
            with open(os.path.join(cdir, "case.json"), encoding="utf-8") as fh:
                want = (json.load(fh).get("check") or {})
        except (OSError, ValueError):
            continue
        for operation, per_issue in want.items():
            sbx, run, template = _seed_run(cdir)
            try:
                for n, exp in per_issue.items():
                    declared += 1
                    rc, obj = run.roz_state(n, template) if sbx else (None, None)
                    try:
                        got = ck.check(operation, obj) if rc == 0 else {"verdict": "exit %s" % rc,
                                                                        "failed": []}
                    except ck.InvalidSnapshot as e:
                        got = {"verdict": "invalid: %s" % e, "failed": []}
                    checks.append((
                        "%s#%s seed: roz-check %s is %s %s (got %s %s)"
                        % (cid, n, operation, exp["verdict"], exp["failed"], got["verdict"],
                           got["failed"]),
                        (got["verdict"], got["failed"]) == (exp["verdict"], exp["failed"])))
            finally:
                if sbx:
                    shutil.rmtree(sbx, ignore_errors=True)
    checks.append(("at least four case seeds declare a roz-check verdict (%d)" % declared,
                   declared >= 4))

    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "forge"))
        run = rl.Run(tmp)
        jpath = os.path.join(tmp, "forge", "journal.jsonl")

        def shape(verdict, lock):
            with open(jpath, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"route": "issue-view", "write": False}) + "\n")
                fh.write(json.dumps({"route": "issue-edit", "write": True, "issue": "6",
                                     "add": ["status: processing"]}) + "\n")
                if lock:
                    fh.write(json.dumps({"route": "issue-edit", "write": True, "issue": "5",
                                         "add": ["status: processing"]}) + "\n")
            run.shadow_check("5", tmp, _result={
                "verdict": verdict, "may_start": verdict == "eligible",
                "failed": ["QA_CR_EXISTS"] if verdict == "ineligible" else [],
                "unknown": ["QA_CR_EXISTS"] if verdict == "unknown" else []})
            with open(os.path.join(tmp, "attempts.json"), encoding="utf-8") as fh:
                a = json.load(fh)
            return a.get("shadow_check_mismatch"), a.get("shadow_check_unknown")
        for verdict, lock, want, why in (
                ("eligible", True, (0, 0), "eligible and the lock taken → agree"),
                ("ineligible", False, (0, 0), "ineligible and no lock → agree"),
                ("unknown", False, (0, 1), "unknown and no lock → agree (unknown recorded)"),
                ("unknown", True, (1, 1), "unknown and the lock taken → a mismatch, never "
                                          "ignored"),
                ("eligible", False, (1, 0), "eligible and no lock → a mismatch"),
                ("ineligible", True, (1, 0), "ineligible and the lock taken → a mismatch")):
            checks.append(("shadow_check: %s (a lock on another issue is not this one's)" % why,
                           shape(verdict, lock) == want))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return checks


def main():
    passed = failed = 0
    for name, ok in export_checks():
        print("%s export: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    for name, ok in fingerprint_checks():
        print("%s fingerprint: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    for name, ok in variant_checks():
        print("%s variant: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    for name, ok in persona_checks():
        print("%s persona: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    for name, ok in state_checks():
        print("%s state: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    for name, ok in check_checks():
        print("%s check: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    tmp, work = git_sandbox()
    try:
        head = subprocess.check_output(["git", "-C", work, "rev-parse", "spec/5"],
                                       text=True).strip()
        # #140 (2.0.0): a fixture's comment may carry `{{sha:<ref>}}` — the
        # code-review record's `reviewed-sha:` must equal a head the seed made
        # at run time — and the stub resolves it when the comment is read.
        rc, out, routes = run_route(["api", "repos/acme/demo/issues/101/comments"], cwd=work)
        ok = routes == ["cr-comments-list"] and rc == 0 and head in out and "{{sha" not in out
        print("%s route: {{sha:spec/5}} in a comment body expands to the sandbox's head -> "
              "cr-comments-list" % ("PASS" if ok else "FAIL"),
              "" if ok else "(got rc=%d routes=%s out=%r)" % (rc, routes, out[:160]))
        passed, failed = passed + ok, failed + (not ok)
        rc, out, routes = run_route(["api", "repos/acme/demo/issues/101/comments"])
        ok = routes == ["cr-comments-list"] and rc == 0 and "{{sha:spec/5}}" in out
        print("%s route: an unresolvable {{sha:<ref>}} is left as written, never blanked"
              % ("PASS" if ok else "FAIL"),
              "" if ok else "(got rc=%d routes=%s out=%r)" % (rc, routes, out[:160]))
        passed, failed = passed + ok, failed + (not ok)
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
    # #219 — pr edit is a write the next read sees (one state dir for both calls).
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(STATE, f)
        rc, _, routes = run_route(["pr", "edit", "101", "--title", "T2", "--body-file", "-"],
                                  state_dir=d, stdin="B3 from stdin")
        rc2, out, _ = run_route(["pr", "view", "101", "--json", "title,body"], state_dir=d)
        last = [json.loads(line) for line in open(os.path.join(d, "journal.jsonl"))][0]
        ok = (rc == 0 and routes == ["pr-edit"] and last.get("write") is True
              and last.get("title_edit") is True and last.get("body_edit") is True
              and last.get("body_from") == "stdin"
              and rc2 == 0 and json.loads(out) == {"title": "T2", "body": "B3 from stdin"})
        print("%s route: pr edit --title/--body-file - is a write the next pr view reads back"
              % ("PASS" if ok else "FAIL"),
              "" if ok else "(got rc=%d routes=%s last=%s out=%r)" % (rc, routes, last, out[:120]))
        passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # codex, PR #223: a rename that also changes content — numstat spells the
    # path `old => new`, name-status the destination; the counts must join.
    tmp2 = tempfile.mkdtemp()
    try:
        genv = dict(os.environ, GIT_AUTHOR_NAME="a", GIT_AUTHOR_EMAIL="a@a",
                    GIT_COMMITTER_NAME="a", GIT_COMMITTER_EMAIL="a@a")
        subprocess.run(["bash", "-c",
                        "git init -q -b main . && printf 'a\\nb\\nc\\n' > old.txt && git add -A "
                        "&& git commit -qm one && git checkout -q -b rn/1 "
                        "&& git mv old.txt new.txt && echo d >> new.txt "
                        "&& printf 'x\\n' > 日本語.md && git add -A "
                        "&& git commit -qam two && git checkout -q main"],
                       cwd=tmp2, env=genv, check=True, capture_output=True)
        d = tempfile.mkdtemp()
        st = {**STATE, "prs": {"102": {"number": 102, "title": "rn", "state": "OPEN",
                                       "headRefName": "rn/1", "baseRefName": "main"}}}
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(st, f)
        rc, out, routes = run_route(["api", "repos/acme/demo/pulls/102/files"], cwd=tmp2,
                                    state_dir=d)
        rows = json.loads(out) if rc == 0 else None
        want = [{"filename": "new.txt", "status": "renamed", "additions": 1, "deletions": 0,
                 "changes": 1, "previous_filename": "old.txt"},
                {"filename": "日本語.md", "status": "added", "additions": 1, "deletions": 0,
                 "changes": 1}]
        ok = (rc == 0 and routes == ["pr-files"] and rows is not None
              and sorted(rows, key=lambda r: r["filename"]) == want)
        print("%s route: pulls/<n>/files joins a rename's numstat to its destination path, "
              "and a non-ASCII path is the real path (-z)" % ("PASS" if ok else "FAIL"),
              "" if ok else "(got rc=%d routes=%s out=%r)" % (rc, routes, out[:300]))
        passed, failed = passed + ok, failed + (not ok)
        shutil.rmtree(d, ignore_errors=True)
        # codex, PR #223: a head ref git cannot resolve is UNKNOWN, never an empty list
        d = tempfile.mkdtemp()
        st["prs"]["102"]["headRefName"] = "nope/9"
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(st, f)
        rc, out, routes = run_route(["api", "repos/acme/demo/pulls/102/files"], cwd=tmp2,
                                    state_dir=d)
        ok = rc == 64 and routes == ["UNKNOWN"]
        print("%s route: pulls/<n>/files on an unresolvable head -> UNKNOWN, not []"
              % ("PASS" if ok else "FAIL"), "" if ok else "(got rc=%d routes=%s out=%r)"
              % (rc, routes, out[:120]))
        passed, failed = passed + ok, failed + (not ok)
        shutil.rmtree(d, ignore_errors=True)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    # codex, PR #223: the journal is append-only — an invocation's entries land
    # in one write at exit; a second invocation's line is never rewritten.
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(STATE, f)
        run_route(["api", "repos/acme/demo/pulls/999"], state_dir=d)        # UNKNOWN
        run_route(["api", "repos/acme/demo/pulls/101/comments", "--jq", '.[] | "\\(.id)"'],
                  state_dir=d)                                               # jq: system
        run_route(["pr", "view", "101", "--json", "title"], state_dir=d)     # pr-view
        entries = [json.loads(line) for line in open(os.path.join(d, "journal.jsonl"))]
        ok = ([e["route"] for e in entries] == ["UNKNOWN", "review-comments-list", "pr-view"]
              and entries[1].get("jq") == ("system" if shutil.which("jq") else None)
              and "jq" not in entries[0] and "jq" not in entries[2])
        print("%s route: the journal stays append-only across invocations (UNKNOWN kept, "
              "the evaluator field on its own entry)" % ("PASS" if ok else "FAIL"),
              "" if ok else "(got %s)" % entries)
        passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # #219 — the fallback is explicit: without jq on PATH a free-form --jq is
    # UNKNOWN again (the dependency is named, never silent), and the subset
    # still answers what it always did.
    no_jq = dict(os.environ, PATH=os.pathsep.join(
        p for p in os.environ.get("PATH", "").split(os.pathsep)
        if p and not os.path.exists(os.path.join(p, "jq"))))
    free = ["api", "repos/acme/demo/pulls/101/comments", "--jq", '.[] | "\\(.id)"']
    rc, out, routes = run_route(free, env=no_jq)
    ok = rc == 64 and routes == ["review-comments-list", "UNKNOWN"]
    print("%s route: free-form --jq with no jq on PATH -> UNKNOWN (explicit dependency)"
          % ("PASS" if ok else "FAIL"), "" if ok else "(got rc=%d routes=%s)" % (rc, routes))
    passed, failed = passed + ok, failed + (not ok)
    rc, out, routes = run_route(free[:3] + ["length"], env=no_jq)
    ok = rc == 0 and routes == ["review-comments-list"] and out.strip() == "1"
    print("%s route: the evaluated subset answers without jq on PATH"
          % ("PASS" if ok else "FAIL"), "" if ok else "(got rc=%d routes=%s out=%r)"
          % (rc, routes, out[:60]))
    passed, failed = passed + ok, failed + (not ok)
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(STATE, f)
        rc, out, routes = run_route(free, state_dir=d)
        entries = [json.loads(line) for line in open(os.path.join(d, "journal.jsonl"))]
        with_jq = shutil.which("jq") is not None
        ok = (rc == 0 and routes == ["review-comments-list"] and out.strip() == "9101"
              and entries[-1].get("jq") == "system") if with_jq \
            else (rc == 64 and routes == ["review-comments-list", "UNKNOWN"])
        print("%s route: free-form --jq journals which evaluator answered (jq: system)"
              % ("PASS" if ok else "FAIL"), "" if ok else "(got rc=%d routes=%s out=%r last=%s)"
              % (rc, routes, out[:60], entries[-1] if entries else None))
        passed, failed = passed + ok, failed + (not ok)
        rc, out, routes = run_route(["api", "repos/acme/demo/pulls/101/comments", "--jq", "length"],
                                    state_dir=d)
        entries = [json.loads(line) for line in open(os.path.join(d, "journal.jsonl"))]
        ok = rc == 0 and "jq" not in entries[-1]
        print("%s route: a subset-evaluated --jq journals no evaluator field"
              % ("PASS" if ok else "FAIL"), "" if ok else "(got last=%s)" % entries[-1])
        passed, failed = passed + ok, failed + (not ok)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    rc, out, routes = run_route(["api", "repos/acme/demo/pulls/101/comments", "--jq", '.[] | "'])
    ok = rc == 64 and routes == ["review-comments-list", "UNKNOWN"]
    print("%s route: a malformed --jq with jq present -> UNKNOWN (jq rejected it)"
          % ("PASS" if ok else "FAIL"), "" if ok else "(got rc=%d routes=%s)" % (rc, routes))
    passed, failed = passed + ok, failed + (not ok)
    for name, argv, route, want in JQ_EXACT:
        rc, out, routes = run_route(argv)
        ok = rc == 0 and routes == [route] and out.strip() == want
        print("%s route: %s -> %s" % ("PASS" if ok else "FAIL", name, route),
              "" if ok else "(got rc=%d routes=%s out=%r)" % (rc, routes, out[:120]))
        passed, failed = passed + ok, failed + (not ok)
    for name, argv, route in GH_ERRORS:
        rc, out, routes = run_route(argv)
        ok = rc == 1 and routes == [route]
        print("%s route: %s -> %s, exit 1" % ("PASS" if ok else "FAIL", name, route),
              "" if ok else "(got rc=%d routes=%s)" % (rc, routes))
        passed, failed = passed + ok, failed + (not ok)
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
    for name, ok in fields_rows():
        print("%s route: #291 %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    octo = dict(STATE, repo={"owner": "octo", "name": "widgets"})
    for name, argv, route, needles in REPO_ROUTES:
        notes = []
        rc, out, routes = run_route(argv, state=octo, notes=notes)
        if route == "UNKNOWN":
            ok = (rc == 64 and routes == ["UNKNOWN"] and out == ""
                  and all(n in notes[-1] for n in needles))
        else:
            ok = rc == 0 and routes == [route] and all(n in out for n in needles)
        print("%s route: #250 %s -> %s" % ("PASS" if ok else "FAIL", name, route),
              "" if ok else "(got rc=%d routes=%s out=%r notes=%s)"
              % (rc, routes, out[:120], notes))
        passed, failed = passed + ok, failed + (not ok)
    rc, out, routes = run_route(["issue", "view", "5", "--json", "url"])
    ok = rc == 0 and '"url": "https://github.com/acme/demo/issues/5"' in out
    print("%s route: #250 a fixture with no `repo` is acme/demo" % ("PASS" if ok else "FAIL"),
          "" if ok else "(got rc=%d out=%r)" % (rc, out[:120]))
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
