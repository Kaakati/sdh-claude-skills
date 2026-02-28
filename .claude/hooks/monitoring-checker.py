#!/usr/bin/env python3
"""
PostToolUse hook: Monitoring standards checker.

Checks .rb files under backend/app/controllers/ and backend/app/jobs/ for:
- Log statements missing request_id
- Sensitive data in log statements
Per monitoring.md. Exits silently for non-matching files.
"""
import json
import os
import re
import sys


ALLOWED_PREFIXES = ("backend/app/controllers/", "backend/app/jobs/")
SENSITIVE_WORDS = ("password", "token", "secret", "ssn", "credit_card")


def normalize(path):
    return path.replace("\\", "/")


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def check_log_without_request_id(content):
    """Check for log statements without request_id."""
    log_pattern = re.compile(
        r"(?:Rails\.logger|logger)\.\w+\s", re.MULTILINE
    )
    warnings = []
    for m in log_pattern.finditer(content):
        # Get the full line
        line_start = content.rfind("\n", 0, m.start()) + 1
        line_end = content.find("\n", m.end())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]
        if "request_id" not in line:
            warnings.append(
                "WARNING: Log statement without request_id. "
                "Include request_id for distributed tracing per monitoring.md."
            )
            return warnings  # One warning is enough
    return warnings


def check_sensitive_data_in_logs(content):
    """Check for sensitive data words in log interpolation."""
    log_pattern = re.compile(
        r"(?:Rails\.logger|logger)\.\w+.*?$", re.MULTILINE
    )
    warnings = []
    for m in log_pattern.finditer(content):
        line = m.group(0).lower()
        # Check for interpolated sensitive words: #{password}, ${token}, etc.
        for word in SENSITIVE_WORDS:
            if word in line and re.search(r"[#$]\{[^}]*" + word, line):
                warnings.append(
                    "WARNING: Potentially sensitive data in log statement "
                    "per monitoring.md. Never log passwords, tokens, PII, or secrets."
                )
                return warnings  # One warning is enough
    return warnings


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    _, ext = os.path.splitext(file_path)
    if ext != ".rb":
        sys.exit(0)

    normalized = normalize(file_path)
    if not any(p in normalized for p in ALLOWED_PREFIXES):
        sys.exit(0)

    content = read_file(file_path)
    if not content:
        sys.exit(0)

    warnings = []
    warnings.extend(check_log_without_request_id(content))
    warnings.extend(check_sensitive_data_in_logs(content))

    for w in warnings:
        print(w)

    sys.exit(0)


if __name__ == "__main__":
    main()
