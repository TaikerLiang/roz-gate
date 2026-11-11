#!/usr/bin/env python3
"""A fake `gh` / `glab` for test_roz_state.py — canned output for one logical
world, rendered in the shape of whichever CLI it was invoked as.

    FAKE_FORGE  the world (JSON, below)
    FAKE_LOG    every argv received, one JSON line each

World:
    {"issues": {"27": {"labels": ["track: spec", …]}},
     "prs": [{"number": 41, "state": "open|merged|closed", "draft": false,
              "base": "spec/27", "head": "feat/27", "head_sha": "…",
              "threads": [false, true],            # resolved?
              "comments": [{"id": 9001, "body": "…"}]}],
     "blockers": {"27": [{"number": 31, "state": "open"}]},
     "fail": ["issue", "prs", "threads:41", "threads2:41", "comments:41", "blockers"],
     "page_size": 2}

The GitLab half follows references/forge-gitlab.md and the public REST
shapes; it has not been checked against a live GitLab (#133 ruling 1).
An argv no route answers exits 64, like the replay forge stub.
"""

import json
import os
import re
import sys
from urllib.parse import unquote

ME = os.path.basename(sys.argv[0])
ARGV = sys.argv[1:]
with open(os.environ["FAKE_FORGE"], encoding="utf-8") as f:
    W = json.load(f)
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps([ME] + ARGV) + "\n")
FAIL = set(W.get("fail", []))
PAGE = int(W.get("page_size", 100))


def die(msg="HTTP 502"):
    sys.stderr.write("%s: %s\n" % (ME, msg))
    sys.exit(1)


def flag(*names):
    for i, a in enumerate(ARGV):
        if a in names and i + 1 < len(ARGV):
            return ARGV[i + 1]
    return None


def fields():
    out = {}
    for i, a in enumerate(ARGV):
        if a in ("-f", "-F") and i + 1 < len(ARGV) and "=" in ARGV[i + 1]:
            k, v = ARGV[i + 1].split("=", 1)
            out[k] = v
    return out


def pages(rows):
    """`--paginate` prints one JSON array per page, back to back."""
    chunks = [rows[i:i + PAGE] for i in range(0, len(rows), PAGE)] or [[]]
    sys.stdout.write("".join(json.dumps(c) for c in chunks))


def pr(number):
    for p in W.get("prs", []):
        if str(p["number"]) == str(number):
            return p
    die("Not Found (HTTP 404)")


def target():
    """The api path: the first bare word after `api` that is not a flag's value."""
    skip, out = False, None
    for a in ARGV[1:]:
        if skip:
            skip = False
        elif a in ("-f", "-F", "-X", "--method", "--jq", "-q", "-H"):
            skip = True
        elif not a.startswith("-") and out is None:
            out = a
    return out or ""


def merged_prs():
    """The world's merged CRs, then `merged_filler` synthetic ones (for the
    ceiling), in the world's own order — never sorted for the caller."""
    rows = [p for p in W.get("prs", []) if p["state"] == "merged"]
    rows += [{"number": 100000 + i, "head": "filler/%d" % i, "head_sha": "f" * 40,
              "merged_at": "2020-01-01T00:00:00Z"} for i in range(int(W.get("merged_filler", 0)))]
    return rows


GH_STATE = {"open": "OPEN", "merged": "MERGED", "closed": "CLOSED"}
GL_STATE = {"open": "opened", "merged": "merged", "closed": "closed"}


def gh():
    if ARGV[:2] == ["repo", "view"]:
        if "repo" in FAIL:
            die()
        print(json.dumps({"owner": {"login": "acme"}, "name": "demo"}))
        return
    if ARGV[:2] == ["issue", "view"]:
        iss = W.get("issues", {}).get(ARGV[2])
        if "issue" in FAIL or iss is None:
            die("Could not resolve to an Issue")
        print(json.dumps({"labels": [{"name": x} for x in iss["labels"]]}))
        return
    if ARGV[:2] == ["pr", "list"]:
        if flag("--state") == "merged":             # the merged history (#272)
            if "merged" in FAIL:
                die()
            rows = [{"number": p["number"], "headRefName": p["head"],
                     "headRefOid": p.get("head_sha", ""), "mergedAt": p.get("merged_at")}
                    for p in merged_prs()]
            print(json.dumps(rows[:int(flag("--limit") or 30)]))
            return
        if "prs" in FAIL:
            die()
        assert flag("--state") == "all", "CR-FIND must ask all states"
        rows = [{"number": p["number"], "state": GH_STATE[p["state"]],
                 "isDraft": p.get("draft", False), "baseRefName": p["base"],
                 "headRefOid": p.get("head_sha", "")}
                for p in W.get("prs", []) if p["head"] == flag("--head")]
        print(json.dumps(rows))
        return
    if ARGV[:1] == ["api"] and target() == "graphql":
        f = fields()
        assert "mutation" not in f.get("query", "")
        p = pr(f["pr"])
        start = int(f.get("after") or 0)
        if ("threads:%s" % p["number"]) in FAIL or (
                start and ("threads2:%s" % p["number"]) in FAIL):
            die()
        th = p.get("threads", [])
        nodes = [{"isResolved": r} for r in th[start:start + PAGE]]
        more = start + PAGE < len(th)
        print(json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": {
            "pageInfo": {"hasNextPage": more, "endCursor": str(start + PAGE) if more else None},
            "nodes": nodes}}}}}))
        return
    if ARGV[:1] == ["api"]:
        t = target()
        m = re.match(r"repos/acme/demo/issues/(\d+)/comments$", t)
        if m:
            p = pr(m.group(1))
            if ("comments:%s" % p["number"]) in FAIL:
                die()
            pages([{"id": c["id"], "body": c["body"], "user": {"login": "roz"}}
                   for c in p.get("comments", [])])
            return
        m = re.match(r"repos/acme/demo/issues/(\d+)/dependencies/blocked_by$", t)
        if m:
            if "blockers" in FAIL:
                die("Not Found (HTTP 404)")
            pages([{"number": b["number"], "state": b["state"],
                    "html_url": "https://forge/x/y/issues/%s" % b["number"]}
                   for b in W.get("blockers", {}).get(m.group(1), [])])
            return
    sys.exit(64)


def gl_label(name):
    """references/forge-gitlab.md § Labels: scoped `key::value`, and the lock
    is the plain label `processing` — never `status::processing`."""
    if name == "status: processing":
        return "processing"
    key, sep, val = name.partition(": ")
    return "%s::%s" % (key, val) if sep and key in ("track", "status", "type") else name


def glab():
    if ARGV[:1] != ["api"]:
        sys.exit(64)
    t = target()
    path, _, qs = t.partition("?")
    q = {k: unquote(v) for k, v in (kv.split("=", 1) for kv in qs.split("&") if "=" in kv)}
    m = re.match(r"projects/:id/issues/(\d+)$", path)
    if m:
        iss = W.get("issues", {}).get(m.group(1))
        if "issue" in FAIL or iss is None:
            die("404 Not Found")
        print(json.dumps({"iid": int(m.group(1)), "labels": [gl_label(x) for x in iss["labels"]]}))
        return
    if path == "projects/:id/merge_requests":
        if q.get("state") == "merged":              # the merged history (#272)
            if "merged" in FAIL:
                die()
            per, page = int(q.get("per_page", 20)), int(q.get("page", 1))
            rows = [{"iid": p["number"], "source_branch": p["head"],
                     "sha": p.get("head_sha", ""), "merged_at": p.get("merged_at")}
                    for p in merged_prs()]
            print(json.dumps(rows[(page - 1) * per:page * per]))
            return
        if "prs" in FAIL:
            die()
        assert q.get("state") == "all", "CR-FIND must ask all states"
        pages([{"iid": p["number"], "state": GL_STATE[p["state"]],
                "draft": p.get("draft", False), "target_branch": p["base"],
                "sha": p.get("head_sha", "")}
               for p in W.get("prs", []) if p["head"] == q.get("source_branch")])
        return
    m = re.match(r"projects/:id/merge_requests/(\d+)/discussions$", path)
    if m:
        p = pr(m.group(1))
        th = p.get("threads", [])
        if ("threads:%s" % p["number"]) in FAIL or (
                len(th) > PAGE and ("threads2:%s" % p["number"]) in FAIL):
            die()
        rows = [{"id": "d%d" % i, "individual_note": False,
                 "notes": [{"resolvable": True, "resolved": r, "type": "DiffNote"}]}
                for i, r in enumerate(th)]
        rows += [{"id": "n%d" % c["id"], "individual_note": True,
                  "notes": [{"resolvable": False, "resolved": False, "type": None}]}
                 for c in p.get("comments", [])]
        pages(rows)
        return
    m = re.match(r"projects/:id/merge_requests/(\d+)/notes$", path)
    if m:
        p = pr(m.group(1))
        if ("comments:%s" % p["number"]) in FAIL:
            die()
        rows = [{"id": c["id"], "body": c["body"], "system": False, "type": None}
                for c in p.get("comments", [])]
        rows.append({"id": 5, "body": "**[reviewer] · code-review** in a diff thread",
                     "system": False, "type": "DiffNote"})
        rows.append({"id": 6, "body": "changed the description", "system": True, "type": None})
        pages(rows)
        return
    m = re.match(r"projects/:id/issues/(\d+)/links$", path)
    if m:
        if "blockers" in FAIL:
            die("403 Forbidden")
        rows = [{"iid": b["number"], "state": GL_STATE[b["state"]],
                 "link_type": "is_blocked_by",
                 "web_url": "https://forge/x/y/issues/%s" % b["number"]}
                for b in W.get("blockers", {}).get(m.group(1), [])]
        rows.append({"iid": 999, "state": "opened", "link_type": "relates_to",
                     "web_url": "https://forge/x/y/issues/999"})
        pages(rows)
        return
    sys.exit(64)


if __name__ == "__main__":
    {"gh": gh, "glab": glab}.get(ME, lambda: sys.exit(64))()
