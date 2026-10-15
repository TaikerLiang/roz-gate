"""C18 · a STOP comment names its resume move                   (defect: 1.35.0-)
Issue #98 (ADMC #73): the human read the STOP comment, left `blocked` on
and wrote the amendment as a top-level CR comment — neither heard; the
comment in front of them named no label move and no channel. Teeth since
1.36.0: guard-gate rule G denies a `· blocked`-titled comment without the
line (proven in hooks/tests/). The static layer: the protocol holds the
template, every spelled-out STOP section fills in its phase, the hook's
message is the remedy, the rule tables carry the row.
"""

from lib.lintkit import src

META = {
    "id": 'C18',
    "title": 'A STOP comment names its resume move',
    "tier": 'hook (guard-gate rule G) + lint',
    "ledger":
        '"The STOP comment opens with `**[<command>] · blocked**` and its must-read ends with '
        '`**To resume:**` — the label to clear, the phase to apply, where the answer goes; a '
        '`blocked`-titled comment without the line is denied before it posts." (ADMC #73: the '
        'human read the STOP, left `blocked` on and wrote the amendment as a top-level CR '
        'comment — neither heard; the comment in front of them named no label move and no '
        'channel — issue #98)',
}

src("C18: the STOP protocol fixes the title", "references/workflow.md",
    "it opens with the\ntitle `**[<command>] · blocked**`")
src("C18: the STOP protocol holds the resume template", "references/workflow.md",
    "**To resume:** clear `status: blocked`, apply `status: <phase>` — yourself,\n"
    "or tell the main agent; <where the answer goes>")
src("C18: spec-answers resumes at in-spec-review and answers on the spec CR",
    "commands/spec-answers.md",
    "apply `status: in-spec-review` — yourself, or tell the\nmain agent; an answer or "
    "amendment goes on the spec CR")
src("C18: next-stage resumes at the gate label it consumed", "commands/next-stage.md",
    "**To resume:**\nclear `status: blocked`, apply the gate label this run consumed")
src("C18: integrate resumes by clearing blocked alone", "commands/integrate.md",
    "**To resume:** clear `status: blocked` — nothing else")
src("C18: the hook's message is the remedy", "hooks/guard_gate.py",
    "ends its must-read with the resume ")
src("C18: README carries row G", "README.md", "| **G** | a STOP comment")
src("C18: docs/index.html carries row G", "docs/index.html", "<tr><td><b>G</b></td>")
src("C18: hooks/README carries row G", "hooks/README.md",
    "| **G** a STOP comment names its resume move |")
