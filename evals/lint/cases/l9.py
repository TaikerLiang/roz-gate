"""L9 · the pages say patrol answers intake comments               (defect 2.4.0-, #174)
Every page that told a reader the thread "belongs to the humans" after the
batch — README's inbox, workflow (1b), the wire spec, the participant
guide, the interactive guide's simulator and wizard, the onboarding beat,
the quiz — now says the same thing: patrol answers every human comment on
its next pass, an answer and never a decision. One sentence on every
surface (en; zh where the page is bilingual), and the retired wording gone.
"""

from lib.lintkit import c, read

META = {
    "id": "L9",
    "title": "Every page says patrol answers every human comment on an intake thread on its "
             "next pass, and none still hands the thread to the humans",
    "tier": "lint (defect 2.4.0-, #174)",
    "ledger": None,
}

EN = "answers every human comment on its next pass"
ZH = "每則人類留言都會在下一輪得到回覆"
RETIRED = ("the thread belongs to the humans", "leaves the thread to the humans",
           "leaves the thread to humans", "won\\'t interfere", "do nothing: the thread",
           "討論串屬於人類", "patrol 不會插手", "把討論串留給人", "把討論留給人")


def flat(relpath):
    return " ".join(read(relpath).split())


for _f in ("README.md", "references/workflow.md", "docs/protocol.md", "docs/participating.md",
           "docs/index.html", "docs/onboarding.html"):
    c.expect("pattern", "L9: %s says patrol %s" % (_f, EN), EN in flat(_f))
for _f in ("docs/index.html", "docs/onboarding.html", "docs/learn/quiz.json"):
    c.expect("pattern", "L9: %s says it in zh" % _f, ZH in flat(_f))
for _f in ("README.md", "references/workflow.md", "docs/protocol.md", "docs/participating.md",
           "docs/index.html", "docs/onboarding.html", "docs/learn/quiz.json",
           "commands/patrol.md", "commands/tip.md"):
    _t = flat(_f)
    for _r in RETIRED:
        c.expect("pattern", "L9: %s no longer says %r" % (_f, _r), _r not in _t)
c.expect("pattern", "L9: the wire spec lists the reply marker",
         "`**[intake] · reply**` — an answer to the human comments" in flat("docs/protocol.md"))
