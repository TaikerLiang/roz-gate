You are grading a document against one criterion. Judge only what the document says; do not use outside knowledge of the project.

Criterion: {criterion}

Document (between the markers):
<<<DOCUMENT
{document}
DOCUMENT>>>

Answer with JSON only, no prose, no code fence:
{"answer": "yes" | "no", "quote": "<a verbatim excerpt from the document, at least 40 characters, that satisfies the criterion — or an empty string when the answer is no>"}

"Verbatim" means copied exactly, character for character, from the document. Do not paraphrase, shorten with ellipses, or merge separate passages. If you cannot copy such an excerpt, the answer is no.
