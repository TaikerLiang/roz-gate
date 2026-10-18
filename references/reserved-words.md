# Reserved words

The loop's English is code, and these are its keywords. A reserved word has
one meaning, fixed by a ruling, and one form. In every English-as-code file
of this plugin — `agents/`, `commands/`, `references/`, `templates/` — it
appears only in code formatting or as the tag its row names; a bare use in
prose is a violation, and the remedy is to reword the sentence, never to
allow the hit (#123, #154). Lint B9 reads this table and checks every row: a
bare use in those four directories, a Path B or promote grep that does not
cover the word, or an empty table is red.

Adding a word takes one ruling by the maintainer and one row here, and the
`grep -nwi` lines in `commands/next-stage.md` (Path B) and
`commands/spec-answers.md` (promote) extended to the word; B9 names each site
that still has to change. A candidate is never listed.

| word | reserved for | the only form it takes | since |
|---|---|---|---|
| `unverified` | the evidence tag on an empirical claim in a spec document (A3): asserted, load-bearing, and nobody has checked | `(unverified)` as a tag in a spec document; in this plugin's files, code formatting only | 1.37.0 (#123); registered 2.2.0 (#154) |
