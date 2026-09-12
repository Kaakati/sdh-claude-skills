#!/usr/bin/env python3
"""Where the tests for a Rails or Python source file live.

`test-coverage-checker` warns when none of these exist; `test-runner` names the ones that do. Both
ask this module, with the same root markers and the same mirrors, so the runner says "found"
exactly when the coverage checker stays quiet about the file. Before, the checker rooted Python at
pyproject.toml alone while the runner also took manage.py, setup.py and setup.cfg, each kept its own
candidate list, and the checker never looked at a Minitest `test/` mirror.
"""
import os

import _hooklib as hooklib

PYTHON_ROOT_MARKERS = ("pyproject.toml", "manage.py", "setup.py", "setup.cfg")
PY_PACKAGE_DIRS = ("src", "app")


def rails_candidates(file_path):
    """`<wrapper>/app/models/user.rb` -> `spec/models/user_spec.rb` (RSpec) and
    `test/models/user_test.rb` (Minitest); [] for a Ruby file outside `app/`."""
    norm = hooklib.normalize(file_path)
    if not norm.endswith(".rb") or not hooklib.under(norm, "app"):
        return []
    spec = hooklib.replace_first_segment(norm, "app", "spec")
    minitest = hooklib.replace_first_segment(norm, "app", "test")
    return [spec[: -len(".rb")] + "_spec.rb", minitest[: -len(".rb")] + "_test.rb"]


def python_root(file_path):
    """Nearest ancestor holding a Python project marker, stopping at the repository root; else None."""
    current = os.path.dirname(os.path.abspath(file_path))
    while True:
        if any(os.path.isfile(os.path.join(current, marker)) for marker in PYTHON_ROOT_MARKERS):
            return current
        parent = os.path.dirname(current)
        if parent == current or os.path.exists(os.path.join(current, ".git")):
            return None
        current = parent


def python_layout(file_path):
    """(base dir, parts from the src/ or app/ anchor) for a Python module, or (None, None).

    Anchored below the nearest project marker, so an ANCESTOR directory named `app` or `src`
    (a /app container WORKDIR, a ~/src checkout) is never mistaken for the package. Without a
    marker the last `src` segment anchors."""
    parts = hooklib.normalize(os.path.abspath(file_path)).split("/")
    root = python_root(file_path)
    first = len(hooklib.normalize(root).rstrip("/").split("/")) if root else 0
    anchors = PY_PACKAGE_DIRS if root else ("src",)
    hits = [i for i in range(first, len(parts) - 1) if parts[i] in anchors]
    if not hits:
        return None, None
    i = hits[0] if root else hits[-1]
    return "/".join(parts[:i]), parts[i:]


def _mirror(file_path, here):
    """(base, package-relative dirs, the dirs tests/ mirrors), or (None, None, None) with neither a
    src/ or app/ anchor nor a project marker. tests/ does not repeat `src/<package>` or `app`."""
    base, parts = python_layout(file_path)
    if base is not None:
        inner = parts[1:-1]  # src/<pkg>/services -> [<pkg>, services]
        return base, inner, (inner[1:] if parts[0] == "src" else inner)
    root = python_root(file_path)
    if root is None:
        return None, None, None
    inner = [p for p in hooklib.normalize(os.path.relpath(here, root)).split("/") if p not in ("", ".")]
    return root, inner, inner


def python_candidates(file_path):
    """pytest locations covering a Python module: a co-located test_<name>.py or <name>_test.py, a
    Django app's own tests/ package, and the project's tests/ mirror (plus tests/unit/, the
    package-relative path, and a flat tests/test_<name>.py)."""
    here = os.path.dirname(os.path.abspath(file_path))
    name = os.path.splitext(os.path.basename(file_path))[0]
    test = f"test_{name}.py"
    found = [os.path.join(here, test), os.path.join(here, f"{name}_test.py"),
             os.path.join(here, "tests", test)]
    base, inner, mirror = _mirror(file_path, here)
    if base is not None:
        found += [os.path.join(base, "tests", *mirror, test),
                  os.path.join(base, "tests", "unit", *mirror, test),
                  os.path.join(base, "tests", *inner, test),
                  os.path.join(base, "tests", test)]
    return found
