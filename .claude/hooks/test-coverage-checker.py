#!/usr/bin/env python3
"""
PostToolUse hook: Test coverage checker.

Checks if source files under Rails app/ or JS/TS src/ (under any wrapper directory) have
corresponding test files per testing.md conventions.
Exits silently for non-source files, test files, and files outside source dirs.
"""
import os

import _hooklib as hooklib


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")
SKIP_PATTERNS = (".test.", ".spec.", "__tests__", "_test.", "_spec.")


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        return []

    normalized = hooklib.normalize(file_path)

    # Skip test files themselves
    if any(p in normalized for p in SKIP_PATTERNS):
        return []

    # Only check files under source directories (wrapper-agnostic)
    is_rails_source = ext == ".rb" and hooklib.under(normalized, "app")
    is_js_source = hooklib.under(normalized, "src")
    if not (is_rails_source or is_js_source):
        return []

    basename = os.path.splitext(os.path.basename(file_path))[0]
    directory = os.path.dirname(file_path)

    # Build candidate test file paths based on convention
    candidates = []

    if ext == ".rb":
        # Rails: <wrapper>/app/services/foo.rb → <wrapper>/spec/services/foo_spec.rb
        if is_rails_source:
            spec_path = hooklib.replace_first_segment(normalized, "app", "spec")
            spec_path = spec_path.replace(f"{basename}.rb", f"{basename}_spec.rb")
            candidates.append(spec_path)
    else:
        # JS/TS test conventions
        candidates.extend([
            os.path.join(directory, f"{basename}.test{ext}"),
            os.path.join(directory, f"{basename}.spec{ext}"),
            os.path.join(directory, "__tests__", f"{basename}.test{ext}"),
            os.path.join(directory, "..", "__tests__", f"{basename}.test{ext}"),
        ])
        # JS/TS: <wrapper>/src/components/Foo.tsx → <wrapper>/tests/components/Foo.test.tsx
        if is_js_source:
            src_test = hooklib.replace_first_segment(normalized, "src", "tests")
            src_test = src_test.replace(f"{basename}{ext}", f"{basename}.test{ext}")
            candidates.append(src_test)

    # Check if any candidate exists
    found = any(os.path.isfile(c) for c in candidates)

    warnings = []
    if not found:
        filename = os.path.basename(file_path)
        warnings.append(
            f"WARNING: No test file found for {filename}. "
            "Consider adding tests per testing.md (80% coverage target for business logic)."
        )

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
