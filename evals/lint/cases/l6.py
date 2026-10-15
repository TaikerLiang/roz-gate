"""L6 · the test keys say where the command runs               (defect 1.36.0-, #99)
`test` and `acceptance_test` run in a linked worktree under
.git/roz-gate/wt/<branch>, where `.git` is a file. A tool that resolves it
as a directory (Maven's git-commit-id plugin: "Could not get HEAD Ref")
fails there and needs its worktree-safe flag. README § Troubleshooting
said so once, but nothing where an adopter fills the two keys in — README's
config block, init's prompt, the onboarding builder — so ADMC's first
integration red (./mvnw test) was a harness issue read as a verdict. The
sentence lives on every surface that asks for the keys — and each surface
is pinned twice: the where (a linked worktree, never the checkout) and the
failure (the flag), so neither half can go alone (codex, PR #117).
"""

from lib.lintkit import src

META = {
    "id": 'L6',
    "title":
        '`test` and `acceptance_test` are documented as running in a linked worktree, never in '
        "the checkout, on every surface an adopter fills them in — README's config block, "
        "init's prompt, the onboarding builder — with the `.git`-as-a-directory failure named",
    "tier": 'lint (defect 1.36.0-, #99)',
    "ledger": None,
}

src("L6: README's config block marks test as running in a linked worktree", "README.md",
    "e.g. uv run pytest / npm test — in a linked worktree")
src("L6: README's config block marks acceptance_test the same way", "README.md",
    "<one feature's acceptance command>   in a linked worktree")
src("L6: README says under the block: a linked worktree, never your checkout", "README.md",
    "run **in a linked worktree** (`git worktree add`,\n"
    "under `.git/roz-gate/wt/<branch>`), never in your checkout")
src("L6: README names the .git-as-a-directory failure under the block", "README.md",
    "needs its worktree-safe flag (`-Dmaven.gitcommitid.skip=true`)")
src("L6: init says where as it asks for the two commands", "commands/init.md",
    "they run **in a linked worktree**\n"
    "  (`git worktree add`, under `.git/roz-gate/wt/<branch>`), never in the\n"
    "  checkout")
src("L6: init names the failure as it asks for the two commands", "commands/init.md",
    "needs its worktree-safe flag")
src("L6: the onboarding builder's hint says where (en)", "docs/onboarding.html",
    "Both commands run in a <b>linked worktree</b> "
    "(<code>.git/roz-gate/wt/&lt;branch&gt;</code>), never in your checkout")
src("L6: the onboarding builder's hint names the failure (en)", "docs/onboarding.html",
    "needs its worktree-safe flag (<code>-Dmaven.gitcommitid.skip=true</code>)")
src("L6: the onboarding builder's hint says where (zh)", "docs/onboarding.html",
    "兩個指令都在 <b>linked worktree</b>(<code>.git/roz-gate/wt/&lt;branch&gt;</code>)裡跑,"
    "絕不在你的 checkout")
src("L6: the onboarding builder's hint names the failure (zh)", "docs/onboarding.html",
    "worktree-safe 旗標")
