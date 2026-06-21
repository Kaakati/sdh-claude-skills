#!/usr/bin/env python3
"""
PostToolUse hook: Test reminder after code edits.
Reads JSON from stdin, checks if the edited file has corresponding test files.
"""
import os

import _hooklib as hooklib


# Skip files matching these patterns (test files, configs, docs)
SKIP_PATTERNS = (
    ".test.", ".spec.", "__tests__",
    ".config.", ".md", ".json", ".yml", ".yaml",
)


def check(event):
    file_path = hooklib.get_file_path(event)

    if not file_path:
        return []

    # Skip test files, configs, and docs
    if any(pattern in file_path for pattern in SKIP_PATTERNS):
        return []

    _, ext = os.path.splitext(file_path)
    ext = ext.lstrip(".")
    basename = os.path.splitext(os.path.basename(file_path))[0]
    directory = os.path.dirname(file_path)

    # Check for common test file patterns
    candidates = [
        os.path.join(directory, f"{basename}.test.{ext}"),
        os.path.join(directory, f"{basename}.spec.{ext}"),
        os.path.join(directory, "__tests__", f"{basename}.test.{ext}"),
        os.path.join(directory, "..", "__tests__", f"{basename}.test.{ext}"),
        os.path.join(f"{directory}_test", f"{basename}_test.{ext}"),
        os.path.join(directory, f"test_{basename}.{ext}"),
    ]

    found = [p for p in candidates if os.path.isfile(p)]

    if found:
        # Normalize paths for display (backslash → forward slash)
        display = [hooklib.normalize(p) for p in found]
        return [f"Related test files found: {' '.join(display)}. Consider running tests to verify changes."]

    return []


if __name__ == "__main__":
    hooklib.run_post_checker(check)
