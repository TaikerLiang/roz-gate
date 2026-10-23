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
                                               "reviewed-sha: {{sha:spec/5}}"}]}},
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
def _aggregate(results):
    d = tempfile.mkdtemp()
    try:
        report = os.path.join(d, "sut")
        for i, r in enumerate(results, 1):
            run = os.path.join(report, "C5", "run-%d" % i)
            os.makedirs(run)
            with open(os.path.join(run, "result.json"), "w") as f:
                json.dump(r, f)
        with contextlib.redirect_stdout(io.StringIO()):
            rr.aggregate({"name": "sut", "model": "m", "mode": "subscription"}, report)
        rows = json.load(open(os.path.join(report, "report.json")))["cases"]
        return next((r for r in rows if r["case"] == "C5"), None)
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


def main():
    passed = failed = 0
    for name, ok in export_checks():
        print("%s export: %s" % ("PASS" if ok else "FAIL", name))
        passed, failed = passed + ok, failed + (not ok)
    for name, ok in fingerprint_checks():
        print("%s fingerprint: %s" % ("PASS" if ok else "FAIL", name))
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
