"""Every fixture carries the fields guard_gate.py reads, typed as it reads them.

guard_gate reads forge JSON with .get() defaults, so a misnamed field (`login`
where GitLab says `username`) is silently empty and the case tests a different
situation than its name claims. The shapes below are exactly what
check_github_summary / check_gitlab_summary / check_intake_reply read; a
guard that reads a new field extends them in the same commit.
"""

import json
import unittest

from hooktest import FX


def user(obj, key, where):
    assert isinstance(obj, dict) and isinstance(obj.get(key), str), \
        "%s: needs {%r: str}" % (where, key)


def check_gh(d):  # gh issue view <n> --json assignees,author,labels,comments
    assert isinstance(d, dict), "top level: object"
    for a in d["assignees"]:
        user(a, "login", "assignees[]")
    user(d["author"], "login", "author")
    for label in d["labels"]:
        assert isinstance(label.get("name"), str), "labels[]: needs {'name': str}"
    for c in d["comments"]:
        user(c["author"], "login", "comments[].author")
        assert isinstance(c["body"], str) and isinstance(c["createdAt"], str), \
            "comments[]: body, createdAt"


def check_gh_issue(d):  # gh issue view <n> --json assignees,author,labels (rule I)
    assert isinstance(d, dict), "top level: object"
    for a in d["assignees"]:
        user(a, "login", "assignees[]")
    user(d["author"], "login", "author")
    for label in d["labels"]:
        assert isinstance(label.get("name"), str), "labels[]: needs {'name': str}"


def check_gh_rest(d):  # gh api repos/{owner}/{repo}/issues/<n>/comments --paginate (rule I)
    assert isinstance(d, list), "top level: array (pages flattened)"
    for c in d:
        user(c["user"], "login", "[].user")
        assert c["user"].get("type") in (None, "User", "Bot"), "[].user.type: User / Bot"
        assert isinstance(c["body"], str) and isinstance(c["created_at"], str), \
            "[]: body, created_at"


def load_pages(text):
    """`gh api --paginate` / `glab api --paginate` print one JSON array per
    page, back to back."""
    rows, i, dec = [], 0, json.JSONDecoder()
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i == len(text):
            return rows
        page, i = dec.raw_decode(text, i)
        rows.extend(page)


def check_glab_issue(d):  # glab issue view <n> --output json
    assert isinstance(d, dict), "top level: object"
    for a in d["assignees"]:
        user(a, "username", "assignees[]")
    user(d["author"], "username", "author")
    assert all(isinstance(label, str) for label in d["labels"]), "labels: strings"


def check_glab_notes(d):  # glab api projects/:id/issues/<n>/notes
    assert isinstance(d, list), "top level: array"
    for n in d:
        user(n["author"], "username", "[].author")
        assert isinstance(n["body"], str) and isinstance(n["created_at"], str), \
            "[]: body, created_at"
        assert isinstance(n["system"], bool), "[]: system"


# Most specific prefix first: next() takes the first that matches.
CHECKS = {"gh_issue_": check_gh_issue, "gh_rest_": check_gh_rest, "gh_": check_gh,
          "glab_issue_": check_glab_issue, "glab_notes_": check_glab_notes}


class FixtureShapes(unittest.TestCase):
    def test_shapes(self):
        for path in sorted(FX.glob("*.json")):
            with self.subTest("fixture shape: %s" % path.name):
                check = next((c for p, c in CHECKS.items() if path.name.startswith(p)), None)
                self.assertIsNotNone(check, "unknown prefix — gh_ / gh_issue_ / gh_rest_ / "
                                            "glab_issue_ / glab_notes_")
                text = path.read_text()
                paged = check in (check_gh_rest, check_glab_notes)
                check(load_pages(text) if paged else json.loads(text))
