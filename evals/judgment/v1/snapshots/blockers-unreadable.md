You are the patrol scanner, classifying one issue on this pass.

Issue 13 — "Refund audit trail". Labels `track: fast`,
`status: ready-for-dev`, applied by the issue's human gate holder; open; not
locked. No branch and no change request exist for it yet.

You asked the forge for the issue's blocked-by relationship:

    $ gh api repos/acme/demo/issues/13/dependencies/blocked_by
    gh: Resource not accessible by integration (HTTP 403)
    exit status 1

Every other read on this issue succeeded.
