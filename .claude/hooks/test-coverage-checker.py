#!/usr/bin/env python3
"""
PostToolUse hook: Test coverage checker.

Checks if source files under app/, src/, web/src/, or next/src/ have
corresponding test files per testing.md conventions.
Exits silently for non-source files, test files, and files outside source dirs.
"""
import json
import os
import sys


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")
SKIP_PATTERNS = (".test.", ".spec.", "__tests__", "_test.", "_spec.")
SOURCE_PREFIXES = ("app/", "src/", "web/src/", "next/src/")


def normalize(path):
    return path.replace("\\", "/")


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        sys.exit(0)

    normalized = normalize(file_path)

    # Skip test files themselves
    if any(p in normalized for p in SKIP_PATTERNS):
        sys.exit(0)

    # Only check files under source directories
    if not any(p in normalized for p in SOURCE_PREFIXES):
        sys.exit(0)

    basename = os.path.splitext(os.path.basename(file_path))[0]
    directory = os.path.dirname(file_path)

    # Build candidate test file paths based on convention
    candidates = []

    if ext == ".rb":
        # Rails: app/services/foo.rb → spec/services/foo_spec.rb
        if "app/" in normalized:
            spec_path = normalized.replace("app/", "spec/", 1)
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
        # Vite: web/src/components/Foo.tsx → web/tests/components/Foo.test.tsx
        if "web/src/" in normalized:
            web_test = normalized.replace("web/src/", "web/tests/", 1)
            web_test = web_test.replace(f"{basename}{ext}", f"{basename}.test{ext}")
            candidates.append(web_test)
        # Next.js: next/src/actions/foo.ts → next/tests/actions/foo.test.ts
        if "next/src/" in normalized:
            next_test = normalized.replace("next/src/", "next/tests/", 1)
            next_test = next_test.replace(f"{basename}{ext}", f"{basename}.test{ext}")
            candidates.append(next_test)

    # Check if any candidate exists
    found = any(os.path.isfile(c) for c in candidates)

    if not found:
        filename = os.path.basename(file_path)
        print(
            f"WARNING: No test file found for {filename}. "
            "Consider adding tests per testing.md (80% coverage target for business logic)."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
