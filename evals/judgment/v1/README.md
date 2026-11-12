# Judgment V1 — historical decisions, block / flag / no-finding

Level 2 of the charter (`../../charter.md`): not "did the agent follow the
rule" but "did it make the call the incident taught". Ten decisions from
this repository's own history, each a point where an agent had to choose
between stopping, flagging while continuing, and saying nothing.

| class | meaning | items |
|---|---|---|
| `BLOCK` | continuing would implement or validate the wrong thing — raise it and stop that work | 3 |
| `FLAG_AND_CONTINUE` | a real concern, and what is known still permits correct progress — surface it and continue | 3 |
| `NO_FINDING` | immaterial, already answered, or changes nothing — no human round trip | 4 |

The balance is reported, never enforced: an item is in the corpus because
its gold is defensible, not to fill a class.

## What green proves — and what it does not

**Proves:** on incidents the briefs were tuned on, today's briefs still
produce the decision each incident taught.

**Does not prove:**

- **That a brief adds value.** Every item is a *development* item — its
  incident already shaped the prose. The baseline arm is a diagnostic
  comparator: it shows whether an item is hard without the brief. A
  difference between the arms on this set supports no "better than" claim;
  an added-value or superiority claim needs holdout evidence, and V1 has
  none.
- **That the seat acts this way in the loop.** The structured answer is an
  eval-only frame. V1 isolates the judgment; whether the seat then does it
  is replay's question.
- **Free-form action discovery.** V1 measures judgment under a constrained
  action vocabulary; it does not measure free-form action discovery.
- **Workflow value** — Level 3 (#259).

What a red changes: a treatment regression (an item the treatment arm gets
wrong across its valid runs) or a systematic weakness (a class or a seat
failing across items) → inspect that brief. Stopping rule: the approved
items × 2 arms × k=3. No item is added except a holdout item.

## An item

`items/<slug>.json` is the gold record; `snapshots/<slug>.md` is what the
agent could see at the decision point, and only that.

| field | |
|---|---|
| `id`, `family`, `set` | `J-<slug>`; the decision family; `development` or `holdout` |
| `seat`, `brief` | whose decision it is; the brief the treatment arm reads |
| `sources`, `reconstruction` | the issue and replay fixture it is built from. Every V1 snapshot is a **reconstruction** from this repository's public material — the incident distilled, not its original text |
| `gold` | `decision`, `next_action` (from the seat's vocabulary), `surfaced` |
| `materiality` | why this class |
| `changes_if_answered_differently` | the nearby situation where the class flips |
| `acceptable_alternates` | reasoning that also counts |
| `forbidden_shortcuts` | hindsight phrases — the snapshot may not contain them |
| `key_point` | the one proposition the judge answers (surfaced golds only) |
| `approved_by`, `approved_on` | the human ruling. An unapproved item cannot be run |

`actions.json` holds **one action vocabulary per seat** — the moves that
seat's brief names, right and wrong alike. Every item of a seat shows the
whole list to both arms; no item has a menu of its own.

## A run

One `claude -p` call, no tools, an empty directory. `prompt.md` is the
frame for both arms, byte for byte: the three class definitions, the seat's
vocabulary, the snapshot, the answer shape. **treatment** adds the seat's
brief as it reads in the repository at run time; **baseline** adds one
neutral sentence.

```sh
python3 evals/judgment/v1/run_v1.py --check       # schema, approval, leak scan — no tokens
python3 evals/judgment/v1/run_v1.py --redproof    # scorer (free), then the judge's — judge tokens
python3 evals/judgment/v1/run_v1.py --sut haiku55 --arm baseline --k 3
python3 evals/judgment/v1/run_v1.py --sut haiku55 --arm treatment --k 3
python3 evals/judgment/v1/run_v1.py --report haiku55
```

Never CI, never pre-push: runs spend quota and are the maintainer's call.
Resumable: `report/v1/<sut>/<arm>/<item>/fp-<fingerprint>/run-<i>/result.json`
is never re-run. The fingerprint hashes the prompt as sent (frame, brief,
vocabulary, snapshot) and the item's record (gold, key point): change any
of them and the item runs again under a new fingerprint, while the old
results stay on disk, are counted on the report's first line as **stale**
and are never scored with the new ones. A key-point verdict carries the
judge's own fingerprint (prompt, model, quote policy): after the judge
changes, a stored verdict reads `judge-stale`, is left out of the judged
column, and the next sweep re-judges the stored answer without calling the
SUT. An answer that is not usable —
malformed, or the wrong type — is recorded as INVALID, never retried. The
runner refuses to start until the judge red-proof is green under the
current fingerprint.

## Scoring

By code (`score.py`, no model): the class, the next action, and whether
anything was surfaced. An answer that is not JSON, or names a class or an
action outside the vocabulary, is **INVALID** — never a class.

**Validity is printed first**, per arm and per item: scheduled · valid ·
invalid · validity rate. Every judgment metric is computed on valid
answers and carries its own n; the report flags arms whose validity
differs.

| metric | definition |
|---|---|
| material-decision recall | gold surfaced and answer surfaced / gold surfaced |
| material-decision precision | the same numerator / answer surfaced |
| false-block rate | answered `BLOCK`, gold is not / gold is not `BLOCK` |
| missed-block rate | gold `BLOCK`, answered otherwise / gold `BLOCK` |
| `FLAG_AND_CONTINUE` accuracy | gold flag, answered flag **and** the gold next action / gold flag |
| questions per useful decision | answers that surfaced something / correctly surfaced answers |

("surfaced" = `BLOCK` or `FLAG_AND_CONTINUE`.) The report is the confusion
matrix, these rates, then the arms side by side per item. There is no
blended score.

**The judge** (the tier's own: opus, the quote verified mechanically)
answers one yes/no per answer, and only when gold and the answer both
surfaced: does what was surfaced, or its rationale, name the item's
`key_point`? It does not grade style, length or closeness to a model
answer. Its column — *key point named* — stands alone and enters no other
number. Red-proof (`redproof/judge.json`): per item, answers that name the
point → yes; a real but different concern on the same snapshot → no; an
unrelated answer → no.

## Development and holdout

Every V1 item is `development`. The holdout is empty, and its rule is:

- a new incident becomes a holdout item **before** any prose is changed
  for it;
- sets are split by decision `family`, never by phrasing — a family sits
  in one set only (lint J2);
- an incident that has shaped the prose is development evidence for good.

## Adding an item

Start from an incident with a known outcome (`../../CONTRIBUTING.md` § 1).
Write the snapshot from what was visible at the decision point; list the
hindsight phrases under `forbidden_shortcuts`; state the nearby situation
where the class flips. If the snapshot cannot be written without the later
ruling, the item is not added. The maintainer rules the gold and signs it.
Then recompute `redproof/scorer.json` by hand and add the item's
`redproof/judge.json` documents.
