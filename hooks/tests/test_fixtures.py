"""Every fixture carries the fields guard_gate.py reads, typed as it reads them.

guard_gate reads forge JSON with .get() defaults, so a misnamed field (`login`
where GitLab says `username`) is silently empty and the case tests a different
situation than its name claims. The shapes below are exactly what
check_github_summary / check_gitlab_summary read; a guard that reads a new
field extends them in the same commit.
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


CHECKS = {"gh_": check_gh, "glab_issue_": check_glab_issue, "glab_notes_": check_glab_notes}


class FixtureShapes(unittest.TestCase):
    def test_shapes(self):
        for path in sorted(FX.glob("*.json")):
            with self.subTest("fixture shape: %s" % path.name):
                check = next((c for p, c in CHECKS.items() if path.name.startswith(p)), None)
                self.assertIsNotNone(check, "unknown prefix — gh_ / glab_issue_ / glab_notes_")
                check(json.loads(path.read_text()))
