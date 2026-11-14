# next-stage — Path A

Routed here by `commands/next-stage.md` §4: `track: spec` + `status: ready-for-spec`.
You have read that file's §0–4 (config, forge adapter, branch names,
workspace, invariants, the map); they hold here. The STOP exit and the
one-issue rule are at the end of `commands/next-stage.md`.

## Path A — spec refinement (2)

### A1. Lock
LABEL-ADD `status: processing`.

### A2. Branch
**The branch may already exist** — a previous attempt at this stage. Before
the cut, **Lookup** the spec kind of #<n> (`git ls-remote --heads origin`
matched against the template — `references/branch-names.md`). A match →
CR-FIND (all-states form) its CR: **open** → illegal state, **STOP** (someone
is still reviewing it; the gate label is wrong, not the branch); **closed
unmerged, or no CR** → this is a **re-spec**, and the route is the
template's. It carries **`{seq}`** → `<spec-branch>` is **1 + max(`{seq}`)**
over Lookup's matches (Expand — never 1 + the count: a gap in the sequences
makes the count an existing ref, #135); **check the expanded name against
the same `ls-remote` output before the cut** — already present → a
collision, **STOP** naming it, never a silent bump. The previous attempts
stay on the remote, readable in their closed CRs — cite them in the report —
and the cut below proceeds. It carries **no
`{seq}`** → the stale branch is the
human's to remove: **STOP**, and the `blocked` comment and the report carry
the remedy verbatim — `git push origin --delete <spec-branch>` (and `<feat-branch>` / `<qa-branch>` if present) — *the human
runs this; the agent never does*: an agent never deletes or force-pushes a
remote branch, and the previous attempt stays readable in its closed CR
(cite it). The resume line reads: run the delete, then re-apply the gate label; the next pass cuts fresh (the cut
uses `-B`, so the previous attempt's local ref cannot block it).

Create `<spec-branch>` from `<default_branch>` **in a worktree** —
`git worktree add $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch> -B <spec-branch> origin/<default_branch>` (`-B`, not `-b`: after a re-spec the previous attempt's **local** `<spec-branch>` ref may survive its removed worktree, and `-B` resets it onto the base; a local ref is not a remote branch — the invariant is untouched; a `-B` refused because the branch is checked out elsewhere is the mutex, a STOP)
— and work there from here on (`git fetch --prune` first — a stale tracking ref would pass the check for a base the forge deleted; then verify `origin/<default_branch>` exists — `git rev-parse --verify -q origin/<default_branch>` — and if it does not, **STOP**: the base the config names is not on the remote; never cut from anything else).

### A3. Spec refinement (NO implementation code)
Base everything strictly on the issue body. Per the workflow's stage (2):
- Dispatch `em` and `product` → write `<specs_dir>/<n>/spec.md`.
- Dispatch `implementer` → write `<specs_dir>/<n>/technical-spec.md` (the
  contract: command/API spec, schema, behavioral guarantees; a documented test
  **port** for non-API features). A seat — `product`, `em`, `implementer`, at
  any dispatch of this command — that finds the base lacks code the issue
  needs **reports it** (what, and which branch holds it) and stops; this
  command then takes the STOP exit below with the shape *the base lacks a
  dependency*. It never proposes a merge, a rebase or a cherry-pick from
  another branch as a question option (#213, `references/workflow.md`). **The test-port line** (#125):
  `technical-spec.md` carries exactly one line `**Test port** — <path>[,
  <path>…]` — the repo-relative files or directories the port lives in;
  the acceptance suite drives it, and it is the one thing under `src/`
  the blind reviewer may read — or `**Test port** — none` when the contract
  is an API doc. Path B refuses to start without the line, and B5b
  copies its paths into the dispatch marker; a port that lives in an
  existing unit-test file is declared there all the same (ADMC #11).
- **Rules enumeration requirement:** `spec.md` MUST enumerate its
  story-level rules exhaustively and number them — `R<k> · <2–4-word
  title>`, one entry per behavioural rule or guarantee; scenarios cite the
  rules they exercise. Each rule carries a **provenance annotation**:
  `(from Q<j>)` — ruled by the gate holder's answer to that question;
  `(from AC-<j>)` — carried from the issue's acceptance criteria;
  `(assumed)` — resolved to a recommendation nobody confirmed. The
  enumeration is the spec's own content in numbered form — never a second
  prose copy that can drift from it. `technical-spec.md` numbers its
  clauses the same way — `G<k>` for guarantees (citing parent rules:
  `G6 (R6, S6)`), `C<k>` for every other normative clause — so that
  tags, findings, and the §5 walk below have stable anchors to attach to;
  anchor-free contract prose cannot be cited, audited, or kept current.
- **Evidence annotations — rulings are not claims.** Two kinds of
  sentence share the spec's typography and must not share its authority.
  The test is **jurisdiction**: *can the implementer be ordered to make
  this sentence true?* Yes → it is a requirement — a ruling or a
  guarantee about the system being built, enforced by (4) and (6) like
  any other. No → it describes **pre-existing reality** (current DB
  behaviour, lock contention, a third-party library, how today's code
  behaves), and writing it down does not make it true. Every such
  empirical claim carries an evidence tag:
  - `(measured, <date>, <scope one-liner>)` — measured by the
    `implementer` (the only spec-stage seat allowed in the codebase),
    with the scope that bounds the claim (`measured 2026-08-20, 15 runs,
    dev db n≈10k`) and a link to what was run wherever one exists. The
    date says when; the scope is the falsifier.
  - `(unverified)` — asserted, load-bearing, and nobody has checked. The
    honest state of a draft; **illegal to sign** (Path B refuses to
    start while one exists). **`unverified` is a reserved word** in every
    spec document: it appears only as this tag. Prose says *not yet
    measured* or *asserted* — the checks match the whole word anywhere,
    so the word loose in a sentence stops the gate exactly as the tag
    does, and the remedy is to reword it, never to wave it through as a
    false positive (#123). The registry of reserved words is
    `${CLAUDE_PLUGIN_ROOT}/references/reserved-words.json`; its rule is
    `reserved-words.md` beside it.
  - `(assumed-empirical: <named risk>)` — the demotion: not measured,
    accepted as an assumption with its risk stated. Distinct from
    `(assumed)`, which marks an unconfirmed *decision*; this marks an
    unmeasured *fact*, and the holder's action differs (order a
    measurement vs confirm a choice).
  Placement: one authority tag on a rule's title line; evidence tags sit
  on the empirical premise itself, in the rationale italics, with the
  measurement citation. Authority tags say *who decided*; evidence tags
  say *how we know* — they never compete for the same clause. Any
  mechanical check of these tags matches the **opening token only** —
  `(unverified)`, `(assumed-empirical:`, `(measured` — because tags with
  free text wrap at the document's line width: requiring the closing
  paren on the same line makes the miss silent on exactly the tag whose
  purpose is to be seen, and a wrapped `(measured …` a checker cannot
  fully parse is a *present* tag, never read as absent. For `unverified`
  the match is the whole word, anywhere: the word is reserved, so no
  prose position needs telling apart.
- **Must-read / supplement requirement:** each spec document is two
  parts. The **must-read** is on top and stands alone — for `spec.md`:
  `## Rules`, `## Scenarios`, `## Open Questions`, with **at most 3 lines
  per rule** (title line + rationale italics); for `technical-spec.md`:
  the numbered clauses (`G<k>`/`C<k>`) and the §5 port table. Everything
  else — background, current-state surveys, glossary, design notes,
  alternatives considered, worked examples — is the **supplement**: a
  trailing `## Supplement` section whose body is one
  `<details><summary>Supplement — <what it holds></summary>` block, and
  the last must-read line points at it ("Details in the supplement
  below."). A reader who needs more opens it; a reader who does not never
  scrolls past it. Section headings, rule and clause IDs, tags and the
  §5 table keep their exact shapes — the fold changes placement, never
  the things the hooks and checkers parse.
- **Scenario boundary:** scenario text states observable behaviour from
  an actor's observation surface — Given/When/Then only. Content
  addressed to another seat (test guidance, review guidance, "recorded so
  QA does not chase it") is a rule, or a note under the rule it derives
  from, never a scenario: an unfalsifiable scenario pollutes the
  coverage map, the evidence cards, and the (5q) audit permanently.
- **Port observability walk:** when the `implementer` designs the test
  port (§5), it walks every `spec.md` scenario once and appends the
  result to §5 as a per-scenario table — `S<k>` ×
  {observable / observable via `<control point>` / limitation: `<why>`}.
  A gap found here is a port fix on the spot; a **limitation is a verdict
  exemption**, and the implementer never grants its own: every
  limitation row is surfaced on the spec-gate kit's attention list for
  the gate holder to countersign. This table is what test-spec.md's
  "not testable through the port" section verifies at (4) instead of
  discovering.
- **ID citation convention:** wherever any agent cites a rule, scenario, or
  question ID in a comment, thread, or report, the first mention in that
  comment is written in full — `R7 · Expired offers don't count`, linked to
  the ID's definition line — never the bare code. The reader may be on a
  phone with no lookup table in their head.
- **Open Questions requirement:** `spec.md`'s `## Open Questions` section is
  the **single collection point for every seat's open questions**, whatever
  document the seat owns — (2a)'s threads anchor here and nowhere else, so a
  question written anywhere else has no route to the gate holder. Seats never
  write the section directly (em owns `spec.md`; concurrent writes and
  self-assigned numbers would break `(from Q<j>)` provenance): each dispatch
  **returns its question batch in its report**, and the main agent appends
  them — em/product first, implementer after — assigning `Q<k>` append-only
  for the life of the issue. The owning document may carry a pointer to a
  Q-ID; it never carries the question body. Each item uses the intake batch
  shape — phone-readable, and reused verbatim as its thread body in A6:
  - Title line `**[<role>] · Q<k> · <2–3-word label>**` — role = who raised
    it (`[product]`, `[em]`, or `[implementer]`; combine if more than one);
    items that challenge the user story / acceptance criteria append
    **(story-level)** to the title line.
  - Blank line, then the question as **one sentence**.
  - The options as **(a)/(b) bullets** — mark the recommended one
    `← ✅ recommended`; an option needing detail says so inline
    ("(b) a subset → say which"). One bullet per option, never prose: the
    forge renders consecutive lines as one paragraph, and guard-gate
    denies a question comment without them (rule F, #109).
  - The why as **one italic line**.

### A4. Commit + push
Dispatch the **commit** sub-agent (the plugin default `general-purpose`, on
`helper_model` from `bin/roz-config --json` when set; it dispatches nothing
itself) with, as its whole prompt,
`${CLAUDE_PLUGIN_ROOT}/references/commit-brief.md` plus the `<spec-branch>` worktree
path, the branch, the two spec docs and the commit message. It returns one
`branch · sha · hook` row; the pre-commit output stays in its context, not
yours. Push `<spec-branch>` from the returned `sha`; a `no-verify:` row is said
so in the report; a `failed:` row is a STOP with its excerpt in the report.

### A5. Open the CR
CR-OPEN from `<spec-branch>` targeting `<default_branch>`, title
`Spec: #<n> <title>`, body: "Stage (2) spec refinement for #<n>. For review.
Closes #<n>" — the (7) merge of this CR is the signature that closes the
issue; where the forge does not close on it, patrol's close-out does.

### A6. Post open questions as inline review threads
**Sweep first:** check the other spec docs for question-shaped content (an
open-questions section, unresolved "TBD"/"open:" items). Found → **move** it:
copy it verbatim into `spec.md`'s `## Open Questions`, tagged with the raising
role, and **delete it from the source document** — the section goes; at most a
one-line pointer to the Q-ID stays (A3's rule: the owning document never
carries the question body). A copy left behind is a second home for the same
text, and two homes drift — and guard-gate denies the commit mechanically
while a `technical-spec.md` under `<specs_dir>` still holds the section (the
deny message is the remedy). Do this before posting anything — a question
outside the threaded surface is invisible to every gate that counts threads,
and resolves the only way it can: silent interpretation. Then, for EACH item
in the `## Open Questions` section of `spec.md`:
THREAD-POST-INLINE on the spec CR, anchored to that item's line in
`<specs_dir>/<n>/spec.md`, body = **the item verbatim** (title line, blank
line, question, option bullets with the marked recommendation, italic why —
A3 already shaped it).
- **Every agent question comment MUST start with `**[`** — `/roz-gate:spec-answers`
  uses that marker to tell agent comments from the user's replies. The A3
  title line satisfies this by construction.
- For **(story-level)** items, end the body with one more italic line: *"If
  your decision changes the user story, I will mirror a note to issue #<n>."*

### A6b. Post the spec-gate kit
Assemble the **spec-gate kit** per
`${CLAUDE_PLUGIN_ROOT}/references/gate-kit.md` (blind-spot header,
attention list, issue-delta, decision ledger — ledger entries exist only
if intake carried rulings) and post it as **one top-level comment** on
the spec CR. This comment is the kit's permanent home — every later
update edits it in place (COMMENT-EDIT), never posts a sibling.

### A6c. Remove the worktree
`git worktree remove --force $(git rev-parse --git-common-dir)/roz-gate/wt/<spec-branch>`
then `git worktree prune` — `<spec-branch>` is on the remote; nothing local stays.

### A7. Flip labels — only AFTER the CR and threads are created
LABEL-REMOVE `status: ready-for-spec` and `status: processing`;
LABEL-ADD `status: in-spec-review`.

### A8. Report
Print the CR URL and the list of open-question threads. Never write code beyond
the two spec docs. **Next:** the user answers the threads;
`/roz-gate:spec-answers` folds them in; when all are resolved, the user
applies `status: ready-for-dev`.
