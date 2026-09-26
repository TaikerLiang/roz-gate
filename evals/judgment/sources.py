#!/usr/bin/env python3
"""The judgment tier's source repository: where the ADMC clone lives, and
whether it holds every commit the fixtures need.

    python3 evals/judgment/sources.py        # clone or fetch, then verify

ADMC is private, so no copy of it is ever committed here. The clone lives
at a gitignored path inside this repo (sources.yaml `admc_path`, relative
to this directory) or wherever ROZ_GATE_ADMC points — e.g. an existing
checkout. This script is the one step that touches the network; every
run clones its sandbox from the local clone (run_judgment.py).

Needed commits: each fixture's pin (the sandbox's main), CONFIG_SOURCE
(the overlay's config block) and each refinement_commit (materialize.py's
historical output). A missing one is reported by name, with the remedy.
"""

import glob
import json
import os
import re
import subprocess
import sys

S = os.path.dirname(os.path.abspath(__file__))
ENV = "ROZ_GATE_ADMC"
CONFIG_SOURCE = "d2ded1269c1c"  # the last commit whose CLAUDE.md carries the section in git


def _yaml(key):
    for line in open(os.path.join(S, "sources.yaml"), encoding="utf-8"):
        m = re.match(r"^%s:\s*(\S+)" % key, line)
        if m:
            return m.group(1)
    sys.exit("sources.yaml: no %s" % key)


def remote():
    return _yaml("admc_remote")


def admc_path():
    """The local clone: ROZ_GATE_ADMC if set, else sources.yaml's admc_path
    relative to evals/judgment/."""
    override = os.environ.get(ENV)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.abspath(os.path.join(S, _yaml("admc_path")))


def needed(cases=None):
    """{commit: why} for the given fixture names (default: all) — one commit
    may serve several (d2ded12 is two pins and the overlay's source)."""
    out = {CONFIG_SOURCE: "the config overlay (CONFIG_SOURCE)"}

    def add(sha, why):
        out[sha] = out[sha] + "; " + why if sha in out else why

    for f in sorted(glob.glob(os.path.join(S, "cases", "*", "fixture.json"))):
        name = os.path.basename(os.path.dirname(f))
        if cases and name not in cases:
            continue
        fx = json.load(open(f, encoding="utf-8"))
        add(fx["pin"], "%s pin" % name)
        if fx.get("refinement_commit"):
            add(fx["refinement_commit"], "%s refinement_commit" % name)
    return out


def missing(path, cases=None):
    """Needed commits absent from the clone at `path`, as 'sha (why)'."""
    if not os.path.isdir(os.path.join(path, ".git")):
        return ["no git clone at %s" % path]
    return ["%s (%s)" % (sha, why) for sha, why in needed(cases).items()
            if subprocess.run(["git", "-C", path, "rev-parse", "--verify", "-q",
                               sha + "^{commit}"], capture_output=True).returncode != 0]


def require(cases=None):
    """The clone's path, or exit naming what is missing and the remedy."""
    path = admc_path()
    gaps = missing(path, cases)
    if gaps:
        sys.exit("ADMC clone at %s is missing:\n  %s\nrun: python3 evals/judgment/sources.py"
                 "   (or point %s at a clone that has them)" % (path, "\n  ".join(gaps), ENV))
    return path


def main():
    path = admc_path()
    if os.path.isdir(os.path.join(path, ".git")):
        print("fetch %s" % path)
        step = ["git", "-C", path, "fetch", "--quiet", "origin"]
    else:
        print("clone %s → %s" % (remote(), path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        step = ["git", "clone", "--quiet", remote(), path]
    if subprocess.run(step).returncode != 0:
        sys.exit("sources: %s failed — do you have access to %s?" % (" ".join(step[:4]), remote()))
    gaps = missing(path)
    if gaps:
        sys.exit("still missing after fetch:\n  " + "\n  ".join(gaps))
    print("ok: %d needed commits present in %s" % (len(needed()), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
