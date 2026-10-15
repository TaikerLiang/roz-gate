# Fixture: the #123 defect channel — the reserved word loose in prose, wrapped
# so that it opens a line (ADMC, docs/specs/12/technical-spec.md, verbatim).

C4 (R7) — 404 mechanism, fully measured. A nonexistent workspaceName must be rejected by throwing
NotFoundResponseException, mirroring WorkspacesService.getWorkspace's existing orElseThrow on
WorkspaceRepo.findByWorkspaceName (WorkspacesService.java:130-136). The resulting HTTP contract, confirmed by reading the
handler (not citing #8's claim
unverified):
