#!/usr/bin/env python3
"""Unit tests for the Workflow Value pilot's pure functions (#259) — no
model, no ADMC, no forge. Run directly, or by lint J3 on every push.

    python3 evals/judgment/tests/test_workflow_value.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CLAUDE_MD = """# ADMC

Java 21, Spring Boot. Run things from the repo root.

## Development Workflow (Roz Gate)

<!-- roz-gate workflow-template v7 -->
Use `/roz-gate:patrol` to drive every issue through the gated loop.

### Roz Gate config

- forge: github
- test: ./mvnw -q test
- acceptance_dir: src/test/java/acceptance
- acceptance_test: ./mvnw -q verify -Pacceptance
- env_sync: true
- lockfile: pom.xml
- lockfile_regen: true
- specs_dir: specs

### Roz Gate personas

- product: product
- qa: qa
"""


def git(work, *args):
    return subprocess.run(["git", "-C", work] + list(args), capture_output=True,
                          text=True).stdout


def history_repo():
    """A pin whose history names the loop: an earlier "Gated Loop" section,
    then the migration to the Roz Gate section; a tag, a side branch and a
    reflog besides — what ADMC's clone looks like at the pin (#259)."""
    d = tempfile.mkdtemp()
    env = dict(os.environ, GIT_AUTHOR_NAME="a", GIT_AUTHOR_EMAIL="a@a",
               GIT_COMMITTER_NAME="a", GIT_COMMITTER_EMAIL="a@a")
    subprocess.run(["bash", "-c",
                    "git init -q -b main . && printf '# ADMC\\n\\n## Gated Loop\\nstages\\n' "
                    "> CLAUDE.md && mkdir src && echo 'class A {}' > src/A.java && git add -A "
                    "&& git commit -qm 'docs: the Gated Loop section' && git tag v0 "
                    "&& git checkout -qb side && echo x > side.txt && git add -A "
                    "&& git commit -qm 'side work' && git checkout -q main"],
                   cwd=d, env=env, check=True, capture_output=True)
    with open(os.path.join(d, "CLAUDE.md"), "w") as f:
        f.write(CLAUDE_MD)
    subprocess.run(["bash", "-c", "git add -A && git commit -qm "
                    "'docs: migrate the workflow section to Roz Gate'"],
                   cwd=d, env=env, check=True, capture_output=True)
    return d


def flattened_checks(check, wv):
    """Ruling (b), 2026-11-14: the baseline sandbox is ONE root commit
    carrying the transformed tree — nothing in its history, refs, reflog or
    objects holds the loop's section (the F-51 calibration's seat read it
    from `git show HEAD`)."""
    flatten = getattr(wv, "flatten_history", None)
    work = history_repo()
    try:
        cfg = wv.parse_config(CLAUDE_MD)
        with open(os.path.join(work, "CLAUDE.md"), "w") as f:
            f.write(wv.baseline_claude_md(CLAUDE_MD, cfg))
        sha = flatten(work) if flatten else None
        commits = git(work, "rev-list", "--all").split()
        check("baseline sandbox: exactly one commit, the one returned, with no parent",
              commits == [sha] and sha
              and git(work, "rev-list", "--parents", "-n1", sha).split() == [sha])
        check("baseline sandbox: main is the only ref",
              git(work, "for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]
              and git(work, "symbolic-ref", "HEAD").strip() == "refs/heads/main")
        check("baseline sandbox: the tree is the transformed one (commands kept, section gone)",
              "./mvnw -q test" in git(work, "show", "HEAD:CLAUDE.md")
              and wv.SECTION_START not in git(work, "show", "HEAD:CLAUDE.md")
              and git(work, "show", "HEAD:src/A.java").strip() == "class A {}"
              and not git(work, "status", "--porcelain"))
        meta = git(work, "log", "-1", "--format=%an %ae %cn %ce%n%B")
        check("baseline sandbox: the commit's message and identity carry no loop vocabulary "
              "(%s)" % ", ".join(wv.loop_words(meta)), meta.strip() and not wv.loop_words(meta))
        every = set(git(work, "cat-file", "--batch-all-objects",
                        "--batch-check=%(objectname)").split())
        reach = {line.split()[0] for line in git(work, "rev-list", "--objects", "--all")
                 .splitlines() if line.strip()}
        check("baseline sandbox: no object the commit does not reach (no old commit, no old "
              "CLAUDE.md, nothing for fsck --lost-found to find)", every and every == reach)
        hits = []
        gitdir = os.path.join(work, ".git")
        for root, _, files in os.walk(gitdir):
            if os.path.relpath(root, gitdir).split(os.sep)[0] == "objects":
                continue
            for name in files:
                text = open(os.path.join(root, name), "rb").read().decode("utf-8", "replace")
                low = text.lower()
                if "roz" in low or "gated loop" in low or wv.SECTION_START in text:
                    hits.append(os.path.relpath(os.path.join(root, name), gitdir))
        check("baseline sandbox: no file under .git names the removed section (%s)"
              % ", ".join(hits), not hits)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def tool(name, **inp):
    return {"type": "tool_use", "name": name, "input": inp}


def run():
    """[(name, ok)] — every check, so the caller prints them all."""
    out = []

    def check(name, ok):
        out.append((name, bool(ok)))

    try:
        import workflow_value as wv
    except ImportError:
        return [("workflow_value imports", False)]

    cfg = wv.parse_config(CLAUDE_MD)
    check("config: the test commands are read",
          cfg.get("test") == "./mvnw -q test"
          and cfg.get("acceptance_test") == "./mvnw -q verify -Pacceptance")
    base = wv.baseline_claude_md(CLAUDE_MD, cfg)
    check("baseline CLAUDE.md: the loop's section is gone",
          "Roz Gate" not in base and "roz-gate" not in base and "personas" not in base
          and "specs_dir" not in base)
    check("baseline CLAUDE.md: the project's own text stays", "Java 21, Spring Boot." in base)
    check("baseline CLAUDE.md: the ordinary commands stay",
          "./mvnw -q test" in base and "./mvnw -q verify -Pacceptance" in base
          and "src/test/java/acceptance" in base)
    check("baseline CLAUDE.md: idempotent", wv.baseline_claude_md(base, cfg) == base)
    check("baseline CLAUDE.md: a file with no section gains only the commands",
          wv.baseline_claude_md("# X\n", cfg).startswith("# X\n")
          and "./mvnw -q test" in wv.baseline_claude_md("# X\n", cfg))

    flattened_checks(check, wv)

    prompt = wv.baseline_prompt(63)
    check("baseline prompt: names the issue", "#63" in prompt)
    check("baseline prompt: carries no loop vocabulary", not wv.loop_words(prompt))
    check("loop_words: sees a planted stage",
          wv.loop_words("First write a spec, then ask.") == ["spec"])

    asked = [{"route": "issue-comment", "write": True, "issue": "63",
              "body": "Should membership be its own table?"},
             {"route": "issue-view", "issue": "63"}]
    done = [{"route": "pr-create", "write": True, "pr": "101", "head": "fix/63"}]
    for name, journal, want in (
            ("asked and stopped", asked, ("asked", 1, 1)),
            ("finished with a pull request", done, ("finished", 0, 0)),
            ("asked and finished", asked + done, ("asked and finished", 1, 1)),
            ("neither", [], ("neither", 0, 0))):
        o = wv.baseline_outcome(journal, 63)
        check("baseline outcome: %s" % name,
              (o["outcome"], o["asking_comments"], o["human_round_trips"]) == want)
    check("baseline outcome: a statement is not an asking comment",
          wv.baseline_outcome([{"route": "issue-comment", "write": True, "issue": "63",
                                "body": "Done. See the PR."}], 63)["asking_comments"] == 0)
    check("baseline outcome: another issue's comment is not counted",
          wv.baseline_outcome([{"route": "issue-comment", "write": True, "issue": "64",
                                "body": "Why?"}], 63)["comments"] == 0)

    uses = [tool("Bash", command="./mvnw -q test"), tool("Read", file_path="a"),
            tool("Bash", command="cd x && ./mvnw -q verify -Pacceptance 2>&1 | tail -5"),
            tool("Task", prompt="p"), tool("Agent", prompt="p"), tool("Bash", command="ls")]
    c = wv.cost(uses, cfg)
    check("cost: tool calls, dispatches, suite runs",
          (c["tool_calls"], c["dispatches"], c["suite_runs"]) == (6, 2, 2))
    check("cost: `true` as a test command never counts",
          wv.cost([tool("Bash", command="true")], {"test": "true"})["suite_runs"] == 0)

    fx = {"issue": 63, "criteria": ["P1", "P2", "N1", "N5"]}
    pol = {"P1": "P", "P2": "P", "N1": "N", "N5": "N"}
    good = {"issue": 63, "value_shape": "a spec ambiguity that changed the design",
            "why_selected": "x", "important": ["P1", "P2"], "immaterial": ["N1", "N5"],
            "known_rework": "unknown", "accepted_outcome": "unknown",
            "unknown": ["known_rework", "accepted_outcome"],
            "reviewed_by": None, "reviewed_on": None}
    check("retrospective: a complete unreviewed record validates",
          not wv.validate_retrospective(good, fx, pol))
    check("retrospective: important must be the fixture's P criteria",
          wv.validate_retrospective(dict(good, important=["P1"]), fx, pol))
    check("retrospective: an N item listed as important is a defect",
          wv.validate_retrospective(dict(good, important=["P1", "P2", "N1"],
                                         immaterial=["N5"]), fx, pol))
    check("retrospective: 'unknown' must be listed under unknown",
          wv.validate_retrospective(dict(good, unknown=[]), fx, pol))
    check("retrospective: a half-stamped review is a defect",
          wv.validate_retrospective(dict(good, reviewed_by="Paul Liang"), fx, pol))
    check("retrospective: reviewed() is false until both fields are set",
          not wv.reviewed(good)
          and wv.reviewed(dict(good, reviewed_by="Paul Liang", reviewed_on="2026-11-13")))

    res_t = {"valid": True, "important_found": ["P1"], "important_missed": ["P2"],
             "immaterial_raised": ["N5"], "questions": 14, "question_unit": "Q-ids",
             "outcome": "gate", "human_round_trips": 1,
             "tokens": {"in": 400000, "out": 9000},
             "cost_counts": {"tool_calls": 120, "dispatches": 3, "suite_runs": 0}}
    res_b = dict(res_t, important_found=[], important_missed=["P1", "P2"],
                 immaterial_raised=[], questions=0, question_unit="asking comments",
                 outcome="finished", human_round_trips=0,
                 tokens={"in": 90000, "out": 4000},
                 cost_counts={"tool_calls": 40, "dispatches": 0, "suite_runs": 2})
    rev = dict(good, reviewed_by="Paul Liang", reviewed_on="2026-11-13")
    real_paired = wv.paired

    def paired(cases):      # a crash is a failed check with a name, never a dead suite
        try:
            return real_paired(cases)
        except Exception as e:  # noqa: BLE001
            return "RAISED %s" % type(e).__name__
    text = paired({"F-63": {"retrospective": rev, "treatment": [res_t], "baseline": [res_b]}})
    check("paired: both arms on the issue's block",
          "F-63" in text and "treatment" in text and "baseline" in text)
    check("paired: found and missed by id", "found P1" in text and "missed P1, P2" in text)
    check("paired: the question units are named", "Q-ids" in text and "asking comments" in text)
    check("paired: the raw counts behind the ratios are printed",
          "1/2" in text and "0/2" in text)
    check("paired: no cross-issue total", "total" not in text.lower()
          and "overall" not in text.lower())
    bad_b = {"valid": False, "invalid_reason": "forge stub hit 2 UNKNOWN route(s)"}
    text = paired({"F-63": {"retrospective": rev, "treatment": [res_t], "baseline": [bad_b]}})
    check("paired: an INVALID arm unpairs the issue and says why",
          "UNPAIRED" in text and "UNKNOWN route" in text and "found P1" not in text)
    text = paired({"F-63": {"retrospective": good, "treatment": [res_t], "baseline": [res_b]}})
    check("paired: an unreviewed retrospective is never paired",
          "not reviewed" in text and "found P1" not in text)
    # codex review, PR #287 — what a run surfaced, from the verdicts alone
    def fields(answers, count):
        try:
            return wv.paired_fields(pol10, answers, count)
        except Exception as e:  # noqa: BLE001
            return {"error": type(e).__name__}

    pol10 = {"P1": "P", "P2": "P", "N1": "N", "N5": "N", "N10": "N"}
    f = fields({"P1": "yes", "P2": "no", "N1": "yes", "N5": "no"}, 14)
    check("paired fields: yes is found, no is missed, a raised N is raised",
          (f.get("important_found"), f.get("important_missed"), f.get("immaterial_raised"),
           f.get("unscored")) == (["P1"], ["P2"], ["N1"], []))
    f = fields({"P1": "judge-invalid", "P2": "yes", "N1": "judge-invalid", "N5": "no"}, 3)
    check("paired fields: a judge-invalid verdict is unscored — never missed, never silent",
          (f.get("important_found"), f.get("important_missed"), f.get("immaterial_raised"),
           f.get("unscored")) == (["P2"], [], [], ["N1", "P1"]))
    # N10 — "silence was right" — is raised exactly when a question was
    # asked, in either arm; the loop's summary check is precision's, not this
    check("paired fields: N10 is not raised by a silent run, whatever the judge said",
          fields({"N10": "no"}, 0).get("immaterial_raised") == []
          and fields({"N10": "yes"}, 0).get("immaterial_raised") == [])
    check("paired fields: N10 is raised by a run that asked",
          fields({"N10": "yes"}, 2).get("immaterial_raised") == ["N10"])
    check("paired fields: a judge-invalid N10 does not unscore — it is never judged here",
          fields({"N10": "judge-invalid"}, 0).get("unscored") == [])
    res_u = dict(res_t, important_found=[], important_missed=[], unscored=["P1"])
    text = paired({"F-63": {"retrospective": rev, "treatment": [res_u], "baseline": [res_b]}})
    check("paired: a run with an unscored criterion unpairs the issue and names it",
          "UNPAIRED" in text and "judge-invalid on P1" in text and "missed" not in text)
    return out


if __name__ == "__main__":
    rows = run()
    for name, ok in rows:
        print("%s %s" % ("PASS" if ok else "FAIL", name))
    bad = sum(1 for _, ok in rows if not ok)
    print("%d passed, %d failed" % (len(rows) - bad, bad))
    sys.exit(1 if bad else 0)
