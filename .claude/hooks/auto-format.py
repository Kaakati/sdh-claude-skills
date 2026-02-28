#!/usr/bin/env python3
"""
PostToolUse hook: Auto-format files after edits.
Reads JSON from stdin, extracts file_path, runs the appropriate formatter.

Formatters are silently skipped if not installed (same behavior as the
former bash version). Requires no external dependencies beyond Python 3.
"""
import json
import os
import shutil
import subprocess
import sys


FORMATTER_MAP = {
    "rb":    ("rubocop", ["rubocop", "--autocorrect-all", "--fail-level=error"]),
    "rake":  ("rubocop", ["rubocop", "--autocorrect-all", "--fail-level=error"]),
    "js":    ("prettier", ["prettier", "--write"]),
    "jsx":   ("prettier", ["prettier", "--write"]),
    "ts":    ("prettier", ["prettier", "--write"]),
    "tsx":   ("prettier", ["prettier", "--write"]),
    "css":   ("prettier", ["prettier", "--write"]),
    "scss":  ("prettier", ["prettier", "--write"]),
    "json":  ("prettier", ["prettier", "--write"]),
    "yaml":  ("prettier", ["prettier", "--write"]),
    "yml":   ("prettier", ["prettier", "--write"]),
    "erb":   ("htmlbeautifier", ["htmlbeautifier"]),
    "py":    ("black", ["black", "--quiet"]),
    "tf":    ("terraform", ["terraform", "fmt"]),
    "tfvars": ("terraform", ["terraform", "fmt"]),
}


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")

    if not file_path or not os.path.isfile(file_path):
        sys.exit(0)

    _, ext = os.path.splitext(file_path)
    ext = ext.lstrip(".")

    if ext not in FORMATTER_MAP:
        sys.exit(0)

    binary_name, cmd_parts = FORMATTER_MAP[ext]

    if not shutil.which(binary_name):
        sys.exit(0)

    try:
        subprocess.run(
            cmd_parts + [file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
