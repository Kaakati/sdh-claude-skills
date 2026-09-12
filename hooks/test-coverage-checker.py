#!/usr/bin/env python3
"""
PostToolUse hook: Test coverage checker.

Checks if source files under Rails app/, JS/TS src/, or a Python src/ or app/ package (under any
wrapper directory) have corresponding test files per the `std-testing` skill conventions.
Exits silently for non-source files, test files, and files outside source dirs.

Rails and Python candidates come from `_testpaths.py`, the same list test-runner reads, so the
runner's "Related test files found" and this checker's "No test file found" can never both speak
about one file. Rails counts the RSpec `spec/` and the Minitest `test/` mirror of `app/`. Python
follows pytest and the `std-python` layout: `src/<pkg>/services/billing.py` is covered by
`tests/services/test_billing.py` (or `tests/unit/...`, `tests/<pkg>/...`, a flat
`tests/test_billing.py`, a co-located `test_billing.py` / `billing_test.py`), rooted at the nearest
pyproject.toml, manage.py, setup.py or setup.cfg.

The warning is shown once per file per session: repeated on every edit of the same untested file,
it was wallpaper, and "consider adding tests" says nothing new the fifth time.

Vendored shadcn/ui primitives (the components.json `aliases.ui` directory) ship without tests and
are CLI-owned, so they are skipped; the gates and compositions built on them are what get tested.
"""
import hashlib
import os

import _hooklib as hooklib
import _testpaths as testpaths
import _vendored as vendored


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")
JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
SKIP_PATTERNS = (".test.", ".spec.", "__tests__", "_test.", "_spec.")
PY_SKIP_FILES = ("__init__.py", "conftest.py")
PY_SKIP_DIRS = ("tests", "test", "migrations", "alembic")


def js_candidates(file_path, normalized, basename, ext):
    directory = os.path.dirname(file_path)
    # <wrapper>/src/components/Foo.tsx → <wrapper>/tests/components/Foo.test.tsx
    src_test = hooklib.replace_first_segment(normalized, "src", "tests")
    return [
        os.path.join(directory, f"{basename}.test{ext}"),
        os.path.join(directory, f"{basename}.spec{ext}"),
        os.path.join(directory, "__tests__", f"{basename}.test{ext}"),
        os.path.join(directory, "..", "__tests__", f"{basename}.test{ext}"),
        src_test.replace(f"{basename}{ext}", f"{basename}.test{ext}"),
    ]


def python_in_scope(file_path):
    """A module inside a src/ or app/ package that is not itself test, init or migration code."""
    base, parts = testpaths.python_layout(file_path)
    if base is None or parts[-1] in PY_SKIP_FILES or parts[-1].startswith("test_"):
        return False
    return not any(p in PY_SKIP_DIRS for p in parts[:-1])


def source_candidates(file_path, normalized, ext):
    """Test files that would cover this source file, or None when it is out of scope."""
    basename = os.path.splitext(os.path.basename(file_path))[0]
    if ext == ".rb":
        return testpaths.rails_candidates(file_path) if hooklib.under(normalized, "app") else None
    if ext == ".py":
        return testpaths.python_candidates(file_path) if python_in_scope(file_path) else None
    if not hooklib.under(normalized, "src") or vendored.is_vendored_ui(file_path):
        return None
    return js_candidates(file_path, normalized, basename, ext)


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    normalized = hooklib.normalize(file_path)
    # Skip non-source files and test files themselves
    if ext not in SOURCE_EXTENSIONS or any(p in normalized for p in SKIP_PATTERNS):
        return []

    candidates = source_candidates(file_path, normalized, ext)
    if candidates is None or any(os.path.isfile(c) for c in candidates):
        return []
    digest = hashlib.sha1(os.path.normcase(os.path.abspath(file_path)).encode("utf-8")).hexdigest()[:16]
    if hooklib.seen_this_session(event, f"test-coverage-{digest}"):
        return []

    return [
        f"WARNING: No test file found for {os.path.basename(file_path)}. "
        "Consider adding tests per the `std-testing` skill (80% coverage target for business logic). "
        "(Shown once per file per session.)"
    ]


if __name__ == "__main__":
    hooklib.run_post_checker(check)
