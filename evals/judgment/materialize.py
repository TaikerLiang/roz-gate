#!/usr/bin/env python3
"""Materialize the judgment tier's fixtures — run ONCE at build, outputs
committed, so every later run is reproducible with no GitHub at all.

For each fixture: the forge state frozen at the question's timestamp T
(issue body verbatim; comments created at or before T; labels and
assignee RECONSTRUCTED from the issues timeline at T — the live labels
carry the answer's aftermath; every issue/PR the body cross-references,
frozen the same way), a fixture.json with the pin and the grading
parameters, and the HISTORICAL agent output the judge red-proof grades
(the real thread bodies at the thread URLs, plus the spec's Open
Questions at the refinement commit).

Contamination is the whole game: every comment after T contains the
answer. `check_frozen()` (also the lint tier's J1) refuses any state
whose timestamps exceed T. Bodies are mutable on GitHub; the GraphQL
userContentEdits history is recorded per issue so an edit after T is a
visible caveat, never a silent one.

Needs: gh (authenticated, read-only), the ADMC clone named in
sources.yaml (for the historical spec docs at the refinement commits).
"""

import json
import os
import re
import subprocess
import sys

S = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "emilyorz", "ADMC"

# Fixture definitions — the mandate's items, pins corrected (design §0):
# the mandate's SHAs were the spec-refinement commits themselves, whose
# trees already hold the questions; the pin is main at T, i.e. their
# parent. F-51's T is INCLUSIVE of the human's `Summary` comment (the
# trigger); the bot's summary four minutes later is the answer and drops.
FIXTURES = {
    "F-63": {
        "issue": 63, "T": "2026-08-12T16:16:16Z", "pin": "d188a207562a",
        "refinement_commit": "b2a0fca9a3cb", "identity": "bot",
        "command": "/roz-gate:next-stage 63", "timeout": 3600,
        "include_issues": [63, 61, 54], "include_prs": [60],
        "surface": "spec-cr", "criteria": ["P1", "P2", "N1", "N5"],
        "question_cap": 16,
        "historical": {"count": 8, "recall": "2/2", "precision": "0/2",
                       "note": "the historical run raised N1 and N5 as questions"},
        "historical_output": {"pr": 64, "roots_before": "2026-08-12T16:17:02Z",
                              "spec_path": "specs/63/spec.md"},
    },
    "F-54": {
        "issue": 54, "T": "2026-08-09T06:14:57Z", "pin": "d2ded1269c1c",
        "refinement_commit": "b198ac57c982", "identity": "user",
        "command": "/roz-gate:next-stage 54", "timeout": 3600,
        "include_issues": [54], "include_prs": [],
        "surface": "spec-cr", "criteria": ["P8"],
        "question_cap": 20,
        "historical": {"count": 10, "recall": "1/1", "precision": "n/a",
                       "note": "P8 is graded on the batch"},
        "historical_output": {"pr": 60, "roots_before": "2026-08-09T06:16:11Z",
                              "spec_path": "specs/54/spec.md"},
    },
    "F-67": {
        "issue": 67, "T": "2026-08-14T14:07:30Z", "pin": "d188a207562a",
        "refinement_commit": None, "identity": "bot",
        "command": "/roz-gate:patrol", "timeout": 1800,
        "include_issues": [67], "include_prs": [],
        "surface": "issue", "criteria": ["P12"],
        "question_cap": 1,
        "historical": {"count": 5, "recall": "1/1", "precision": "cap fail (5 > 1)",
                       "note": "the five questions were moot; the finding was the value"},
        "historical_output": {"issue_comment": 5294772137},
    },
    "F-51": {
        "issue": 51, "T": "2026-08-08T10:40:53Z", "pin": "d2ded1269c1c",
        "refinement_commit": None, "identity": "user",
        "command": "/roz-gate:patrol", "timeout": 1800,
        "include_issues": [51], "include_prs": [],
        "surface": "issue", "criteria": ["N10"],
        "question_cap": 0,
        "historical": {"count": 0, "recall": "n/a", "precision": "1/1",
                       "note": "correct silence: zero questions, summary with assumptions"},
        "historical_output": {"issue_comment": 5225755809},
    },
}


def gh(*args):
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("gh api %s failed: %s" % (" ".join(args), out.stderr.strip()))
    return json.loads(out.stdout)


def paged(path):
    rows = []
    page = 1
    while True:
        chunk = gh("%s?per_page=100&page=%d" % (path, page))
        rows.extend(chunk)
        if len(chunk) < 100:
            return rows
        page += 1


def login(user):
    return (user or {}).get("login", "")


def issue_at(n, T):
    """One issue frozen at T: body verbatim, comments <= T, labels and
    assignees replayed from the timeline up to T."""
    iss = gh("repos/%s/%s/issues/%d" % (OWNER, REPO, n))
    labels, assignees = [], []
    for ev in paged("repos/%s/%s/issues/%d/timeline" % (OWNER, REPO, n)):
        if ev.get("created_at", "") > T:
            continue
        kind = ev.get("event")
        if kind == "labeled":
            name = ev["label"]["name"]
            if name not in labels:
                labels.append(name)
        elif kind == "unlabeled":
            name = ev["label"]["name"]
            if name in labels:
                labels.remove(name)
        elif kind == "assigned":
            a = login(ev.get("assignee"))
            if a and a not in assignees:
                assignees.append(a)
        elif kind == "unassigned":
            a = login(ev.get("assignee"))
            if a in assignees:
                assignees.remove(a)
    closed_at = iss.get("closed_at")
    comments = [
        {"id": c["id"], "author": login(c.get("user")), "body": c["body"],
         "createdAt": c["created_at"]}
        for c in paged("repos/%s/%s/issues/%d/comments" % (OWNER, REPO, n))
        if c["created_at"] <= T
    ]
    edits = gh("graphql", "-f", "query=%s" % (
        '{repository(owner:"%s",name:"%s"){issue(number:%d){lastEditedAt '
        'userContentEdits(first:50){nodes{editedAt}}}}}' % (OWNER, REPO, n)))
    edit_times = [e["editedAt"] for e in
                  edits["data"]["repository"]["issue"]["userContentEdits"]["nodes"]]
    return {
        "title": iss["title"], "body": iss["body"] or "",
        "author": login(iss.get("user")), "createdAt": iss["created_at"],
        "state": "closed" if closed_at and closed_at <= T else "open",
        "labels": labels, "assignees": assignees, "comments": comments,
        "_body_edits_after_T": [t for t in edit_times if t > T],
    }


def pr_at(n, T):
    """One PR frozen at T (None if it did not exist yet). Review threads
    are rebuilt from the flat review-comment list (reply chains → root);
    a thread counts as resolved at T only if an agent `✅ [` reply landed
    by T — GitHub exposes no resolution timestamp."""
    pr = gh("repos/%s/%s/pulls/%d" % (OWNER, REPO, n))
    if pr["created_at"] > T:
        return None
    closed = pr.get("closed_at")
    merged = pr.get("merged_at")
    state = "OPEN"
    if merged and merged <= T:
        state = "MERGED"
    elif closed and closed <= T:
        state = "CLOSED"
    flat = [c for c in paged("repos/%s/%s/pulls/%d/comments" % (OWNER, REPO, n))
            if c["created_at"] <= T]
    by_id = {c["id"]: c for c in flat}

    def root_of(c):
        while c.get("in_reply_to_id") in by_id:
            c = by_id[c["in_reply_to_id"]]
        return c["id"]

    threads = {}
    for c in sorted(flat, key=lambda c: c["created_at"]):
        r = root_of(c)
        t = threads.setdefault(r, {"id": "T%d" % r, "isResolved": False,
                                   "path": by_id[r].get("path"),
                                   "line": by_id[r].get("line"), "comments": []})
        t["comments"].append({"databaseId": c["id"], "author": login(c.get("user")),
                              "body": c["body"], "createdAt": c["created_at"]})
        if c["body"].startswith("✅ ["):
            t["isResolved"] = True
    reviews = [
        {"id": r["id"], "state": r["state"], "body": r.get("body") or "",
         "author": login(r.get("user")), "submitted_at": r.get("submitted_at", "")}
        for r in paged("repos/%s/%s/pulls/%d/reviews" % (OWNER, REPO, n))
        if r.get("submitted_at", "") <= T and r.get("state") != "PENDING"
    ]
    comments = [
        {"id": c["id"], "author": login(c.get("user")), "body": c["body"],
         "created_at": c["created_at"]}
        for c in paged("repos/%s/%s/issues/%d/comments" % (OWNER, REPO, n))
        if c["created_at"] <= T
    ]
    return {
        "number": n, "title": pr["title"], "body": pr.get("body") or "",
        "state": state, "isDraft": bool(pr.get("draft")),
        "headRefName": pr["head"]["ref"], "baseRefName": pr["base"]["ref"],
        "createdAt": pr["created_at"],
        "threads": list(threads.values()), "reviews": reviews, "comments": comments,
    }


def historical_output(fx, admc):
    """The real agent output for the judge red-proof: root thread bodies
    on the spec CR (in posting order) + the spec's Open Questions at the
    refinement commit; or the intake comment body."""
    h = fx["historical_output"]
    parts = []
    if "pr" in h:
        roots = [c for c in paged("repos/%s/%s/pulls/%d/comments" % (OWNER, REPO, h["pr"]))
                 if not c.get("in_reply_to_id") and c["created_at"] < h["roots_before"]]
        for c in sorted(roots, key=lambda c: c["created_at"]):
            parts.append("--- [thread-post-inline] ---\n" + c["body"].strip())
        spec = subprocess.run(["git", "-C", admc, "show",
                               "%s:%s" % (fx["refinement_commit"], h["spec_path"])],
                              capture_output=True, text=True)
        if spec.returncode != 0:
            sys.exit("cannot read %s at %s in %s" % (h["spec_path"], fx["refinement_commit"], admc))
        parts.append("--- [spec.md: Open Questions] ---\n" + open_questions(spec.stdout))
    else:
        c = gh("repos/%s/%s/issues/comments/%d" % (OWNER, REPO, h["issue_comment"]))
        parts.append("--- [issue-comment] ---\n" + c["body"].strip())
    return "\n\n".join(parts) + "\n"


def open_questions(spec_text):
    m = re.search(r"^## Open Questions\s*$(.*?)(?=^## |\Z)", spec_text, re.M | re.S)
    return m.group(1).strip() if m else ""


def check_frozen(cases_dir):
    """Every timestamp in every state.json is <= its fixture's T. Returns
    the list of violations (empty = frozen). Lint J1 calls this."""
    bad = []
    for name in sorted(os.listdir(cases_dir)):
        d = os.path.join(cases_dir, name)
        try:
            fx = json.load(open(os.path.join(d, "fixture.json"), encoding="utf-8"))
            st = json.load(open(os.path.join(d, "state.json"), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        T = fx["T"]
        for n, iss in st.get("issues", {}).items():
            if iss.get("createdAt", "") > T:
                bad.append("%s: issue %s created after T" % (name, n))
            for c in iss.get("comments", []):
                if c.get("createdAt", "") > T:
                    bad.append("%s: issue %s comment %s after T" % (name, n, c.get("id")))
        for n, pr in st.get("prs", {}).items():
            if pr.get("createdAt", "") > T:
                bad.append("%s: pr %s created after T" % (name, n))
            for t in pr.get("threads", []):
                for c in t.get("comments", []):
                    if c.get("createdAt", "") > T:
                        bad.append("%s: pr %s thread comment %s after T" % (name, n, c.get("databaseId")))
            for r in pr.get("reviews", []):
                if r.get("submitted_at", "") > T:
                    bad.append("%s: pr %s review %s after T" % (name, n, r.get("id")))
            for c in pr.get("comments", []):
                if c.get("created_at", "") > T:
                    bad.append("%s: pr %s comment %s after T" % (name, n, c.get("id")))
    return bad


def main():
    admc = None
    for line in open(os.path.join(S, "sources.yaml"), encoding="utf-8"):
        m = re.match(r"^admc:\s*(.+?)\s*$", line)
        if m:
            admc = os.path.expanduser(m.group(1))
    if not admc or not os.path.isdir(admc):
        sys.exit("sources.yaml: admc path missing or not a directory")
    only = sys.argv[1:] or sorted(FIXTURES)
    for name in only:
        fx = FIXTURES[name]
        T = fx["T"]
        cdir = os.path.join(S, "cases", name)
        os.makedirs(cdir, exist_ok=True)
        state = {"repo": {"owner": OWNER, "name": REPO},
                 "agent_login": "roz-gatekeeper", "issues": {}, "prs": {}}
        caveats = []
        for n in fx["include_issues"]:
            iss = issue_at(n, T)
            edits = iss.pop("_body_edits_after_T")
            if edits:
                caveats.append("issue %d body edited after T: %s" % (n, ", ".join(edits)))
            state["issues"][str(n)] = iss
        for n in fx["include_prs"]:
            pr = pr_at(n, T)
            if pr:
                state["prs"][str(n)] = pr
        with open(os.path.join(cdir, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        main_issue = state["issues"][str(fx["issue"])]
        # The historical run's OWN `status: processing` lock landed minutes
        # before T (it is the run that produced the questions); the SUT
        # takes its own lock, so the fixture starts unlocked.
        if "status: processing" in main_issue["labels"]:
            main_issue["labels"].remove("status: processing")
            with open(os.path.join(cdir, "state.json"), "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=1)
        fixture = {k: v for k, v in fx.items() if k != "historical_output"}
        fixture.update({"frozen_at": T, "labels_at_T": main_issue["labels"],
                        "assignees_at_T": main_issue["assignees"],
                        "comments_at_T": len(main_issue["comments"]),
                        "caveats": caveats})
        with open(os.path.join(cdir, "fixture.json"), "w", encoding="utf-8") as f:
            json.dump(fixture, f, ensure_ascii=False, indent=1)
        hdir = os.path.join(S, "redproof", "historical")
        os.makedirs(hdir, exist_ok=True)
        with open(os.path.join(hdir, name + ".md"), "w", encoding="utf-8") as f:
            f.write(historical_output(fx, admc))
        print("%s: issue #%d at %s — labels %s, assignees %s, %d comments; %d issues, %d prs; caveats: %s"
              % (name, fx["issue"], T, main_issue["labels"], main_issue["assignees"],
                 len(main_issue["comments"]), len(state["issues"]), len(state["prs"]),
                 caveats or "none"))
    bad = check_frozen(os.path.join(S, "cases"))
    if bad:
        sys.exit("NOT FROZEN:\n  " + "\n  ".join(bad))
    print("frozen: every timestamp <= T")


if __name__ == "__main__":
    main()
