#!/usr/bin/env python3
"""The Workflow Value pilot's pure functions (#259, `evals/workflow-value.md`).

No model, no forge, no ADMC: everything here takes text, journal entries
and transcript tool-use blocks and returns data. `run_judgment.py` calls
it for the baseline arm and the paired report; lint J3 runs its tests.
"""

import os
import re

S = os.path.dirname(os.path.abspath(__file__))
SECTION_START = "## Development Workflow (Roz Gate)"
BASELINE_SECTION = "## Project commands"
# the facts the loop's config block holds that an engineer on the
# repository would know anyway — never the loop's own keys
ORDINARY = (("forge", "forge"), ("test", "test"), ("acceptance_dir", "acceptance tests live in"),
            ("acceptance_test", "acceptance tests"), ("env_sync", "environment sync"),
            ("lockfile", "lockfile"), ("lockfile_regen", "regenerate the lockfile"))
# words that would teach the baseline the loop. Closed list; a hit is a
# defect in the prompt, not a judgment call.
LOOP_WORDS = ("roz", "gate", "spec", "stage", "seat", "patrol", "persona", "intake",
              "track:", "status:", "ready-for", "blind", "fidelity")
QUESTION_UNITS = {"treatment": "Q-ids", "baseline": "asking comments"}


def parse_config(text):
    """The `### Roz Gate config` block's `- key: value` lines."""
    m = re.search(r"^### Roz Gate config\s*$(.*?)(?=^#{1,3} |\Z)", text, re.M | re.S)
    out = {}
    for line in (m.group(1) if m else "").splitlines():
        kv = re.match(r"^- ([a-z_]+):\s*(.*)$", line.strip())
        if kv:
            out[kv.group(1)] = kv.group(2).strip()
    return out


def baseline_claude_md(text, cfg):
    """The repository's CLAUDE.md as the baseline sees it: the loop's
    section removed, and the ordinary facts its config held — how to test,
    where acceptance tests live — kept in a neutral block. Idempotent."""
    for start in (SECTION_START, BASELINE_SECTION):
        if start in text:
            text = text[:text.index(start)]
    lines = ["- %s: `%s`" % (label, cfg[key]) for key, label in ORDINARY
             if cfg.get(key) and cfg[key] not in ("true", "false", "''", '""')]
    block = BASELINE_SECTION + "\n\n" + "\n".join(lines) + "\n"
    return text.rstrip("\n") + "\n\n" + block


def baseline_prompt(issue):
    with open(os.path.join(S, "baseline-prompt.md"), encoding="utf-8") as f:
        return f.read().strip().replace("{issue}", str(issue))


def loop_words(text):
    low = text.lower()
    return [w for w in LOOP_WORDS if re.search(r"(?<![a-z])%s" % re.escape(w), low)]


def baseline_outcome(journal, issue):
    """What the baseline did, from the forge journal alone. `asking
    comments` are the comments it wrote on the issue that contain a
    question — a different unit from the loop's Q-ids, and reported as
    such. A round trip is counted when it asked: the human must answer
    before the work can be right."""
    n = str(issue)
    comments = [e.get("body") or "" for e in journal
                if e.get("write") and e.get("route") == "issue-comment"
                and str(e.get("issue")) == n]
    prs = sum(1 for e in journal if e.get("write") and e.get("route") == "pr-create")
    asking = sum(1 for body in comments if "?" in body or "？" in body)
    outcome = {(True, True): "asked and finished", (True, False): "asked",
               (False, True): "finished", (False, False): "neither"}[(asking > 0, prs > 0)]
    return {"outcome": outcome, "comments": len(comments), "asking_comments": asking,
            "prs_opened": prs, "human_round_trips": 1 if asking else 0}


def cost(tool_uses, cfg):
    """Secondary cost from the transcript's tool-use blocks: every call,
    the agent dispatches, and the suite runs — Bash commands that carry
    one of the configured test commands."""
    cmds = [cfg[k] for k in ("test", "acceptance_test")
            if cfg.get(k) and cfg[k] not in ("true", "false")]
    uses = list(tool_uses)
    suites = sum(1 for u in uses if u.get("name") == "Bash"
                 and any(c in ((u.get("input") or {}).get("command") or "") for c in cmds))
    return {"tool_calls": len(uses),
            "dispatches": sum(1 for u in uses if u.get("name") in ("Task", "Agent")),
            "suite_runs": suites}


def paired_fields(polarity, answers, questions):
    """What one valid run surfaced, from its verdicts (`{criterion: yes |
    no | judge-invalid}`) and its question count — the same rule for both
    arms:

    - a P criterion judged yes is found, judged no is missed;
    - an N criterion judged yes is an immaterial item raised;
    - N10 ("silence was right") is raised exactly when the run asked
      anything. Its judged half — did the loop's summary record its
      assumptions — belongs to the tier's precision, not to this field;
    - a judge-invalid verdict is neither: the criterion is **unscored**,
      and a run with one is never paired. The judge failing is not the
      arm missing a decision, nor the arm staying silent."""
    found, missed, raised, unscored = [], [], [], []
    for c in sorted(answers):
        ans = answers[c]
        if c == "N10":
            raised += [c] if questions else []
        elif ans not in ("yes", "no"):
            unscored.append(c)
        elif polarity.get(c) == "P":
            (found if ans == "yes" else missed).append(c)
        elif ans == "yes":
            raised.append(c)
    return {"important_found": found, "important_missed": missed,
            "immaterial_raised": raised, "unscored": unscored}


# ---- the retrospective record ------------------------------------------------
RETRO_FIELDS = ("issue", "value_shape", "why_selected", "important", "immaterial",
                "known_rework", "accepted_outcome", "unknown", "reviewed_by", "reviewed_on")


def reviewed(rec):
    return bool(rec.get("reviewed_by")) and bool(
        re.match(r"^\d{4}-\d{2}-\d{2}$", str(rec.get("reviewed_on"))))


def validate_retrospective(rec, fx, polarity):
    """Defects, as text. The record is the gold: `important` and
    `immaterial` are the fixture's P and N criteria and nothing else; what
    the history does not settle is the word `unknown`, and is listed. The
    review is the gate holder's signature on the whole record — null until
    then, never half-stamped."""
    bad = ["missing %s" % k for k in RETRO_FIELDS if k not in rec]
    if bad:
        return bad
    if rec["issue"] != fx["issue"]:
        bad.append("issue %r is not the fixture's %r" % (rec["issue"], fx["issue"]))
    for field, pol in (("important", "P"), ("immaterial", "N")):
        want = sorted(c for c in fx["criteria"] if polarity.get(c) == pol)
        if sorted(rec[field]) != want:
            bad.append("%s is %s, the fixture's %s criteria are %s"
                       % (field, sorted(rec[field]), pol, want))
    for field in ("value_shape", "why_selected", "known_rework", "accepted_outcome"):
        if not isinstance(rec[field], str) or not rec[field].strip():
            bad.append("%s is empty — write it, or the word unknown" % field)
        elif rec[field].strip() == "unknown" and field not in rec["unknown"]:
            bad.append("%s is unknown but not listed under unknown" % field)
    if not reviewed(rec) and not (rec["reviewed_by"] is None and rec["reviewed_on"] is None):
        bad.append("half-stamped review — reviewed_by and reviewed_on are both null, or a "
                   "name and a YYYY-MM-DD date")
    return bad


# ---- the paired report ----------------------------------------------------------
def _ids(xs):
    return ", ".join(xs) if xs else "—"


def _row(arm, r):
    c, t = r.get("cost_counts") or {}, r.get("tokens") or {}
    return ("   %-10s found %s · missed %s · immaterial raised %s\n"
            "              %s %s · %s · round trips %s\n"
            "              cost: tokens %s in / %s out · tool calls %s · dispatches %s · "
            "suite runs %s"
            % (arm, _ids(r["important_found"]), _ids(r["important_missed"]),
               _ids(r["immaterial_raised"]), r["questions"], r["question_unit"],
               r["outcome"], r["human_round_trips"], t.get("in", "?"), t.get("out", "?"),
               c.get("tool_calls", "?"), c.get("dispatches", "?"), c.get("suite_runs", "?")))


def paired(cases):
    """Per issue, the arms side by side, then the raw counts behind the
    ratios. An issue is paired only when its retrospective record is
    reviewed and both arms have a valid run; anything else is listed with
    the reason and contributes no number — a run with a judge-invalid
    criterion included. Nothing is summed across issues."""
    out = []
    for name in sorted(cases):
        c = cases[name]
        rec = c["retrospective"]
        out.append("== %s — %s" % (name, rec.get("value_shape", "")))
        if not reviewed(rec):
            out.append("   UNPAIRED — the retrospective record is not reviewed "
                       "(reviewed_by / reviewed_on are null)")
            continue
        blocked = []
        for arm in ("baseline", "treatment"):
            runs = c.get(arm) or []
            if not runs:
                blocked.append("%s: no run" % arm)
            for i, r in enumerate(runs, 1):
                if not r.get("valid"):
                    blocked.append("%s run-%d INVALID: %s" % (arm, i, r.get("invalid_reason")))
                elif r.get("unscored"):
                    blocked.append("%s run-%d unscored: judge-invalid on %s"
                                   % (arm, i, ", ".join(r["unscored"])))
        if blocked:
            out.append("   UNPAIRED — " + "; ".join(blocked))
            continue
        for arm in ("baseline", "treatment"):
            for r in c[arm]:
                out.append(_row(arm, r))
        for arm in ("baseline", "treatment"):
            for r in c[arm]:
                found, n_imp = len(r["important_found"]), len(rec["important"])
                out.append("   %-10s important surfaced %d/%d · immaterial raised %d/%d"
                           % (arm, found, n_imp, len(r["immaterial_raised"]),
                              len(rec["immaterial"])))
        if rec.get("unknown"):
            out.append("   the record leaves unknown: %s" % ", ".join(rec["unknown"]))
    return "\n".join(out)
