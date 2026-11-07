"""E11 · A fold may ask once — the second-order question is deferred  (#206)
ConsoleAPI #1: folding Q6/Q7 raised product's Q8/Q9 and the issue went back
behind the human gate for another pass; nothing bounded the chain. Ruling
(c): a fold may post new questions once; a question raised by answering a
fold-raised question is `· deferred` — in `spec.md`'s `## Open Questions`
(the single collection point, A3), no thread, one CR comment — and resolves
to its recommendation at `ready-for-dev`. Replay E11 measures the deferred
half on a run; this case holds the statements on every surface.
"""

from lib.lintkit import src

META = {
    "id": 'E11',
}

src("E11: spec-answers states the rule", "commands/spec-answers.md",
    "**A fold may ask once** (#206)")
src("E11: the seat returns the batch, never writes the section", "commands/spec-answers.md",
    "it never writes\n   `## Open Questions` itself")
src("E11: depth is read from the provenance line", "commands/spec-answers.md",
    "carries the italic line *raised by the fold of Q<i>* or it does not")
src("E11: depth 0 posts the thread with the provenance line", "commands/spec-answers.md",
    "*raised by the fold of Q<j>* — and THREAD-POST-INLINE it as A6 does")
src("E11: depth 1 marks the item deferred", "commands/spec-answers.md",
    "the title line ending `· deferred`")
src("E11: depth 1 posts no thread", "commands/spec-answers.md",
    "and post **no thread**")
src("E11: one top-level deferred comment", "commands/spec-answers.md",
    "CR-COMMENT `**[spec-answers] · deferred**` lists the deferred items")
src("E11: a follow-up is not a new question", "commands/spec-answers.md",
    "is not a new question and is never\n   deferred")
src("E11: §7 reports deferred items apart from threads", "commands/spec-answers.md",
    "`deferred: Q<k>, … — recommendations stand unless answered`")
src("E11: next-stage resolves deferred items by default at ready-for-dev",
    "commands/next-stage.md", "**Deferred questions resolve by default here**\n(#206)")
src("E11: a rule born from a deferred item carries (assumed)", "commands/next-stage.md",
    "carries `(assumed)` as its\nprovenance, never `(from Q<k>)`")
src("E11: the implementer's dispatch names the default", "commands/next-stage.md",
    "a `· deferred` item in `## Open Questions`")
src("E11: the gate kit sorts open deferred items to the top", "references/gate-kit.md",
    "`· deferred`")
src("E11: the product brief — the batch comes back, the seat never posts", "agents/product.md",
    "a fold may\n  ask once")
src("E11: the em brief — the batch comes back, the seat never posts", "agents/em.md",
    "a fold may\n  ask once")
src("E11: workflow (2a) states the rule", "references/workflow.md",
    "A fold may ask once (#206)")
src("E11: README's (2a) row states the rule", "README.md",
    "a fold may ask once — a question raised by answering a fold-raised question is `· deferred`")
src("E11: the (2a) card on the live page", "docs/index.html",
    "A fold may ask once: a question raised by answering a fold-raised question is <i>deferred</i>")
src("E11: the onboarding walkthrough on the live page", "docs/index.html",
    "A fold may ask once; a follow-on question it cannot ask is listed as <i>deferred</i>")
