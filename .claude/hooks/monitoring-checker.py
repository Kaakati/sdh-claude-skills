#!/usr/bin/env python3
"""PostToolUse hook: Monitoring standards checker.

Checks .rb files under backend/app/controllers/ and backend/app/jobs/ for:
- Log statements missing request_id
- Sensitive data in log statements
Per monitoring.md. Returns no warnings for non-matching files."""

import os
import re

import _hooklib as hooklib

ALLOWED_DIRS = ("app/controllers", "app/jobs")
SENSITIVE_WORDS = ("password", "token", "secret", "ssn", "credit_card")


def check_log_without_request_id(content):
    """Check for log statements without request_id."""
    log_pattern = re.compile(r"(?:Rails\.logger|logger)\.\w+\s", re.MULTILINE)
    warnings = []
    for m in log_pattern.finditer(content):
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
    log_pattern = re.compile(r"(?:Rails\.logger|logger)\.\w+.*?$", re.MULTILINE)
    warnings = []
    for m in log_pattern.finditer(content):
        line = m.group(0).lower()
        for word in SENSITIVE_WORDS:
            if word in line and re.search(r"[#$]\{[^}]*" + word, line):
                warnings.append(
                    "WARNING: Potentially sensitive data in log statement "
                    "per monitoring.md. Never log passwords, tokens, PII, or secrets."
                )
                return warnings  # One warning is enough
    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext != ".rb":
        return []

    if not hooklib.under_any(file_path, ALLOWED_DIRS):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []
    warnings.extend(check_log_without_request_id(content))
    warnings.extend(check_sensitive_data_in_logs(content))
    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
