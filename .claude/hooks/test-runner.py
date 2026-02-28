#!/usr/bin/env python3
"""
PostToolUse hook: Test reminder after code edits.
Reads JSON from stdin, checks if the edited file has corresponding test files.
"""
import json
import os
import sys


# Skip files matching these patterns (test files, configs, docs)
SKIP_PATTERNS = (
    ".test.", ".spec.", "__tests__",
    ".config.", ".md", ".json", ".yml", ".yaml",
)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")

    if not file_path:
        sys.exit(0)

    # Skip test files, configs, and docs
    if any(pattern in file_path for pattern in SKIP_PATTERNS):
        sys.exit(0)

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
        display = [p.replace("\\", "/") for p in found]
        print(f"Related test files found: {' '.join(display)}. Consider running tests to verify changes.")

    sys.exit(0)


if __name__ == "__main__":
    main()
