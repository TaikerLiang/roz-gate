"""E7 · a question's options reach the holder as a list       (defect: 1.34.1-)
Issue #109: a (2a) thread wrote its options as prose, and the forge
rendered them as one paragraph on the holder's phone. Teeth since 1.35.0:
guard-gate rule F denies the comment (proven in hooks/tests/). The static
layer: the shape is stated in both homes, both name the teeth, the hook's
message is the remedy, the rule tables carry the row.
"""

from lib.lintkit import src

META = {
    "id": 'E7',
    "title": "A question's options reach the holder as a list",
    "tier": 'hook (guard-gate rule F) + lint',
    "ledger":
        '"Each question block carries at least two option bullets — `- (a) …`, `- (b) …`; a '
        'comment without them is denied before it posts." (a (2a) thread wrote the options as '
        "prose; the forge rendered them as one paragraph on the holder's phone, with nothing "
        'for the `3a` shorthand to point at — issue #109)',
}

src("E7: A3 states the options as bullets", "commands/next-stage.md",
    "The options as **(a)/(b) bullets**")
src("E7: A3 names the teeth", "commands/next-stage.md",
    "guard-gate\n    denies a question comment without them (rule F, #109)")
src("E7: the intake batch states the options as bullets", "references/intake-brief.md",
    "then the options as **(a)/(b) bullets**")
src("E7: the intake batch names the teeth", "references/intake-brief.md",
    "guard-gate denies the comment without them\n       (rule F, #109)")
src("E7: the hook's message is the remedy", "hooks/guard_gate.py",
    "`- (a) …` / `- (b) … ← ✅ recommended`")
src("E7: README carries row F", "README.md", "| **F** | a question comment")
src("E7: docs/index.html carries row F", "docs/index.html", "<tr><td><b>F</b></td>")
src("E7: hooks/README carries row F", "hooks/README.md",
    "| **F** question options are bullets |")
