#!/usr/bin/env python3
"""Judgment V1 scoring — pure, no model, no I/O beyond what it is handed.

    score(items, answers) -> {arm: report}

`items`   {id: item}                       the gold records (items/*.json)
`answers` [{item, arm, run, valid, decision, next_action, surfaced,
            key_point}]                    one per scheduled run

An INVALID answer (`valid` false: no parseable JSON, a class or action
outside the vocabulary) is never a judgment class. It is counted — per arm
and per item — and every judgment metric is computed on valid answers
only, each rate carrying its own n (#258, review).

Surfaced = BLOCK or FLAG_AND_CONTINUE. The judged key point is a separate
column and enters no other number.
"""

CLASSES = ("BLOCK", "FLAG_AND_CONTINUE", "NO_FINDING")
SURFACED = ("BLOCK", "FLAG_AND_CONTINUE")


def rate(num, den):
    return {"n": num, "of": den, "rate": (num / den) if den else None}


def validity(rows):
    valid = sum(1 for a in rows if a["valid"])
    return {"scheduled": len(rows), "valid": valid, "invalid": len(rows) - valid,
            "validity_rate": (valid / len(rows)) if rows else None}


def score_arm(items, rows):
    ok = [a for a in rows if a["valid"]]

    def gold(a):
        return items[a["item"]]["gold"]

    should = [a for a in ok if gold(a)["decision"] in SURFACED]
    did = [a for a in ok if a["decision"] in SURFACED]
    hit = [a for a in should if a["decision"] in SURFACED]
    not_block = [a for a in ok if gold(a)["decision"] != "BLOCK"]
    block = [a for a in ok if gold(a)["decision"] == "BLOCK"]
    flag = [a for a in ok if gold(a)["decision"] == "FLAG_AND_CONTINUE"]
    judged = [a for a in hit if a.get("key_point") in ("yes", "no")]
    matrix = {g: {c: 0 for c in CLASSES} for g in CLASSES}
    for a in ok:
        matrix[gold(a)["decision"]][a["decision"]] += 1
    per_item = {}
    for iid in sorted(set(a["item"] for a in rows)):
        mine = [a for a in rows if a["item"] == iid]
        g = items[iid]["gold"]
        per_item[iid] = dict(
            validity(mine), gold=g["decision"],
            decisions=[a["decision"] if a["valid"] else "INVALID" for a in mine],
            class_correct=sum(1 for a in mine if a["valid"] and a["decision"] == g["decision"]),
            action_correct=sum(1 for a in mine
                               if a["valid"] and a["next_action"] == g["next_action"]),
            surfaced_consistent=sum(1 for a in mine
                                    if a["valid"] and bool(a["surfaced"]) == g["surfaced"]))
    return {
        "validity": validity(rows),
        "confusion": matrix,
        "recall": rate(len(hit), len(should)),
        "precision": rate(len(hit), len(did)),
        "false_block": rate(sum(1 for a in not_block if a["decision"] == "BLOCK"),
                            len(not_block)),
        "missed_block": rate(sum(1 for a in block if a["decision"] != "BLOCK"), len(block)),
        "flag_accuracy": rate(sum(1 for a in flag
                                  if a["decision"] == "FLAG_AND_CONTINUE"
                                  and a["next_action"] == gold(a)["next_action"]), len(flag)),
        "key_point": dict(rate(sum(1 for a in judged if a["key_point"] == "yes"), len(judged)),
                          judge_invalid=sum(1 for a in hit
                                            if a.get("key_point") == "judge-invalid")),
        "questions_per_useful": rate(sum(1 for a in ok if a["surfaced"]), len(hit)),
        "items": per_item,
    }


def score(items, answers):
    return {arm: score_arm(items, [a for a in answers if a["arm"] == arm])
            for arm in sorted(set(a["arm"] for a in answers))}


def fmt(r):
    return "—" if r["rate"] is None else "%d/%d (%.0f%%)" % (r["n"], r["of"], 100 * r["rate"])


def render(report):
    """The text report: validity first, then the matrix, then the rates,
    then the arms side by side per item. No blended score and no verdict
    between the arms — on a development set the baseline is a diagnostic
    comparator, never evidence of added value."""
    out = []
    rates = sorted(r["validity"]["validity_rate"] for r in report.values()
                   if r["validity"]["validity_rate"] is not None)
    if len(rates) > 1 and rates[0] != rates[-1]:
        out.append("!! validity differs between arms — read every rate with its n")
    for arm, r in report.items():
        v = r["validity"]
        out.append("== %s: scheduled %d · valid %d · invalid %d · %s"
                   % (arm, v["scheduled"], v["valid"], v["invalid"],
                      "—" if v["validity_rate"] is None else "%.0f%%" % (100 * v["validity_rate"])))
        out.append("   gold \\ answered     " + "  ".join("%-17s" % c for c in CLASSES))
        for g in CLASSES:
            out.append("   %-19s " % g + "  ".join("%-17d" % r["confusion"][g][c]
                                                    for c in CLASSES))
        for key, label in (("recall", "material-decision recall"),
                           ("precision", "material-decision precision"),
                           ("false_block", "false-block rate"),
                           ("missed_block", "missed-block rate"),
                           ("flag_accuracy", "FLAG_AND_CONTINUE accuracy"),
                           ("key_point", "key point named (judged, separate)")
                           ):
            out.append("   %-36s %s" % (label, fmt(r[key])))
        q = r["questions_per_useful"]
        out.append("   %-36s %s" % ("questions per useful decision",
                                    "—" if q["rate"] is None
                                    else "%d/%d (%.2f)" % (q["n"], q["of"], q["rate"])))
        if r["key_point"]["judge_invalid"]:
            out.append("   judge-invalid: %d" % r["key_point"]["judge_invalid"])
    out.append("== per item (valid/scheduled · answered) — diagnostic, not a comparison verdict")
    ids = sorted(set(i for r in report.values() for i in r["items"]))
    for iid in ids:
        cells = []
        for arm, r in report.items():
            it = r["items"].get(iid)
            if it:
                cells.append("%s %d/%d [%s]" % (arm, it["valid"], it["scheduled"],
                                                " ".join(it["decisions"])))
        gold = next(r["items"][iid]["gold"] for r in report.values() if iid in r["items"])
        out.append("   %-26s gold %-17s %s" % (iid, gold, " | ".join(cells)))
    return "\n".join(out)
