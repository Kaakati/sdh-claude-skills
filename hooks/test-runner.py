#!/usr/bin/env python3
"""
PostToolUse hook: Test reminder after code edits.
Reads JSON from stdin, checks if the edited file has corresponding test files.

The candidates follow each stack's own layout: colocated JS/TS tests; for Rails and Python, the
list in `_testpaths.py` that test-coverage-checker reads too, so this reminder speaks exactly when
that checker stays quiet. Rails: the `spec/` (RSpec) and `test/` (Minitest) mirrors of `app/`.
Python: pytest's `tests/` mirror of the package (the `std-python` skill:
`src/<package>/services/billing.py` -> `tests/services/test_billing.py`, FastAPI's `app/` the same
way), a Django app's own `tests/` package, and a co-located `test_<name>.py` / `<name>_test.py`.
"""
import os

import _hooklib as hooklib
import _testpaths as testpaths


# Skip files matching these patterns (test files, configs, docs)
SKIP_PATTERNS = (
    ".test.", ".spec.", "__tests__",
    ".config.", ".md", ".json", ".yml", ".yaml",
)


def _js_candidates(directory, basename, ext):
    return [
        os.path.join(directory, f"{basename}.test.{ext}"),
        os.path.join(directory, f"{basename}.spec.{ext}"),
        os.path.join(directory, "__tests__", f"{basename}.test.{ext}"),
        os.path.join(directory, "..", "__tests__", f"{basename}.test.{ext}"),
        os.path.join(f"{directory}_test", f"{basename}_test.{ext}"),
        os.path.join(directory, f"test_{basename}.{ext}"),
    ]


def _candidates(file_path):
    basename, ext = os.path.splitext(os.path.basename(file_path))
    if ext == ".rb":
        return testpaths.rails_candidates(file_path)
    if ext == ".py":
        return testpaths.python_candidates(file_path)
    return _js_candidates(os.path.dirname(file_path), basename, ext.lstrip("."))


def check(event):
    file_path = hooklib.get_file_path(event)

    # Skip test files, configs, and docs
    if not file_path or any(pattern in file_path for pattern in SKIP_PATTERNS):
        return []

    found = list(dict.fromkeys(
        hooklib.normalize(os.path.normpath(p)) for p in _candidates(file_path) if os.path.isfile(p)))
    if not found:
        return []

    # Once per session, not once per edit.
    #
    # This fires whenever an edited source file HAS tests; `test-coverage-checker` fires when
    # it does NOT. Between them every source edit produced a message — a 100% injection rate,
    # which mattered little while these went to a debug log and matters enormously now they
    # reach the model. Of the two, only "no test file found" is actionable: "consider running
    # tests" tells the reader something they can already see, on every single edit, which is
    # how a whole advisory layer earns its way into being ignored (Ch. 5).
    if hooklib.seen_this_session(event, "test-runner-reminder"):
        return []
    return [
        f"Related test files found: {' '.join(found)}. Consider running tests to verify "
        f"changes. (This reminder appears once per session.)"
    ]


if __name__ == "__main__":
    hooklib.run_post_checker(check)
