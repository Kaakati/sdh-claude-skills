#!/usr/bin/env python3
"""PostToolUse advisory checker (dispatched): is the edited file orthogonal to the rest of the project?

`post-edit-dispatch.py` runs `check(event)` in-process, last in its CHECKERS list. The logic lives
once, in the shared `_arch*` modules that the `orthogonality` skill's scans import as well; this file
is the dispatcher's entry point to `_archhooks.checker_lines`, which:

  * opens the project's architecture index READ-ONLY and parses only the edited file. It never
    writes the index: `orthogonality-index.py` (SessionStart) and `orthogonality-watch.py`
    (asyncRewake) own writes, so this synchronous path never waits on a write lock;
  * runs the edit-time detectors (DK1-DK4, CM1-CM4, BC1-BC3, MF3, MF5) against the index, or only
    the file-local DK4, MF3, MF5 and CM1 when no index exists yet, inside a 1.5 s budget;
  * returns at most three `ORTHOGONALITY [<ID> <slug>]` lines: severity warn, confidence high or
    medium, new since the baseline, not suppressed, not already shown this session. Once-per-session
    notes cover an index not built yet, an invalid `.claude/orthogonality.json`, a budget stop and a
    failed background refresh.

Every line states the evidence (both locations, the measured signal) and names the owner skill for
the fix, such as the `std-database`, `std-api-design` or `std-code-standards` skill, plus the
`orthogonality` skill for policy, declarations and inline `sdh:orthogonal-ok <ID> <reason>` markers.
Nothing here asks or denies.

Never checked here:
  * DK6 cross-file clones, Terraform (TF1-TF2) and the other whole-codebase detectors: on-demand
    scans and CI only;
  * what other hooks own: layer violations (`clean-architecture-checker.py`), unindexed foreign keys
    and HABTM (`database-design-checker.py`), migration safety (`migration-validator.py`),
    envelope keys (`api-design-checker.py`).
Quiet: `SDH_ORTHOGONALITY=off`, vendored shadcn/ui primitives, config `ignore` globs, and any file
outside SOURCE_EXTENSIONS that is not a dependency manifest.
"""
import _hooklib as hooklib
import _archhooks

# The literal the harness reads for this hook's scope. It equals `_archhooks.SOURCE_EXTENSIONS`;
# manifests (Gemfile, package.json, pyproject.toml, requirements*.txt) are matched by name there.
SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".sql")


def check(event):
    """Orthogonality warning lines for the edited file; [] when it is out of scope."""
    return _archhooks.checker_lines(event)


if __name__ == "__main__":
    hooklib.run_post_checker(check)
