# roz-check — may an operation start?

Mechanical policy over a `roz-state` snapshot (#134). `roz-state`
(`references/roz-state.md`) says what is observably true; `roz-check`
answers one question about it: **may operation X start from this observed
state — and if not, which precondition says so?** It never runs the
operation, takes no lock and writes nothing. `hooks/state_check.py` is the
policy (pure: a snapshot in, a result out; not a hook); `bin/roz-check` is
its CLI. No command consumes it yet — it is in shadow (§ Shadow adoption).
Lint L16 holds this page and the module equal.

One operation so far: `integrate`.

## A rule's four statuses

| status | meaning |
|---|---|
| `pass` | the precondition holds |
| `fail` | it is known not to hold |
| `unknown` | the fact it needs is `unknown` in the snapshot — neither satisfied nor refuted (`references/roz-state.md` § The unknown invariant); the rule carries the fact's `reason` |
| `not_evaluated` | its prerequisite rule did not pass, so there is nothing to evaluate; it names the prerequisite in `requires` |

**Prerequisites propagate one way.** Prerequisite `pass` → the dependent is
evaluated normally. Prerequisite `fail` → `not_evaluated`. Prerequisite
`unknown` → `not_evaluated`. A prerequisite that is itself `not_evaluated`
is not a pass either, so the rule is transitive: a missing or unknown CR is
**one** root cause, and its thread, record and currentness rules are
`not_evaluated` — never a second failure or a second unknown. A
`not_evaluated` rule is in neither `failed` nor `unknown`.

## The verdict

```text
any rule fails        → ineligible
else any is unknown   → unknown
else                  → eligible
```

A known blocker wins even when another, independent fact is unavailable.

**`unknown` means the operation must not start.** `ineligible` and
`unknown` stay distinct in the result — a known precondition failed,
versus the checker could not establish that all of them pass — but both
mean the evidence does not authorize the operation: no lock is taken.
`may_start` is `true` only for `eligible`, so no caller re-derives that.

## integrate

The entry preconditions of `commands/integrate.md` § 1, as they stand —
none added, none dropped. `integrate` needs the spec **branch**; it never
checks a spec CR at entry, so there is no such rule.

| code | passes when | prerequisite |
|---|---|---|
| `TRACK_NOT_FAST` | `track` is not `fast` (the fast track has no integration stage) | — |
| `NOT_LOCKED` | `processing` is false | — |
| `NOT_BLOCKED` | `blocked` is false | — |
| `ENTRY_STATUS_LEGAL` | `status` is null (no `status:` label) or `in-user-review` | — |
| `SPEC_BRANCH_EXISTS` | `branches.spec` is observed | — |
| `IMPLEMENTATION_CR_EXISTS` | `implementation.cr` is observed and `open` or `merged` | — |
| `QA_CR_EXISTS` | `qa.cr` is observed and `open` or `merged` | — |
| `IMPLEMENTATION_REVIEW_THREADS_CLEAR` | `implementation.open_review_threads` is observed `0` | `IMPLEMENTATION_CR_EXISTS` |
| `IMPLEMENTATION_REVIEW_RECORDED` | `implementation.review_marker` is observed | `IMPLEMENTATION_CR_EXISTS` |
| `IMPLEMENTATION_REVIEW_CURRENT` | the record's `reviewed_sha` equals the implementation CR's `head_sha` | `IMPLEMENTATION_REVIEW_RECORDED` |
| `QA_CR_NOT_DRAFT` | the QA CR's `draft` is false | `QA_CR_EXISTS` |
| `FIDELITY_THREADS_CLEAR` | `qa.open_fidelity_threads` is observed `0` | `QA_CR_EXISTS` |
| `FIDELITY_AUDIT_RECORDED` | `qa.fidelity_marker` is observed | `QA_CR_EXISTS` |

Policy that lives here and not in `roz-state`:

- **a closed-unmerged CR counts as absent** — `roz-state` reports it as the
  closed CR it is; `…_CR_EXISTS` fails on it;
- **`reviewed_sha` is compared with `head_sha`** — `roz-state` reports
  both and compares nothing; a record whose `reviewed_sha` is `null` is
  not current;
- **the fidelity record carries no sha**, so its rule is existence only —
  the asymmetry is the prose's, kept as it is;
- **a thread count of `0` is "clear" only beside its record**: zero threads
  with no record fails `…_RECORDED` (#95, #140) — the count and the record
  are two rules;
- a merged CR whose head branch the forge deleted (#272) is an observed CR:
  the rule reads the CR, not the branch.

Not rules, on purpose: `fix_rounds` validation (config, not state — the
snapshot does not carry it), and clearing a stale lock (`NOT_LOCKED` says
the lock is there; whether it is stale, and clearing it, is the command's
or the human's call).

## The result

```json
{
  "schema": "roz-check/0.1",
  "operation": "integrate",
  "issue": 27,
  "verdict": "ineligible",
  "may_start": false,
  "rules": [
    {"code": "NOT_LOCKED", "status": "pass",
     "evidence": [{"path": "processing", "value": false}]},
    {"code": "QA_CR_EXISTS", "status": "pass",
     "evidence": [{"path": "qa.cr",
                   "fact": {"status": "observed", "source": "CR-FIND",
                            "value": {"number": 42, "state": "open", "draft": false,
                                      "base": "spec/27", "head_sha": "ef56"}}}]},
    {"code": "FIDELITY_THREADS_CLEAR", "status": "unknown", "requires": "QA_CR_EXISTS",
     "reason": "forge_query_failed",
     "evidence": [{"path": "qa.open_fidelity_threads",
                   "fact": {"status": "unknown", "value": null, "source": "THREADS-LIST",
                            "reason": "forge_query_failed"}}]},
    {"code": "FIDELITY_AUDIT_RECORDED", "status": "fail", "requires": "QA_CR_EXISTS",
     "evidence": [{"path": "qa.fidelity_marker",
                   "fact": {"status": "absent", "value": null,
                            "source": "CR-COMMENTS-LIST"}}]}
  ],
  "failed": ["FIDELITY_AUDIT_RECORDED"],
  "unknown": ["FIDELITY_THREADS_CLEAR"]
}
```

(Four of the thirteen rules shown.) **Evidence is the snapshot's own
fact**: an envelope is copied whole — `status`, `value`, `source`, and
`reason` when unknown — under its `path`; a plain value is `path` +
`value`; a rule that compares two facts lists both. A STOP message or a
later audit reads why a rule came out as it did; it never reconstructs it.
Callers read `verdict`, `may_start`, `failed` and `unknown` — codes, never
prose.

A check result is not a snapshot. `eligible`, `verdict`, `review_clean` and
the like are on the snapshot's deny-list (`references/roz-state.md` § Never
a fact) because they are decisions; this is where decisions live.

## Running it

```
bin/roz-check integrate <issue> --json                      # collects through roz-state
bin/roz-check integrate <issue> --json --state <file>       # checks a saved snapshot; asks nothing
```

| exit | stdout | meaning |
|---|---|---|
| 0 | the result | a verdict was computed — `ineligible` and `unknown` are answers, not errors |
| 2 | `roz-state`'s typed collection failure, passed through | the snapshot could not be collected; no verdict |
| 3 | nothing | `roz-state` returned something its contract rejects — a defect |
| 64 | nothing | usage |
| 65 | nothing | `--state` is unreadable, not a valid snapshot, or of another issue |

## What it never decides

Whether a red is a real bug or a harness issue; whether a contract is
right; whether a finding is justified; which patrol action follows a
failure; the wording of a STOP message. Those stay with the agent
(`references/roz-state.md` § What it answers). It runs nothing and it is no
transition engine: one operation, one list of rules.

## Shadow adoption

`commands/integrate.md` still enforces its own § 1; nothing trusts the
checker yet. `Run.shadow_check` (`evals/CONTRIBUTING.md` § 7) compares, on
an integrate replay case, the verdict on the state integrate **read** — the
case's seeded state — with whether the run took the lock (`status:
processing` added to the issue):

| verdict | expected | a mismatch when |
|---|---|---|
| `eligible` | the lock is taken | no lock |
| `ineligible` | no lock | the lock is taken |
| `unknown` | no lock | the lock is taken — counted, never ignored |

The STOP reason lives in prose and is not compared; the failed codes are
recorded in the detail. Each integrate case also declares the verdict and
failed codes its seed must give (`case.json`'s `check`), which the harness
verifies with no model call. The exit — coverage, zero unexplained
mismatches, N stable runs — is § 7's; N is set by the plan that makes the
checker authoritative, and that plan deletes § 1's restatement.
