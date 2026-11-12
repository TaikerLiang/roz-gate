#!/usr/bin/env python3
"""Unit tests for the Workflow Value pilot's pure functions (#259) — no
model, no ADMC, no forge. Run directly, or by lint J3 on every push.

    python3 evals/judgment/tests/test_workflow_value.py
"""

import os
import sys

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
    return out


if __name__ == "__main__":
    rows = run()
    for name, ok in rows:
        print("%s %s" % ("PASS" if ok else "FAIL", name))
    bad = sum(1 for _, ok in rows if not ok)
    print("%d passed, %d failed" % (len(rows) - bad, bad))
    sys.exit(1 if bad else 0)
