---
description: Host one turn of the stage-(7) review conversation — answer the user's CR comments from the artifacts, dispatch a seat when judgment is needed, and act only on what they confirm
argument-hint: "[issue-number]"
---

Host **one turn** of the user's review at stage (7) (see
`${CLAUDE_PLUGIN_ROOT}/references/workflow.md` → (7) Review). The user is
reading the CR and talking; you answer, and you act only on what they
confirm. Follow these steps; do nothing beyond them.

## 0. Load config & forge adapter

Read the `### Roz Gate config` block in the project's CLAUDE.md (`forge`,
`default_branch`, `test`, `acceptance_test`, `env_sync`, `specs_dir`,
`acceptance_dir`), then
`${CLAUDE_PLUGIN_ROOT}/references/forge-<forge>.md` for the concrete CLI behind
every CAPITALIZED-OP. Missing config → stop; tell the user to run
`/roz-gate:init`. **Personas**: the seat dispatches below resolve through the
`### Roz Gate personas` block — dispatch the mapped subagent, attaching the
seat's R&R row from `${CLAUDE_PLUGIN_ROOT}/references/workflow.md` as its
contract. Block missing → plugin defaults.

## 1. Find the conversation (read-only)
- Issue `<n>` from `$ARGUMENTS`, or every issue labelled
  `status: in-user-review`. Skip any carrying `status: processing` (another
  command holds it).
- The CR is `spec/<n>` for `track: spec`, `fast/<n>` for `track: fast` (CR-FIND).
  Missing or closed while the label persists → report it and act on nothing.
- **Read all three channels** — THREADS-LIST (inline threads), REVIEWS-LIST
  (review summary bodies), CR-COMMENTS-LIST (top-level comments). An item is
  **unheard** when its latest entry does **not** start with `**[` or `✅ [`.
  Nothing unheard → report "nothing new" and stop; no lock was taken.

## 2. Lock
LABEL-ADD `status: processing`. It coexists with `in-user-review` — a mutex,
not a phase. Every exit removes it.

## 3. Answer — one item at a time, oldest first

**You are the bridge, not a seat.** Every sentence you write is one of:
- a **verbatim quote** from a named artifact with a permalink **at a SHA**
  (spec line, decision-ledger entry, prior ruling, code) — a branch link
  rots when the line moves;
- the **verbatim return of a dispatched seat**;
- a **fact about repo or forge state** ("merged at `abc1234`", "the suite is
  green").

Anything you add beyond those is marked `interpretation:` — marking makes it
visible, it does not license it. A sentence that claims something about the
product, the design, or correctness and is none of the three above is **new
judgment: dispatch the seat that owns it** (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`
R&R). A behavioural claim cites a spec rule or a test, never a code line alone.

**Every write obeys three rules** — they are one mechanism with the detection
predicate in step 1, and breaking any of them makes the conversation answer
itself on the next patrol pass:
1. It starts literally with `**[review] · answer**`, `· question`, or
   `· addressed`. **Never open with a quote block** (guard-gate denies a
   quote-opening, marker-carrying comment mechanically).
2. **Only you post to the CR.** A dispatched seat returns text; you post it,
   prefixed. (The intake relay rule, unchanged.)
3. It cites the URL of the comment it answers, and it never resolves the
   thread — at (7) the user asked, so the user's satisfaction closes it.

Many items end here: a question answered from the ledger costs no dispatch and
changes nothing. That is the common case, not a shortcut.

## 4. Before proposing any change — one seat opinion
**Any resolution that would edit a file gets one seat opinion first**, before
you read anything back. The trigger is the act you are about to take, not your
reading of what the user meant:

| About to edit | Seat |
|---|---|
| `<specs_dir>/<n>/spec.md`, or any user-visible behaviour | `product` |
| `technical-spec.md` or implementation code | `implementer` |
| nothing — pure explanation | **none** |

The seat's (7) deliverable is narrow: enumerate happy/edge/failure for the
proposed change, and **name which existing rules or scenarios it invalidates**.
Its answer goes into the readback — it is the only thing at (7) that puts a
failure branch in front of the user.

`track: fast` is the exception, as it is at (3'): no seat dispatch, no readback
ceremony — you wrote the code, so you and the user talk plainly. Everything
else in this command still applies.

## 5. Read it back, then wait
State the change in one line, in the user's terms, naming the files it will
touch and what the seat said it invalidates. If it changes a rule, **the
readback contains the new rule text** — that text is what the user approves and
what goes into `spec.md` verbatim in step 6.

- The user's word authorizes. **Silence is never consent**; neither is your own
  summary. A 👍 is consent to a readback proposing **one** change — never to a
  readback proposing several (a reaction cannot select which).
- A reply that adds anything the readback did not contain (*"sure, but watch
  out for X"*) is **not** a plain yes: read back the amended change, once more.
- Anything you cannot read as a clear yes → ask, in the thread, in their
  language. **Ambiguity resolves to asking, never to acting.** At (7) an
  ambiguous reply is usually information: the readback was wrong, or the change
  is bigger than you framed it.
- If the change would touch the issue's **acceptance criteria**, the readback
  offers the other door beside it, in neutral words and with its cost — see
  step 7. Not an alarm, not a STOP: a second shape of the same answer.

No confirmation this turn → post the readback, unlock, and report. The user
answers when they answer.

## 6. Act — only on what they confirmed
CR-VIEW first: not open → discard, write nothing, report what never landed (the
user merged mid-turn; surviving items are a follow-up issue's business). Then,
by change class:

- **Doc or comment only** → commit and say so.
- **Code** → commit, then the **hand-back rule**
  (`${CLAUDE_PLUGIN_ROOT}/references/workflow.md`): re-run config
  `acceptance_test` for the feature **and** config `test`, capture the output,
  and only then push. Red → the stage-(6) taxonomy (`commands/integrate.md`
  step 5): real bug → fix; harness issue → `qa`, **on `qa/<n>`, merged back**
  (a hook blocks acceptance-file edits on `spec/<n>` — that is the road, not an
  obstacle); a failing assertion that faithfully states the contract is the
  **contract-defect** class and it is **never yours to classify as
  "they authorized it"** — that reading would launder any red at the last gate.
  Stop and let the user rule. Cap: 3 attempts, then stop and report.
  On `track: fast`, a code change re-dispatches `reviewer` on the new commits —
  it is the whole guard that track has.
- **Spec semantics** — the change alters what a rule or scenario means → do
  **not** fold it here. LABEL-REMOVE `status: in-user-review`, LABEL-ADD
  `status: in-spec-review`, post the question as a spec-CR thread, and let
  (2a)'s machinery handle it; `/roz-gate:spec-answers` returns the issue here
  when it is answered.
- **A rule changed** → its approved text lands in `<specs_dir>/<n>/spec.md` in
  the **same commit**, provenance `(from review)`. A rule living in code while
  `spec.md` states the old one poisons every later kit, every fidelity review
  and the next feature's spec round — and no redo of this issue reaches it.

One commit per turn, its message citing the comment(s) it answers. Then
COMMENT-EDIT the gate-kit comment
(`${CLAUDE_PLUGIN_ROOT}/references/gate-kit.md`): append the exchange to the
decision ledger (§3's shape, unmodified), and if the suite re-ran, regenerate
the evidence cards wholesale from the new output and re-stamp `cards-sha`.
Finally THREAD-REPLY `**[review] · addressed**` with the diff link and the
changed lines quoted.

## 7. The other door — back to intake
When the user judges the issue itself was wrong, starting over is the cheap,
correct remedy, not a failure — say it that way. On their word (they apply it,
you never do): close the CRs, LABEL-REMOVE the `track:` label and every
`status:` label. The issue is the inbox again ((1b)) and the next patrol pass
picks it up.

State the cost once, factually: the merged work is on `spec/<n>` and
re-derivable — that part is cheap — but their **decision ledger** is their own
rulings, and a fresh intake would re-ask them. Offer to carry it into the new
intake as **prior answers to confirm, not re-answer**; the ledger is already
one comment, already verbatim.

## 8. Unlock and report
LABEL-REMOVE `status: processing`. `status: in-user-review` stays — the issue is
at the user's gate either way, so **(7) has no `blocked` exit**: anything you
could not do is a `**[review] · question**` saying so, and the prefix itself
makes it non-actionable until they reply.

Report per issue: what you answered from artifacts, what you dispatched, what
you read back and is now waiting on them, what you committed and whether the
suite re-ran, and anything that arrived mid-turn (it is next turn's work).
