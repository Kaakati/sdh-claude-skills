#!/usr/bin/env python3
"""
PostToolUse hook: Error handling checker.

Checks source files for empty catch/rescue/except blocks and
rescue Exception (should be StandardError) per error-handling.md.
Exits silently for non-source files.
"""
import json
import os
import re
import sys


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def check_empty_handlers(content, ext):
    warnings = []
    if ext == ".rb":
        # rescue ... followed by end with nothing meaningful between
        pattern = re.compile(
            r"rescue\b[^\n]*\n(\s*#[^\n]*\n)*\s*end\b", re.MULTILINE
        )
        if pattern.search(content):
            warnings.append(
                "WARNING: Empty error handler found per error-handling.md."
            )
    elif ext == ".py":
        # except ... : followed by pass or just a comment
        pattern = re.compile(
            r"except\b[^\n]*:\s*\n(\s*#[^\n]*\n)*\s*pass\b", re.MULTILINE
        )
        if pattern.search(content):
            warnings.append(
                "WARNING: Empty error handler found per error-handling.md."
            )
    else:
        # JS/TS: catch(...) { } with nothing meaningful inside
        pattern = re.compile(
            r"catch\s*\([^)]*\)\s*\{\s*(//[^\n]*)?\s*\}", re.MULTILINE
        )
        if pattern.search(content):
            warnings.append(
                "WARNING: Empty error handler found per error-handling.md."
            )
    return warnings


def check_rescue_exception(content, ext):
    if ext != ".rb":
        return []
    pattern = re.compile(r"rescue\s+Exception\b")
    if pattern.search(content):
        return [
            "WARNING: Rescue StandardError, not Exception per error-handling.md."
        ]
    return []


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

    content = read_file(file_path)
    if not content:
        sys.exit(0)

    warnings = []
    warnings.extend(check_empty_handlers(content, ext))
    warnings.extend(check_rescue_exception(content, ext))

    for w in warnings:
        print(w)

    sys.exit(0)


if __name__ == "__main__":
    main()
