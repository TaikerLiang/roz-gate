"""E8 · a top-level comment on the spec CR is heard as an amendment
(defect: 1.35.0-, #98) — replay E8 proves the fold; the static layer:
spec-answers names the three channels, routes a no-path item to
product, replies through an op both adapters name.
"""

from lib.lintkit import src

META = {
    "id": 'E8',
}

src("E8: spec-answers reads the three channels", "commands/spec-answers.md",
    "On each CR: THREADS-LIST (inline threads), REVIEWS-LIST")
src("E8: a top-level item is product's", "commands/spec-answers.md",
    "has no path, so it is `product`'s")
src("E8: the reply to a top-level item is a CR-COMMENT", "commands/spec-answers.md",
    "A top-level item has no thread: CR-COMMENT")
src("E8: a cited top-level item is heard — never folded twice (codex review, PR #114)",
    "commands/spec-answers.md",
    "**and no later top-level\n  comment opening with `**[` or `✅ [` cites it**")
src("E8: the GitHub adapter names CR-COMMENT", "references/forge-github.md",
    '| CR-COMMENT | `gh pr comment <pr> --body "..."`')
src("E8: the GitLab adapter names CR-COMMENT", "references/forge-gitlab.md",
    '| CR-COMMENT | `glab mr note <iid> --message "..."`')
src("E8: spec-answers never folds the gate kit (#193)", "commands/spec-answers.md",
    "**The gate-kit comment is the loop's own, never an\n  item**")
src("E8: review-answers never hears the gate kit (#193)", "commands/review-answers.md",
    "The gate-kit comment is the loop's own, never an item")
src("E8: tip never counts the gate kit unheard (#193)", "commands/tip.md",
    "the gate-kit comment is the loop's own, never an item")
src("E8: patrol never dispatches on the gate kit (#193)", "references/patrol-scan.md",
    "the gate-kit comment is the loop's own, never an item")
