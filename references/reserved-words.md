# Reserved words

The loop's English is code, and these are its keywords. A reserved word has
one meaning, fixed by a ruling, and one form. In every English-as-code file
of this plugin — `agents/`, `commands/`, `references/`, `templates/` — it
appears only in code formatting or as the tag its entry names; a bare use in
prose is a violation, and the remedy is to reword the sentence, never to
allow the hit (#123, #154).

The list is `reserved-words.json`, beside this file — the registry that lint
and agents read. One entry per word:

| field | meaning |
|---|---|
| `word` | the reserved word, lower case |
| `reserved_for` | what the word means in the loop, and where |
| `form` | the only form it takes in a spec document, and in this plugin's files |
| `spec_gate` | `true` when a bare use blocks a spec document: Path B and promote grep for it |
| `since` | the version that reserved it |
| `ruling` | the issue that ruled it |
| `registered` | the version and issue that added the entry |

Lint B9 reads the registry and checks every entry: a bare use in the four
directories' Markdown, a Path B or promote grep that does not cover a
`spec_gate` word, or an empty registry is red.

A word qualifies when it is a protocol literal — a label value, a tag, a
review severity, a forge event type, a table-row value the loop reads or
writes verbatim — and its ordinary English reading differs from that
meaning (#160). A defined term is a glossary concept, not a reserved word.
Adding a word takes one ruling by the maintainer and one entry in the
registry; for a `spec_gate` word, the `grep -nwi` lines in
`commands/next-stage.md` (Path B) and `commands/spec-answers.md` (promote)
are extended to it too. B9 names each site that still has to change. A
candidate is never listed.
