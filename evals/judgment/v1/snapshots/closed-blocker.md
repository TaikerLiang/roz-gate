You are the patrol scanner, classifying one issue on this pass.

Issue 12 — "Order history export". Labels `track: spec`,
`status: ready-for-spec`, applied by the issue's human gate holder; open;
not locked. No branch and no change request exist for it yet.

You asked the forge for the issue's blocked-by relationship:

    $ gh api repos/acme/demo/issues/12/dependencies/blocked_by
    [{"number": 8, "state": "closed", "title": "Order ledger schema"}]

Every other read on this issue succeeded. The issue has no unread comments.
