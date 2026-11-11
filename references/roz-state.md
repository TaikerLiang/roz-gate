# roz-state — the observation contract

The contract for the workflow fact layer (#239). `bin/roz-state` (#133)
implements it; `roz-check` (#134) consumes it; no command reads this page
yet. `hooks/state_contract.py` is the same contract as code — a shared
contract and validation module, kept in `hooks/` for layout convenience,
not a hook rule and not owned by the hook layer. Lint L15 holds the two
equal.

## What it answers

`roz-state` answers one question: **what is observably true right now?**
It never answers "what should Roz Gate do next?".

```text
forge / git / config
        ↓
roz-state     observable facts + provenance
        ↓
roz-check     mature mechanical policy          (#134)
        ↓
command / LLM semantic interpretation
        ↓
human         authority / intent
```

| question | owner |
|---|---|
| Does branch X exist? Which branch is the current attempt? | `roz-state`, through `roz-branch` |
| Is the CR open, merged, draft? What is its base? | `roz-state` |
| How many unresolved threads? Is an audit marker there, and for which sha? | `roz-state` |
| Is a forge-native blocker open? | `roz-state` |
| Is the marker's sha the CR's head? Is the review clean? | `roz-check` |
| Is a red a harness issue or a contract mismatch? Is a clause contradictory? | the agent |
| Should the work be authorized or accepted? | the human |

Things that can be observed mechanically become code. Things that need
interpretation stay with the agent. Things that need authority stay with
the human.

## Facts, not decisions

A fact is raw evidence. A marker is its `reviewed_sha` and `comment_id`;
whether that sha is the CR's head is a comparison, and comparisons are
`roz-check`'s. A thread count is a number; whether the review is clean is
policy. `roz-state` is read-only: it writes no label, comment, branch or
CR.

### Never a fact

These keys are rejected at every depth, in every schema version. A
decision or a derived verdict is never an "additive field".

| key | why |
|---|---|
| `action` | a decision |
| `next_action` | a decision |
| `next_stage` | a decision |
| `transition` | a decision |
| `ready_for_integration` | a verdict over several facts |
| `review_clean` | a verdict — it encodes what "clean" means |
| `fidelity_current` | a verdict — `reviewed_sha` compared with the head |
| `eligible` | a verdict |

## A snapshot, or a typed failure

A collector emits exactly one of two things.

**A snapshot** — when the issue's identity, its base state and the
resolved config were established.

**A collection failure** — when any of them was not. No snapshot is
emitted, no plain field is fabricated, and the tool exits non-zero with:

```json
{"schema": "roz-state/0.1",
 "collection_failure": {"reason": "forge_query_failed", "source": "ISSUE-VIEW",
                        "detail": "gh: HTTP 502"}}
```

`reason` and `source` are required; `detail` is optional free text. A
failure carries no snapshot field, and a snapshot carries no
`collection_failure`.

## The three statuses

Inside a snapshot, identity is plain: `unknown` is not a meaningful state
for it, because without it there is no snapshot. Every other fact is an
envelope:

```json
{"status": "observed", "value": 0, "source": "THREADS-LIST"}
{"status": "absent",   "value": null, "source": "CR-FIND"}
{"status": "unknown",  "value": null, "source": "THREADS-LIST", "reason": "forge_query_failed"}
```

| status | meaning |
|---|---|
| `observed` | the collector asked and got a value — `0` and `[]` are values |
| `absent` | the entity or fact itself does not exist |
| `unknown` | the collector could not establish the fact; `reason` is required |

`source` is required on every envelope: the forge op or tool that was
asked. `value` is `null` unless the status is `observed`. One timestamp,
the snapshot's `observed_at`; none per fact.

**absent ≠ unknown.** Absent is "asked, and it is not there". Unknown is
"could not ask, or got no answer".

**absent ≠ observed-empty.** Absent is about the entity; `0` and `[]` are
about a count or collection that was established and found nothing. This
is #95's lesson — zero findings is not proof that anyone looked — frozen
into the shape:

| situation | fact |
|---|---|
| the QA CR does not exist | `qa.cr` = absent |
| the QA CR exists, no fidelity marker | `qa.fidelity_marker` = absent |
| the dependency query succeeds, no blockers | `dependencies.blocked_by` = observed `[]` |
| the thread query succeeds, zero unresolved | `open_review_threads` = observed `0` |
| the CR is absent | its thread count and marker = absent (nothing to count) |
| the CR is unknown | its thread count and marker = unknown, `depends_on_unknown` |

A thread count is never absent under an observed CR, and
`dependencies.blocked_by` is never absent at all: the issue always exists.

### Reasons

| reason | when |
|---|---|
| `forge_query_failed` | the forge CLI exited non-zero or returned nothing parseable |
| `remote_unreachable` | `git ls-remote` failed (`roz-branch` outcome `UNKNOWN`) |
| `ambiguous` | more than one candidate and no rule picks one (`MULTIPLE_SAME_SEQ`) |
| `depends_on_unknown` | the fact hangs off a CR that is itself unknown |
| `unsupported` | this forge or this version cannot answer |

## The unknown invariant

> An unknown fact neither satisfies nor refutes a precondition. A consumer
> never reads it as `0`, `false` or empty.

What a precondition does when a fact is unknown — stop, wait, report — is
`roz-check`'s policy (#134), decided per precondition. Two behaviours are
already defined and are instances of the invariant: a failed blocker read
is `waiting on: blockers unknown`, never "no blockers" (F15, #205); an
unreadable remote is `UNKNOWN` → STOP, never "no branch" (#135).

## v0.1 fields

`track: spec` only, and only facts production behaviour already consumes.
Strict within the version: a key `roz-state/0.1` does not declare is an
error in a `0.1` snapshot. **Adding an observational field is an additive
revision** — the tables below, the module, its tests and the `schema`
string move in one PR (`roz-state/0.2`); it is never evidence that a
snapshot became semantically invalid. Removing or re-typing a field is a
breaking revision.

### Plain values

| path | type | from |
|---|---|---|
| `schema` | `roz-state/0.1` | — |
| `observed_at` | ISO-8601 UTC | the collector's clock |
| `issue` | integer | the argument |
| `track` | string, or `null` when no `track:` label is worn | ISSUE-VIEW |
| `status` | string, or `null` when no `status:` label is worn | ISSUE-VIEW |
| `processing` | boolean — the label is worn | ISSUE-VIEW |
| `blocked` | boolean — the label is worn; it means "waiting on the human", not a lock | ISSUE-VIEW |
| `config.branch_template` | string | `bin/roz-config` |
| `config.default_branch` | string | `bin/roz-config` |
| `config.acceptance_dir` | string | `bin/roz-config` |

`config` carries only the resolved values that shaped the observation —
for reproducing it and for autopsying a shadow mismatch — never the whole
block.

### Facts

| path | value when observed | source | inventory row |
|---|---|---|---|
| `branches.spec` | `{name, sha}` | `roz-branch match` | L4, C31 |
| `branches.implementation` | `{name, sha}` | `roz-branch match` | L4, C31 |
| `branches.qa` | `{name, sha}` | `roz-branch match` | L4, C31 |
| `spec.cr` | `{number, state, draft, base, head_sha}` | CR-FIND, all states | C6, C13 |
| `implementation.cr` | `{number, state, draft, base, head_sha}` | CR-FIND, all states | C6, C13, A7 |
| `implementation.open_review_threads` | integer ≥ 0 | THREADS-LIST | C22 (obs) |
| `implementation.review_marker` | `{reviewed_sha, comment_id}` | CR-COMMENTS-LIST | C22 (obs) |
| `qa.cr` | `{number, state, draft, base, head_sha}` | CR-FIND, all states | C6, C13 |
| `qa.open_fidelity_threads` | integer ≥ 0 | THREADS-LIST | C16 (obs) |
| `qa.fidelity_marker` | `{reviewed_sha, comment_id}` | CR-COMMENTS-LIST | C16 (obs) |
| `dependencies.blocked_by` | list of `{issue, state, url}` | ISSUE-BLOCKERS | F15 |

A CR's `state` is `open`, `merged` or `closed`; a blocker's is `open` or
`closed`. `base` is the CR's target branch: a CR's state means something
only together with it (#209). `roz-branch` outcomes map as `NO_MATCH` →
absent, `UNKNOWN` → unknown (`remote_unreachable`), `MULTIPLE_SAME_SEQ` →
unknown (`ambiguous`).

## Example

An issue in development: the spec CR merged, the implementation CR open,
no QA yet, and one read that failed.

```json
{
  "schema": "roz-state/0.1",
  "observed_at": "2026-11-11T01:00:00Z",
  "issue": 27,
  "track": "spec",
  "status": "in-dev",
  "processing": false,
  "blocked": false,
  "config": {
    "branch_template": "{kind}/{n}/{seq}",
    "default_branch": "main",
    "acceptance_dir": "tests/acceptance"
  },
  "branches": {
    "spec": {"status": "observed", "value": {"name": "spec/27/2", "sha": "ab12"},
             "source": "roz-branch match"},
    "implementation": {"status": "observed", "value": {"name": "feat/27/2", "sha": "cd34"},
                       "source": "roz-branch match"},
    "qa": {"status": "absent", "value": null, "source": "roz-branch match"}
  },
  "spec": {
    "cr": {"status": "observed",
           "value": {"number": 40, "state": "merged", "draft": false,
                     "base": "main", "head_sha": "ab12"},
           "source": "CR-FIND"}
  },
  "implementation": {
    "cr": {"status": "observed",
           "value": {"number": 41, "state": "open", "draft": false,
                     "base": "spec/27/2", "head_sha": "cd34"},
           "source": "CR-FIND"},
    "open_review_threads": {"status": "unknown", "value": null, "source": "THREADS-LIST",
                            "reason": "forge_query_failed"},
    "review_marker": {"status": "observed",
                      "value": {"reviewed_sha": "cd34", "comment_id": 9001},
                      "source": "CR-COMMENTS-LIST"}
  },
  "qa": {
    "cr": {"status": "absent", "value": null, "source": "CR-FIND"},
    "open_fidelity_threads": {"status": "absent", "value": null, "source": "THREADS-LIST"},
    "fidelity_marker": {"status": "absent", "value": null, "source": "CR-COMMENTS-LIST"}
  },
  "dependencies": {
    "blocked_by": {"status": "observed", "value": [], "source": "ISSUE-BLOCKERS"}
  }
}
```

Nothing here says whether the review is clean: the marker's sha equals the
head, and the thread count is unknown — what follows from that is
`roz-check`'s.

## Forge neutrality and transport

GitHub and GitLab differences stay below the snapshot: the same fact has
the same path and shape on both. The collector asks through `gh` / `glab`
— the forge ops the prose already names, which the replay forge stub
intercepts — behind adapters that map each CLI's output to the envelope.
Branch identity comes only from `roz-branch` (`references/branch-names.md`,
#135); `roz-state` never expands a template or matches a head itself.
Dependencies are observations: no ordering, no graph, no scheduling.

## After v0.1

| candidate | why not yet |
|---|---|
| unheard human comments (inventory A1–A3) | reads comment content and authorship, not a count; its shape has not survived shadow use |
| who applied a gate label (C24) | an event stream, not a state |
| `track: fast` | after the spec-track shape is stable |

## Shadow adoption

`roz-state` runs beside the workflow before anything trusts it. The
comparison unit (one replay run: the scanner's report against a snapshot
of the same final forge-stub state) and the three-part exit — coverage,
zero unexplained mismatches, N stable runs — are
`evals/CONTRIBUTING.md` § 7's; N is set in #133's plan. The scenario
matrix every cell of which must be observed first:

| scenario |
|---|
| a missing CR |
| an open CR, a draft CR, a merged CR |
| a re-spec (`{seq}` > 1) |
| an implementation CR targeting the current spec branch vs an old one |
| zero review threads |
| no audit marker vs a completed clean audit |
| one open dependency |
| several dependencies |
| an unavailable forge observation |

A mismatch is classified — collector defect, branch-resolution defect,
prose-interpretation defect, missing field, or a genuinely ambiguous rule
— and fixed or filed. After parity the collector is the source of truth
and the duplicate prose observation is deleted: its row in
`docs/prose-inventory.md` moves to `authoritative`, then `migrated`.
