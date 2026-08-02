# Forge adapter — GitLab (`glab`)

Concrete CLI for every forge operation the gated-loop commands name. All `glab`
calls infer the project from the current directory's git remote. Vocabulary: a
**change request (CR)** is a GitLab **Merge Request**. Works with gitlab.com and
self-hosted instances (`glab auth login --hostname <host>` first).

Prerequisite: `glab auth status` succeeds for the remote's host.

## Labels: the scoped-label scheme

GitLab **scoped labels** (`key::value`) let the platform enforce "at most one
label per scope" natively — gated-loop uses this deliberately:

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

## Bootstrap (used by /gated-loop:init)

| Op | Command |
|---|---|
| LABEL-CREATE | `glab label create --name "<label>" --color "<hex>" --description "..."` |
| ISSUE-TEMPLATE-PATH | `.gitlab/issue_templates/idea.md` |

Create the scoped names exactly as written (`track::spec` etc.) plus the plain
`processing`. Suggested colors as in the GitHub adapter.

## Known differences that matter to the loop

- **Draft flag** lives in the MR's `draft` field (CR-VIEW), not `isDraft`.
- **Inline anchoring** needs the three diff SHAs; if a spec-doc line moved after
  a rebase, re-fetch `diff_refs` before posting.
- Thread resolution is per-discussion (one call), not per-GraphQL-node — simpler
  than GitHub here.
