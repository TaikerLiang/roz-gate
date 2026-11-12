"""The roz-state collector (#133) — one issue's observable workflow state,
under the contract in references/roz-state.md / state_contract.py.

Facts only: what a label, a remote head, a CR record, a thread list or a
comment says. No comparison between two facts, no verdict, no next step —
those are roz-check's (#134) or the agent's. Read-only by construction:
every forge call goes through `run()`, which refuses any argv outside the
read allow-list, and git is asked for nothing but `ls-remote` and config.

Branch identity is roz-branch's alone (hooks/branch_names.py): this module
matches a snapshot and never renders, parses or guesses a name. A CR is
looked up by the bound head. `collect_snapshot` adds to the remote's heads
the head names merged CRs remember (#272), so a head the forge deleted on
merge still finds its CR: the branch is `absent`, the CR `observed`.

Selection is ours, never the CLI's (every list is read to the end, then
ordered here): among the CRs of one head — the one open CR; more than one
open → unknown (ambiguous); none open → the merged CR with the highest
number, else the closed CR with the highest number. Among the records of
one kind — the comment with the highest id.

Two adapters, one logical shape. `GitHub` follows references/forge-github.md
and is exercised against the replay forge stub. `GitLab` follows
references/forge-gitlab.md and the public REST shapes: contract-compatible
against canned glab output; live compatibility not yet verified.

Stdlib only, Python 3.9-compatible, like the hooks. Kept in hooks/ beside
state_contract.py for layout convenience; not a hook.
"""

import json
import re
import subprocess
import time

from branch_names import collect_remote_heads, effective, local_key, match_heads, validate
from config_block import find_block, git, main_checkout
from state_contract import SCHEMA

TIMEOUT = 60
# The merged history is read to its last page; past this many merged CRs the
# read stops and says `history_truncated` — unknown, never "read" (#272).
MERGED_CEILING = 5000
DEFAULT_ACCEPTANCE_DIR = "tests/acceptance"
# contract name → roz-branch kind
KINDS = (("spec", "spec"), ("implementation", "feat"), ("qa", "qa"))
# fact → (the CR it hangs off, the record's opening marker)
MARKERS = {"implementation.review_marker": "**[reviewer] · code-review**",
           "qa.fidelity_marker": "**[reviewer] · fidelity**"}
REVIEWED_SHA = re.compile(r"^\s*reviewed-sha:\s*`?([0-9a-fA-F]{7,64})`?\s*$", re.M)
SRC_BRANCH = "roz-branch match"


class Refused(Exception):
    """An argv outside the read allow-list — a defect, never an observation."""


class ReadFailed(Exception):
    def __init__(self, reason, detail=""):
        super().__init__(detail)
        self.reason, self.detail = reason, detail


# ---- the one gate every forge call passes ----------------------------------------

_VALUE_FLAGS = ("--jq", "-q", "-H", "--header", "--hostname")


def allowed(argv):
    """True only for the reads this collector makes. Anything that could
    write — a mutating subcommand, an HTTP method, a request field, a
    GraphQL mutation, a request body — is refused."""
    if not argv or argv[0] not in ("gh", "glab"):
        return False
    cli, rest = argv[0], list(argv[1:])
    if cli == "gh" and rest[:2] in (["repo", "view"], ["issue", "view"], ["pr", "list"]):
        return True
    if rest[:1] != ["api"]:
        return False
    target, graphql_fields, i = None, [], 1
    while i < len(rest):
        a = rest[i]
        if a == "--paginate":
            pass
        elif a in _VALUE_FLAGS:
            i += 1
        elif a in ("-f", "-F"):
            if i + 1 >= len(rest):
                return False
            graphql_fields.append(rest[i + 1])
            i += 1
        elif a.startswith("-"):
            return False                    # -X, --method, --input, --field, …: never
        elif target is None:
            target = a
        else:
            return False
        i += 1
    if target is None:
        return False
    if graphql_fields:
        # fields turn a REST call into a POST; only a GraphQL *query* may carry them
        if cli != "gh" or target != "graphql":
            return False
        queries = [f[len("query="):] for f in graphql_fields if f.startswith("query=")]
        if len(queries) != 1 or not queries[0].lstrip().startswith("query"):
            return False
        if re.search(r"\bmutation\b|\bsubscription\b", queries[0]):
            return False
    return target != "graphql" or bool(graphql_fields)


def run(argv):
    """stdout of one allowed read; ReadFailed when the CLI is missing, times
    out or exits non-zero. Never a shell."""
    if not allowed(argv):
        raise Refused("not a read: %s" % " ".join(argv[:6]))
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ReadFailed("forge_query_failed", "%s: %s" % (argv[0], type(e).__name__))
    if p.returncode != 0:
        tail = (p.stderr.strip().splitlines() or ["exit %d" % p.returncode])[-1]
        raise ReadFailed("forge_query_failed", "%s: %s" % (argv[0], tail[:200]))
    return p.stdout


def _stream(text):
    """Every JSON value in `text`, in order — `--paginate` prints one array
    per page back to back. Unparseable output is a failed read."""
    dec, out, i = json.JSONDecoder(), [], 0
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            val, i = dec.raw_decode(text, i)
        except ValueError:
            raise ReadFailed("forge_query_failed", "unparseable forge output")
        out.append(val)
    return out


def _rows(text):
    """The rows of a (possibly paginated) list response."""
    rows = []
    for val in _stream(text):
        if not isinstance(val, list):
            raise ReadFailed("forge_query_failed", "expected a list from the forge")
        rows.extend(val)
    if not all(isinstance(r, dict) for r in rows):
        raise ReadFailed("forge_query_failed", "expected objects in the forge's list")
    return rows


def _one(text):
    vals = _stream(text)
    if len(vals) != 1 or not isinstance(vals[0], dict):
        raise ReadFailed("forge_query_failed", "expected one object from the forge")
    return vals[0]


def _cr(number, state, draft, base, head_sha):
    """One CR record in the contract's shape; a record that cannot be
    normalised is a failed read, never a half-filled fact."""
    if (isinstance(number, bool) or not isinstance(number, int) or state is None
            or not isinstance(draft, bool) or not isinstance(base, str) or not base
            or not isinstance(head_sha, str) or not head_sha):
        raise ReadFailed("forge_query_failed", "a CR record the adapter cannot normalise")
    return {"number": number, "state": state, "draft": draft, "base": base,
            "head_sha": head_sha}


# ---- adapters: CLI output → logical rows -----------------------------------------

class GitHub:
    """references/forge-github.md. `gh` infers the repository from the remote."""

    THREADS = ("query($owner:String!,$repo:String!,$pr:Int!,$after:String){"
               "repository(owner:$owner,name:$repo){pullRequest(number:$pr){"
               "reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}"
               "nodes{isResolved}}}}}")
    STATES = {"OPEN": "open", "MERGED": "merged", "CLOSED": "closed"}

    def __init__(self):
        self._repo = None

    def repo(self):
        if self._repo is None:
            r = _one(run(["gh", "repo", "view", "--json", "owner,name"]))
            owner, name = (r.get("owner") or {}).get("login"), r.get("name")
            if not owner or not name:
                raise ReadFailed("forge_query_failed", "gh repo view named no repository")
            self._repo = (owner, name)
        return self._repo

    def labels(self, issue):
        r = _one(run(["gh", "issue", "view", str(issue), "--json", "labels"]))
        if not isinstance(r.get("labels"), list):
            raise ReadFailed("forge_query_failed", "ISSUE-VIEW returned no label list")
        return [x.get("name") for x in r["labels"] if isinstance(x, dict)]

    def crs(self, head):
        rows = _rows(run(["gh", "pr", "list", "--head", head, "--state", "all", "--limit",
                          "1000", "--json", "number,state,isDraft,baseRefName,headRefOid"]))
        return [_cr(r.get("number"), self.STATES.get(r.get("state")), r.get("isDraft"),
                    r.get("baseRefName"), r.get("headRefOid")) for r in rows]

    def merged_heads(self, repo=None):
        argv = ["gh", "pr", "list", "--state", "merged", "--limit", str(MERGED_CEILING + 1),
                "--json", "number,headRefName,headRefOid,mergedAt"]
        if repo:                                # (host, path): the remote's own repository
            argv += ["--repo", "%s/%s" % repo]
        rows = _rows(run(argv))
        if len(rows) > MERGED_CEILING:
            raise ReadFailed("history_truncated",
                             "more than %d merged CRs" % MERGED_CEILING)
        return [{"cr": r.get("number"), "head": r.get("headRefName"),
                 "sha": r.get("headRefOid"), "merged_at": r.get("mergedAt")} for r in rows]

    def unresolved_threads(self, number):
        owner, name = self.repo()
        count, after = 0, None
        while True:
            argv = ["gh", "api", "graphql", "-f", "query=" + self.THREADS,
                    "-F", "owner=" + owner, "-F", "repo=" + name, "-F", "pr=%d" % number]
            if after is not None:
                argv += ["-f", "after=" + after]
            r = _one(run(argv))
            try:
                rt = r["data"]["repository"]["pullRequest"]["reviewThreads"]
                nodes, info = rt["nodes"], rt["pageInfo"]
                count += sum(1 for n in nodes if n["isResolved"] is False)
                more, after = info["hasNextPage"], info["endCursor"]
            except (KeyError, TypeError):
                raise ReadFailed("forge_query_failed", "THREADS-LIST: an unexpected shape")
            if not more:
                return count
            if not after:
                raise ReadFailed("forge_query_failed", "THREADS-LIST: a next page with no cursor")

    def comments(self, number):
        owner, name = self.repo()
        rows = _rows(run(["gh", "api", "--paginate",
                          "repos/%s/%s/issues/%d/comments" % (owner, name, number)]))
        return [{"id": r.get("id"), "body": r.get("body") or ""} for r in rows]

    def blockers(self, issue):
        owner, name = self.repo()
        rows = _rows(run(["gh", "api", "--paginate", "repos/%s/%s/issues/%d/dependencies/blocked_by"
                          % (owner, name, issue)]))
        return [{"issue": r.get("number"), "state": r.get("state"), "url": r.get("html_url")}
                for r in rows]


class GitLab:
    """references/forge-gitlab.md, through `glab api` (GET only). Canned
    output only — live GitLab not yet verified (#133 ruling 1)."""

    STATES = {"opened": "open", "merged": "merged", "closed": "closed"}

    @staticmethod
    def _get(path):
        return run(["glab", "api", "--paginate", path])

    def labels(self, issue):
        r = _one(run(["glab", "api", "projects/:id/issues/%d" % issue]))
        if not isinstance(r.get("labels"), list):
            raise ReadFailed("forge_query_failed", "ISSUE-VIEW returned no label list")
        return [self._label(x) for x in r["labels"] if isinstance(x, str)]

    @staticmethod
    def _label(name):
        """GitLab's scheme → the loop's names (forge-gitlab.md § Labels): the
        scoped `track::spec` / `status::in-dev` / `type::fix` are `track: spec`
        / `status: in-dev` / `type: fix`, and the lock is the plain, unscoped
        label `processing` — `status: processing` everywhere else."""
        if name == "processing":
            return "status: processing"
        key, sep, val = name.partition("::")
        return "%s: %s" % (key, val) if sep and key in ("track", "status", "type") else name

    def crs(self, head):
        from urllib.parse import quote
        rows = _rows(self._get("projects/:id/merge_requests?source_branch=%s&state=all"
                               "&per_page=100" % quote(head, safe="")))
        return [_cr(r.get("iid"), self.STATES.get(r.get("state")),
                    r.get("draft", r.get("work_in_progress")), r.get("target_branch"),
                    r.get("sha")) for r in rows]

    def merged_heads(self, repo=None):
        from urllib.parse import quote
        rows, page = [], 1
        # (host, path): the remote's own project, by its URL-encoded path
        project, host = (quote(repo[1], safe=""), ["--hostname", repo[0]]) if repo else (":id", [])
        while True:
            got = _rows(run(["glab", "api", *host, "projects/%s/merge_requests?state=merged"
                             "&per_page=100&page=%d" % (project, page)]))
            rows.extend(got)
            if len(got) < 100:
                break                       # the forge's last page: the history is read
            if len(rows) >= MERGED_CEILING:
                raise ReadFailed("history_truncated",
                                 "more than %d merged CRs" % MERGED_CEILING)
            page += 1
        return [{"cr": r.get("iid"), "head": r.get("source_branch"), "sha": r.get("sha"),
                 "merged_at": r.get("merged_at")} for r in rows]

    def unresolved_threads(self, number):
        rows = _rows(self._get("projects/:id/merge_requests/%d/discussions?per_page=100"
                               % number))
        count = 0
        for d in rows:
            notes = [n for n in (d.get("notes") or []) if isinstance(n, dict)
                     and n.get("resolvable")]
            if notes and not all(n.get("resolved") for n in notes):
                count += 1
        return count

    def comments(self, number):
        rows = _rows(self._get("projects/:id/merge_requests/%d/notes?per_page=100" % number))
        # top-level only: no system note, no note that belongs to a diff thread
        return [{"id": r.get("id"), "body": r.get("body") or ""} for r in rows
                if not r.get("system") and r.get("type") is None]

    def blockers(self, issue):
        rows = _rows(self._get("projects/:id/issues/%d/links?per_page=100" % issue))
        return [{"issue": r.get("iid"), "state": self.STATES.get(r.get("state")),
                 "url": r.get("web_url")}
                for r in rows if r.get("link_type") == "is_blocked_by"]


ADAPTERS = {"github": GitHub, "gitlab": GitLab}


# ---- envelopes --------------------------------------------------------------------

def observed(value, source):
    return {"status": "observed", "value": value, "source": source}


def absent(source):
    return {"status": "absent", "value": None, "source": source}


def unknown(reason, source):
    return {"status": "unknown", "value": None, "source": source, "reason": reason}


def failure(reason, source, detail=""):
    f = {"reason": reason, "source": source}
    if detail:
        f["detail"] = detail
    return {"schema": SCHEMA, "collection_failure": f}, 2


# ---- selection: ours, never the CLI's ---------------------------------------------

def pick_cr(crs):
    """(cr, None) · (None, None) when there is none · (None, 'ambiguous')."""
    opens = [c for c in crs if c["state"] == "open"]
    if len(opens) == 1:
        return opens[0], None
    if len(opens) > 1:
        return None, "ambiguous"
    for state in ("merged", "closed"):
        group = [c for c in crs if c["state"] == state]
        if group:
            return max(group, key=lambda c: c["number"]), None
    return None, None


def pick_marker(comments, marker):
    """The record with the highest comment id, raw — or None."""
    hits = [c for c in comments if isinstance(c.get("id"), int) and not isinstance(c["id"], bool)
            and c["body"].lstrip().startswith(marker)]
    if not hits:
        return None
    rec = max(hits, key=lambda c: c["id"])
    m = REVIEWED_SHA.search(rec["body"])
    return {"reviewed_sha": m.group(1) if m else None, "comment_id": rec["id"]}


# ---- the branch snapshot: the remote's heads + the merged history (#272) ----------

_REMOTE_URL = (re.compile(r"^(?:https?|ssh|git)://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+?)(?:\.git)?/?$"),
               re.compile(r"^(?:[^@/]+@)?([^/:]+):(?!/)(.+?)(?:\.git)?/?$"))      # scp-like


def forge_repo(remote):
    """(host, path) of the forge repository `remote` names — from its
    configured URL, as written (before any `insteadOf`) — or None when the
    URL names none (a local path: a sandbox). The history must come from
    the repository the heads came from, never from wherever the forge CLI
    resolves by default (codex review, PR #275)."""
    url = git("config", "--get", "remote.%s.url" % remote) or ""
    for pat in _REMOTE_URL:
        m = pat.match(url)
        if m and "/" in m.group(2):
            return m.group(1), m.group(2)
    return None


def collect_snapshot(remote="origin"):
    """branch_names.collect_remote_heads, plus `merged_heads` — the head
    names merged CRs remember, so a head the forge deleted on merge can
    still be bound (branch_names.match_heads decides; this only collects).

        merged_heads: {"status": "observed", "heads": {name: {"cr", "sha", "merged_at"}}}
                    | {"status": "unknown", "reason": "forge_query_failed" |
                       "history_truncated", "detail": …, "heads": {}}
                    | {"status": "not_asked", "heads": {}}

    `not_asked`: no Roz Gate config block (not a roz-gate project — no forge
    is named), or the remote itself is unreadable. The read is bound to the
    repository `remote` names (`forge_repo`); only a remote whose URL names
    none — a local path — is left to the forge CLI's own resolution, since
    there is then no other repository to confuse it with. A failed history read
    never touches the remote's part: `status` stays the remote's. Where
    merged CRs share a head name, the one merged last is kept —
    max((merged_at, number)): chronology, the number only breaking a tie
    or standing in for a missing time."""
    snap = collect_remote_heads(remote)
    snap["merged_heads"] = {"status": "not_asked", "heads": {}}
    if snap.get("status") != "observed":
        return snap
    block = find_block(git("rev-parse", "--show-toplevel"))
    forge = (_block_key(block, "forge") or "").lower() if block else ""
    if forge not in ADAPTERS:
        return snap
    try:
        best = {}
        for r in ADAPTERS[forge]().merged_heads(forge_repo(remote)):
            if (not isinstance(r["head"], str) or not r["head"] or not isinstance(r["sha"], str)
                    or not r["sha"] or isinstance(r["cr"], bool) or not isinstance(r["cr"], int)):
                raise ReadFailed("forge_query_failed", "a merged CR record the adapter "
                                 "cannot normalise")
            key = (r["merged_at"] or "", r["cr"])
            if r["head"] not in best or key > best[r["head"]][0]:
                best[r["head"]] = (key, {"cr": r["cr"], "sha": r["sha"],
                                         "merged_at": r["merged_at"]})
        snap["merged_heads"] = {"status": "observed",
                                "heads": {h: v[1] for h, v in sorted(best.items())}}
    except ReadFailed as e:
        snap["merged_heads"] = {"status": "unknown", "reason": e.reason, "detail": e.detail,
                                "heads": {}}
    return snap


# ---- config -----------------------------------------------------------------------

def _block_key(block, key):
    m = re.search(r"^-\s*%s:\s*(.+)$" % re.escape(key), block, re.M)
    return m.group(1).strip().strip("`").strip() if m else None


def _default_branch(tops):
    """bin/roz-config's rule, read without running it (its first run may
    write the local file — this tool writes nothing)."""
    stored = local_key(tops, "default_branch")
    if stored:
        return stored
    ref = git("symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    return ref[len("origin/"):] if ref and ref.startswith("origin/") else "main"


def _labels_state(labels):
    """(track, status, processing, blocked) or ReadFailed(ambiguous)."""
    tracks = sorted({x[len("track:"):].strip() for x in labels if x.startswith("track:")})
    statuses = sorted({x[len("status:"):].strip() for x in labels if x.startswith("status:")})
    stage = [s for s in statuses if s not in ("processing", "blocked")]
    if len(tracks) > 1:
        raise ReadFailed("ambiguous", "more than one track label: %s" % ", ".join(tracks))
    if len(stage) > 1:
        raise ReadFailed("ambiguous", "more than one status label: %s" % ", ".join(stage))
    typ = sorted({x[len("type:"):].strip() for x in labels if x.startswith("type:")})
    return ((tracks[0] if tracks else None), (stage[0] if stage else None),
            "processing" in statuses, "blocked" in statuses, (typ[0] if len(typ) == 1 else None))


# ---- the collector ----------------------------------------------------------------

def collect(issue):
    """(snapshot, 0) or (typed collection failure, 2), for the repository in
    the current directory. Never a partial snapshot."""
    top = git("rev-parse", "--show-toplevel")
    if not top:
        return failure("unsupported", "git", "not inside a git repository")
    block = find_block(top)
    if block is None:
        return failure("unsupported", "config block",
                       "no Roz Gate config block — not a roz-gate project")
    forge = (_block_key(block, "forge") or "").lower()
    if forge not in ADAPTERS:
        return failure("unsupported", "config block", "forge: %r is not github or gitlab" % forge)
    tops = [top, main_checkout()]
    template = effective(local_key(tops, "branch_template"))
    why = validate(template)
    if why:
        return failure("unsupported", "roz-config", "branch_template %s: %s" % (template, why))
    config = {"branch_template": template, "default_branch": _default_branch(tops),
              "acceptance_dir": _block_key(block, "acceptance_dir") or DEFAULT_ACCEPTANCE_DIR}
    api = ADAPTERS[forge]()
    try:
        track, status, processing, blocked, typ = _labels_state(api.labels(issue))
    except ReadFailed as e:
        return failure(e.reason, "ISSUE-VIEW", e.detail)

    snap = {"schema": SCHEMA, "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "issue": issue, "track": track, "status": status, "processing": processing,
            "blocked": blocked, "config": config, "branches": {},
            "spec": {}, "implementation": {}, "qa": {}, "dependencies": {}}

    # branches — one read of the remote's heads, matched per kind
    heads = collect_snapshot() if track == "spec" else None
    crs = {}
    for name, kind in KINDS:
        if track != "spec":
            # roz-state/0.1 binds branches for `track: spec` only
            snap["branches"][name] = unknown("unsupported", SRC_BRANCH)
            crs[name] = unknown("depends_on_unknown", "CR-FIND")
            continue
        m = match_heads(heads, template, kind=kind, n=str(issue),
                        type=(typ or "feat") if kind == "feat" else None)
        outcome, found = m["outcome"], m["matches"]
        if outcome == "UNKNOWN":
            # the remote unreadable, or no live head and a merged history that
            # could not be read to its end (#272) — never "no branch"
            why = ("remote_unreachable" if heads.get("status") != "observed" else
                   "forge_query_failed" if m.get("reason") == "forge_query_failed" else
                   "unsupported")                    # history_truncated: past the ceiling
            snap["branches"][name] = unknown(why, SRC_BRANCH)
            crs[name] = unknown("depends_on_unknown", "CR-FIND")
        elif outcome == "MULTIPLE_SAME_SEQ":
            snap["branches"][name] = unknown("ambiguous", SRC_BRANCH)
            crs[name] = unknown("depends_on_unknown", "CR-FIND")
        elif outcome == "NO_MATCH":
            snap["branches"][name] = absent(SRC_BRANCH)
            crs[name] = absent(SRC_BRANCH)     # no head, live or remembered, to ask about
        else:
            head = found[-1] if outcome == "MULTIPLE_SEQ" else found[0]   # sorted by {seq}
            if not head.get("sha"):
                snap["branches"][name] = unknown("remote_unreachable", SRC_BRANCH)
                crs[name] = unknown("depends_on_unknown", "CR-FIND")
                continue
            # a head only a merged CR remembers is no branch — but its name
            # still finds the CR (#272)
            snap["branches"][name] = (absent(SRC_BRANCH) if head.get("deleted") else observed(
                {"name": head["branch"], "sha": head["sha"]}, SRC_BRANCH))
            try:
                cr, why = pick_cr(api.crs(head["branch"]))
            except ReadFailed as e:
                crs[name] = unknown(e.reason, "CR-FIND")
                continue
            crs[name] = (unknown(why, "CR-FIND") if why else observed(cr, "CR-FIND") if cr
                         else absent("CR-FIND"))
    for name, _ in KINDS:
        snap[name]["cr"] = crs[name]

    # what hangs off a CR follows the CR
    for name, count_key, marker_key in (
            ("implementation", "open_review_threads", "review_marker"),
            ("qa", "open_fidelity_threads", "fidelity_marker")):
        cr = crs[name]
        if cr["status"] == "absent":
            snap[name][count_key] = absent("THREADS-LIST")
            snap[name][marker_key] = absent("CR-COMMENTS-LIST")
            continue
        if cr["status"] == "unknown":
            snap[name][count_key] = unknown("depends_on_unknown", "THREADS-LIST")
            snap[name][marker_key] = unknown("depends_on_unknown", "CR-COMMENTS-LIST")
            continue
        number = cr["value"]["number"]
        try:
            snap[name][count_key] = observed(api.unresolved_threads(number), "THREADS-LIST")
        except ReadFailed as e:
            snap[name][count_key] = unknown(e.reason, "THREADS-LIST")
        try:
            rec = pick_marker(api.comments(number), MARKERS["%s.%s" % (name, marker_key)])
            snap[name][marker_key] = (observed(rec, "CR-COMMENTS-LIST") if rec
                                      else absent("CR-COMMENTS-LIST"))
        except ReadFailed as e:
            snap[name][marker_key] = unknown(e.reason, "CR-COMMENTS-LIST")

    # forge-native blockers — an observation, in issue-number order; no graph
    try:
        rows = api.blockers(issue)
        if not all(isinstance(b["issue"], int) and not isinstance(b["issue"], bool)
                   and b["state"] in ("open", "closed") and isinstance(b["url"], str) and b["url"]
                   for b in rows):
            raise ReadFailed("forge_query_failed", "a blocker record the adapter cannot normalise")
        snap["dependencies"]["blocked_by"] = observed(
            sorted(rows, key=lambda b: b["issue"]), "ISSUE-BLOCKERS")
    except ReadFailed as e:
        snap["dependencies"]["blocked_by"] = unknown(e.reason, "ISSUE-BLOCKERS")
    return snap, 0
