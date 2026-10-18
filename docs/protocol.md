---
title: The Roz Gate wire protocol
---

# The Roz Gate wire protocol

**protocol v1** · reference client: the `roz-gate` Claude Code plugin, 2.0.0

Everything the loop needs lives **on the forge**: issue and change-request
(CR) comments, labels, branches. There is no side channel. This page is the
wire: what gets read and what gets written. Any agent or human that follows
it interoperates with the loop without installing anything; `roz-gate` is
the **reference client** of this page, not the protocol itself. The page
commits to what is read and written — never to how anyone thinks.

GitHub label names use the space form (`track: spec`); GitLab uses scoped
labels (`track::spec`, `status::blocked`) plus a **plain** `processing`, so
the lock can sit next to a phase label.

## 1. Labels — the state machine

| Label | Class | Meaning |
|---|---|---|
| *(no `track:` label)* | — | the **inbox**: a raw idea, pre-loop — intake only |
| `track: spec` | track | needs a debated spec; gated by `status: ready-for-spec` |
| `track: fast` | track | mechanical change; gated by `status: ready-for-dev` directly |
| `status: ready-for-spec` | **gate** | the human's order: refine the spec |
| `status: ready-for-dev` | **gate** | the human's order: build it |
| `status: in-spec-review` | transient | the spec CR awaits the human; question threads are live |
| `status: in-user-review` | transient | the work passed its verdict; the review conversation is open |
| `status: processing` | transient | the lock: a command is running — do not act |
| `status: blocked` | transient | an automated step stopped and needs the human — do not act |

**The one ownership rule.** Humans move **gate** labels — a gate label is an
authorization. Agents move **transient** labels — a transient label is a
status report. Neither ever moves the other's — with one exception, in the
human's favour: the human may clear `status: blocked` themselves (the resume
line below invites it). An agent that applies `status: ready-for-spec` or
`status: ready-for-dev` violates the protocol (the reference client refuses it
at the tool layer).

**Invariants.**

- In the loop, exactly one `track:` label; at most one `status:` label
  besides the `processing` lock — the lock is a mutex, not a phase, and
  coexists with the phase label it locks.
- A gate label on a track-less issue is the one legal transient of intake:
  the holder's confirmation, which the next pass finalizes into the
  confirmed track (`ready-for-spec` ⇒ `spec`, `ready-for-dev` ⇒ `fast`).
- `track: fast` never carries `status: ready-for-spec`.
- **No `status:` label means in flight or done** — the open CRs are the
  state. Which CRs exist, and on which branches, is the reference client's
  business, not the wire's.
- An issue may **return to the inbox**: strip its `track:` and `status:`
  labels and it is a raw idea again, its discussion intact.
- An agent that finds an illegal state **stops and reports — it never
  repairs labels.**

## 2. Comments — the marker grammar

- **Agent comments start with the bold bracket, `**[`**, or with `✅ [` for a
  resolution note. Human input is free-form and never starts with either.
  The text inside the bracket is a role or a name — the five seat names the
  reference client uses are examples, not requirements.
  - `**[intake]**` — the one-time intake question batch
  - `**[intake] · summary**` — an intake summary
  - `**[<role>] · Q<k> · <label>**` — an open-question thread on the spec CR
  - `**[<command>] · blocked**` — a stopped step (below)
- **The `summary` request.** A comment by the gate holder whose first or last
  non-empty line is exactly `summary` (case-insensitive; emphasis and
  backticks stripped). Corrections and the request may share one comment.
  From anyone else it is discussion.
- **Question batches are asked once**; answers are free-form replies
  (`1a 2b` shorthand welcome), from anyone, on any device. Unanswered
  questions resolve to their recommendation and are listed as assumptions.
- **Answers on a spec CR are read from three channels**: the inline review
  thread, the review summary body, and a top-level CR comment — the one a
  phone offers. A thread the human opened is an amendment request.
- **The STOP comment.** When an automated step stops, the issue carries
  `status: blocked` alone and one comment whose title is
  `**[<command>] · blocked**`; its last line before the folded evidence is
  the resume line — **To resume:** clear `status: blocked`, apply
  `status: <phase>` — and that line names where the answer goes. When the
  step stopped from in flight there is no phase to restore: the line then
  says that clearing `status: blocked` is the whole move. Nothing else about
  the stop is wire.

## 3. The gate holder

The issue's **assignee**; unassigned → the **author, if human**. A bot
identity **never** holds a gate, and a bot-created issue **carries a human
assignee at birth**. Everything before the gate label is input; **the label
is the decision**. The body invariant holds however many agents take part:
*every word that reaches a gated issue body was either said by the gate
holder or seen by them.*

## 4. Identity and capability containment

With more than one agent in a thread, **author structure is the identity
mechanism** — text markers are presentation, not authority.

- An agent acts under its **own** forge identity: a GitHub App
  (`<slug>[bot]`) or a GitLab project access token bot
  (`project_<id>_bot_<hash>`) — or, as the reference client does by
  default, under its **operator's** session, in which case that one human
  owns every word posted under their name and the `**[` prefix is what
  tells agent output from theirs. Never another agent's session, and never a
  shared one: with more than one agent in a thread, each acts under its own
  bot identity. GitLab bot usernames are opaque; name the tokens
  meaningfully and keep the mapping in the client's configuration.
- When comparing GitHub logins, strip the `app/` prefix and the `[bot]`
  suffix — one App surfaces as `app/<slug>`, `<slug>` and `<slug>[bot]`
  depending on the API path.
- A gate label applied by a **bot identity is not an authorization**,
  whichever client applied it. The forge records who applied each label; a
  client that audits those events (the reference client's patrol does)
  reports such a label as a violation and acts on nothing until a human
  moves it.
- **Containment is the token's scope.** The forge has no per-label
  permissions, so the only forge-side control is what each agent's token can
  do: an intake-only agent with issue write access alone physically cannot
  push or merge. Give each agent its role's scopes and nothing more.
- **Conformance is per client.** The reference client enforces this page on
  itself at the tool layer. For any other client, review its code and
  contain its token — the page cannot enforce itself.

## 5. Many participants, one driver

Foreign agents are safe **as participants** today: commenting, answering a
batch, reviewing a CR, opening a thread, writing a `**[`-prefixed input —
every rule above holds for them. The **driver** — the seat that moves
transient labels, posts batches and summaries, finalizes issue bodies, opens
and merges work into CRs — is **exactly one per repository**: the
`processing` lock has no owner and no expiry, batches are asked once, and the
scheduler acts on one issue per pass. A second driver is protocol v2
material. The driver's own durable records — review and audit stamps,
contract-deviation sections, test-port lines, reserved words in spec
documents — are reference-client internals: it writes them and it reads
them, so they are outside v1 and may change without notice.

An agent joining the loop MUST:

1. Read state **only** from labels and comments — no side channels.
2. Prefix every comment it authors with `**[<its-role-or-name>]`.
3. Never apply, remove or repair a **gate** label; never merge a CR.
4. Act under its own bot identity or under its one accountable operator's
   session — never another agent's — and give every issue it creates a
   human assignee.
5. Honor `status: processing` and `status: blocked` — never act on a locked
   or stopped issue.
6. Stop and report anything illegal or unexpected — never improvise.

Humans need none of this — see [participating.md](participating.md): answer,
`summary`, label, review.

## 6. Versioning

This page carries its own stamp, **protocol v1**, decoupled from the
reference client's version. Within v1, changes are **additive only**: a label
or marker never changes meaning, and nothing listed here is removed. A
change that breaks either is protocol v2.
