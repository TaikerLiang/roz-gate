"""L10 · the loop's worktrees get your gitignored files            (defect 2.5.1-, #122)
Every loop command works in a linked worktree under
`<git-common-dir>/roz-gate/wt/<branch>`, and a gitignored file — `.env`
first — is not in a fresh one: a repo whose `test` loads it went red there
for harness reasons. Since #122 the plugin's PostToolUse hook
`sync-worktree` copies `worktree_copy` (a local key, default `.env`) in as
`git worktree add` returns. Every surface that says where `test` runs says
so, `/roz-gate:config` offers the key, and `hooks.json` registers the hook;
hooks/tests prove the copy.
"""

import json

from lib.lintkit import c, read

META = {
    "id": "L10",
    "title": "Every surface that says where `test` runs says your gitignored files "
             "(`worktree_copy`, default `.env`) are copied into the loop's worktrees, and "
             "`hooks.json` registers the PostToolUse hook that does it",
    "tier": "lint (defect 2.5.1-, #122)",
    "ledger": None,
}

EN = "your gitignored files (`worktree_copy`, default `.env`) are copied in"
ENH = "your gitignored files (<code>worktree_copy</code>, default <code>.env</code>) are copied in"
ZHH = "你的 gitignored 檔案(<code>worktree_copy</code>,預設 <code>.env</code>)會被複製進去"


def flat(relpath):
    return " ".join(read(relpath).split())


for _f in ("README.md", "references/workflow.md", "commands/init.md"):
    c.expect("pattern", "L10: %s says %s" % (_f, EN), EN in flat(_f))
_on = flat("docs/onboarding.html")
c.expect("pattern", "L10: the onboarding test-key hint says it (en)", ENH in _on)
c.expect("pattern", "L10: the onboarding test-key hint says it (zh)", ZHH in _on)
c.expect("pattern", "L10: the onboarding builder has a worktree_copy field that renders a "
                    "/roz-gate:config line",
         'id="f_wcopy"' in _on and "['worktree_copy', () => $('f_wcopy').value.trim()]" in _on)
c.expect("pattern", "L10: /roz-gate:config's menu explains worktree_copy and its default",
         "`worktree_copy` — your gitignored files the plugin's `sync-worktree` hook copies"
         in flat("commands/config.md") and "default = `.env`" in flat("commands/config.md"))
_hooks = json.loads(read("hooks/hooks.json")).get("hooks", {})
c.expect("pattern", "L10: hooks.json registers sync-worktree.sh as PostToolUse on Bash",
         any(e.get("matcher") == "Bash"
             and any("hooks/sync-worktree.sh" in h.get("command", "") for h in e.get("hooks", []))
             for e in _hooks.get("PostToolUse", [])))
c.expect("pattern", "L10: hooks/README.md explains the worktree copy",
         "## The worktree copy" in read("hooks/README.md"))
