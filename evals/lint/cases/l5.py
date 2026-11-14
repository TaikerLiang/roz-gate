"""L5 · the config block has two homes                        (defect 1.31.1-, #94)
CLAUDE.md, then CLAUDE.local.md — in the toplevel, then in the main
checkout (CLAUDE.local.md is untracked: a linked worktree has none). Every
hook loader opened CLAUDE.md only; a project that kept its block in
CLAUDE.local.md (ADMC, its PR #62) was "not a roz-gate project" to four
rules — guard-acceptance and rule D off, rule A in user mode, rule E
without its suite exemption — while the commands, which read the block
from Claude Code's context where both files land, ran the loop. One reader
(hooks/config_block.py) for every loader, and the prose says what the hooks
do. 2.4.0 (#165): the acceptance prefilter's grep is for the template, now
the local file's — in both places, this toplevel and the main checkout.
#277: the acceptance prefilter is gone (a thin wrapper); guard_acceptance.py
resolves the toplevel, the main checkout, the block and the local file from
the edited file's worktree — the reader takes the place it is given.
"""

from lib.lintkit import must_not_match, read, src

META = {
    "id": 'L5',
    "title":
        'the config block has two homes — `CLAUDE.md`, then `CLAUDE.local.md`, in the toplevel,'
        " then in the main checkout; the hooks' one reader (`hooks/config_block.py`), "
        "guard-acceptance, every command's step 0 and the docs agree",
    "tier": 'lint (defect 1.31.1-, #94)',
    "ledger": None,
}

_HOMES = ("hooks/guard_blind.py", "hooks/guard_acceptance.py", "hooks/guard_gate.py")
src("L5: config_block.py is the one reader", "hooks/config_block.py",
    "def find_block(top, main=None):")
src("L5: the reader's order is CLAUDE.md, then CLAUDE.local.md", "hooks/config_block.py",
    'HOMES = ("CLAUDE.md", "CLAUDE.local.md")')
src("L5: the reader falls back to the main checkout", "hooks/config_block.py",
    "def main_checkout(cwd=None):")
src("L5: the reader's fallback is the main checkout of the toplevel it is given (#277)",
    "hooks/config_block.py", "main = main or main_checkout(top)")
for _f in _HOMES:
    src("L5: %s imports the reader" % _f, _f, "from config_block import find_block")
    must_not_match("L5: %s never opens a CLAUDE.md of its own" % _f, r'CLAUDE\.md"', read(_f))
src("L5: guard-acceptance resolves the main checkout from the file's worktree (#277)",
    "hooks/guard_acceptance.py", "main_root = main_checkout(top)")
src("L5: guard-acceptance reads the block and the local file in the same two places (#277)",
    "hooks/guard_acceptance.py", 'find_block(top, main)')
src("L5: …the local file: this toplevel's, else the main checkout's (#165, #277)",
    "hooks/guard_acceptance.py", 'local_key_source((top, main), "branch_template")')
src("L5: the reader honours core.worktree", "hooks/config_block.py", '"core.worktree"')
for _f in ("commands/integrate.md", "commands/next-stage.md", "commands/patrol.md",
           "commands/review-answers.md", "commands/spec-answers.md", "commands/to-issues.md",
           "commands/uninit.md"):
    src("L5: %s step 0 names both homes" % _f, _f,
        "block in the project's CLAUDE.md (or CLAUDE.local.md)")
src("L5: uninit removes the section from whichever file carries it (codex, PR #100)",
    "commands/uninit.md", "**CLAUDE.md** — or **CLAUDE.local.md**, whichever carries it")
src("L5: config's hard rule covers both homes", "commands/config.md",
    "`CLAUDE.md` or `CLAUDE.local.md`\nyourself")
src("L5: README names the second home", "README.md",
    "The block may live in `CLAUDE.local.md`")
src("L5: hooks/README names both homes", "hooks/README.md",
    "config block in `CLAUDE.md` or `CLAUDE.local.md`")
src("L5: hooks/README lists the reader", "hooks/README.md", "| `config_block.py` |")
src("L5: the onboarding page names the second home", "docs/onboarding.html",
    "or kept in CLAUDE.local.md")
