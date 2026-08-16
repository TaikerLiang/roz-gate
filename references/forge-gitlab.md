# Forge adapter — GitLab (`glab`)

Concrete CLI for every forge operation the roz-gate commands name. All `glab`
calls infer the project from the current directory's git remote. Vocabulary: a
**change request (CR)** is a GitLab **Merge Request**. Works with gitlab.com and
self-hosted instances (`glab auth login --hostname <host>` first).

Prerequisite: `glab auth status` succeeds for the remote's host.

## Identity

Two modes, set by `agent_identity` in the Roz Gate config (key absent →
`user`):

- **`user`** (default): every op runs as the human's `glab auth login`
  session — the pre-1.7.0 behavior, unchanged.
- **`bot`**: every CAPITALIZED-OP runs as the project's **project access
  token** bot (`bot_login` = its full username,
  `project_<id>_bot_<hash>`; one-time setup in
  `references/identity-github-app.md`, GitLab section):
  - Pass the token **per invocation**: `GITLAB_TOKEN=<token> glab …` —
    honored by both `glab api` and the CLI subcommands (`issue note`,
    `issue update`, `issue list`, …). **Never export it into the session
    environment.**
  - `glab api` POST/PUT bodies with array or nested params (e.g.
    `scopes`, `position`) must be sent as JSON —
    `--input -` plus `-H 'Content-Type: application/json'`; form
    encoding of arrays fails.
  - ISSUE-CREATE always sets `assignee_ids` to the config's `operator` —
    a bot-authored issue must never be born holder-less; a bot is never
    a gate holder.
  - Git: push over HTTPS —
    `git push https://<any-name>:<token>@gitlab.com/<path>.git <branch>`
    (the basic-auth username is arbitrary) — and commit with per-command
    `git -c user.name/-c user.email` author flags, never writing
    identity into the repo's git config.

## Labels: the scoped-label scheme

GitLab **scoped labels** (`key::value`) let the platform enforce "at most one
label per scope" natively — roz-gate uses this deliberately:

- `track::spec` / `track::fast` — scoped: **exactly-one-track is enforced by the platform.**
- `status::ready-for-spec`, `status::ready-for-dev`, `status::in-spec-review`,
  `status::in-user-review`, `status::blocked` — scoped: at-most-one-status enforced.
- `processing` — a **plain, unscoped label**, deliberately outside the `status::`
  scope. The lock must **coexist** with the phase label it locks (a stale
  `processing` + phase pair is the crash-forensics record); a scoped
  `status::processing` would silently replace the phase label and destroy that
  evidence. Never scope the lock.

Wherever a command names a label like `status: ready-for-spec`, read it as
`status::ready-for-spec` on GitLab; `status: processing` is the plain label
`processing`.

## Issues & labels

| Op | Command |
|---|---|
| ISSUE-LIST | `glab issue list --output json` (add `--label "<label>"` to filter) |
| ISSUE-VIEW | `glab issue view <n> --output json` (comments: `glab api "projects/:id/issues/<n>/notes"`) |
| LABEL-ADD | `glab issue update <n> --label "<label>"` |
| LABEL-REMOVE | `glab issue update <n> --unlabel "<label>"` |
| ISSUE-COMMENT | `glab issue note <n> --message "..."` |
| COMMENT-EDIT | `glab api -X PUT "projects/:id/merge_requests/<iid>/notes/<note-id>" -f body="..."` (issues: same shape under `issues/<n>/notes/<note-id>`) |
| ISSUE-CREATE | `glab issue create --title "..." --description "..." [--label "<label>"]` |
| ISSUE-EDIT-BODY | `glab issue update <n> --description "..."` (async intake only, after the user's `approve`) |

## Change requests

| Op | Command |
|---|---|
| CR-OPEN | `glab mr create --source-branch <branch> --target-branch <target> --title "..." --description "..."` |
| CR-OPEN-DRAFT | same + `--draft` |
| CR-READY | `glab mr update <mr> --ready` |
| CR-FIND | `glab mr list --source-branch <branch> --output json` |
| CR-VIEW | `glab mr view <mr> --output json` (`draft` field) |
| CR-MERGE | `glab mr merge <mr>` (the human's act at (7) — commands never run this) |

## Review threads (GitLab: "discussions")

All REST, via `glab api`. `:id` is auto-resolved by glab to the current project.
`<iid>` is the MR's internal id.

**THREADS-LIST** — every discussion with resolution state and notes:

```
glab api "projects/:id/merge_requests/<iid>/discussions?per_page=100"
```

Each discussion has `id`, `notes[]` (with `id`, `body`, `author.username`,
`resolvable`, `resolved`). A thread is "unresolved" if any resolvable note has
`resolved: false`.

**THREAD-POST-INLINE** — open a discussion anchored to a file line. GitLab
needs a `position` object with the MR's diff SHAs — fetch them once:

```
glab api "projects/:id/merge_requests/<iid>" --jq .diff_refs
# → { base_sha, head_sha, start_sha }
glab api -X POST "projects/:id/merge_requests/<iid>/discussions" \
  -f body="..." \
  -f "position[position_type]=text" \
  -f "position[base_sha]=<base_sha>" -f "position[head_sha]=<head_sha>" \
  -f "position[start_sha]=<start_sha>" \
  -f "position[new_path]=<file>" -F "position[new_line]=<line>"
```

**THREAD-REPLY** — add a note to an existing discussion:

```
glab api -X POST "projects/:id/merge_requests/<iid>/discussions/<discussion_id>/notes" \
  -f body="..."
```

**THREAD-RESOLVE** — resolve the whole discussion:

```
glab api -X PUT "projects/:id/merge_requests/<iid>/discussions/<discussion_id>" \
  -F resolved=true
```

## Bootstrap (used by /roz-gate:init)

| Op | Command |
|---|---|
| LABEL-CREATE | `glab label create --name "<label>" --color "<hex>" --description "..."` |
| LABEL-DELETE | `glab label delete "<label>"` (erases it from closed issues too — `/roz-gate:uninit` only, on explicit request) |
| ISSUE-TEMPLATE-PATH | `.gitlab/issue_templates/idea.md` |

Create the scoped names exactly as written (`track::spec` etc.) plus the plain
`processing`. Suggested colors as in the GitHub adapter.

## Known differences that matter to the loop

- **Draft flag** lives in the MR's `draft` field (CR-VIEW), not `isDraft`.
- **Inline anchoring** needs the three diff SHAs; if a spec-doc line moved after
  a rebase, re-fetch `diff_refs` before posting. After any push, `diff_refs`
  refreshes **asynchronously** — re-fetch until `head_sha` equals the pushed
  commit, or the position post 500s.
- Thread resolution is per-discussion (one call), not per-GraphQL-node — simpler
  than GitHub here.
