"""C6 · CR lookup sees merged CRs where it must              (defect: 1.11.0-)
"""

from lib.lintkit import c, must_match, read, src

META = {
    "id": 'C6',
    "title": 'CR lookup sees merged CRs where it must',
    "tier": 'lint (defect 1.11.0-)',
    "ledger":
        "— (amended for #77, 1.30.0: the scanner's in-flight row also reads the all-states form"
        ' — a merged `feat`/`qa` CR satisfies "exists, thread-clean, not a draft", so '
        'both-merged routes to the re-verdict; the guard that held the row to the open-only '
        'default is gone)',
}

gh_crfind = "\n".join(line for line in read("references/forge-github.md").splitlines()
                      if "CR-FIND" in line)
gl_crfind = "\n".join(line for line in read("references/forge-gitlab.md").splitlines()
                      if "CR-FIND" in line)
c.expect("pattern", "C6: github adapter CR-FIND documents --state all for merged CRs",
         "--state all" in gh_crfind)
c.expect("pattern", "C6: gitlab adapter CR-FIND documents --all for merged MRs",
         "--all" in gl_crfind)
src("C6: the post-integration detection path cites the all-states form",
    "commands/spec-answers.md", "all-states form")
# 1.30.0 (#77): the in-flight row joins the readers. Until then this block
# held it to the open-only default; a merged feat/qa CR therefore read as
# absent, a both-merged issue (the human cleared a STOP, or moved the spec
# branch) classified "in progress" forever, and the re-verdict never ran.
inflight = "\n".join(line for line in read("references/patrol-scan.md").splitlines()
                     if "no `status:`, `track: spec`" in line)
must_match("C6: patrol's in-flight row cites the all-states form", r"all-states form", inflight)
src("C6: integrate's CR lookup cites the all-states form", "commands/integrate.md",
    "all-states form")
