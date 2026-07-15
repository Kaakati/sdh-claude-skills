#!/usr/bin/env python3
"""PostToolUse hook: Monitoring standards checker.

Checks .rb files under app/controllers/ and app/jobs/ (any wrapper) for sensitive
data interpolated into log statements.

It does NOT check for request_id on each log line: that id is attached by Rails via
`config.log_tags`, so it is not present in the source, and the remedy for its absence
is config rather than an edit at the call site. See the `std-monitoring` skill.
Returns no warnings for non-matching files."""

import os
import re

import _hooklib as hooklib

ALLOWED_DIRS = ("app/controllers", "app/jobs")
SENSITIVE_WORDS = ("password", "token", "secret", "ssn", "credit_card")


# REMOVED: check_log_without_request_id.
#
# It warned when a log line did not literally contain "request_id". Two independent reasons that
# check could never be right, and it was also broken:
#
# 1. IT ASKED SOURCE TO CONTAIN WHAT THE FRAMEWORK INJECTS. This repo's own prescription
#    (`std-monitoring/references/request-tracing.md`) is `config.log_tags = [:request_id]` plus
#    Sidekiq client/server middleware — the id is attached by Rails at runtime and is NOT in the
#    source line. So on a CORRECTLY configured app every plain `Rails.logger.info("...")` was a
#    false positive, and on a misconfigured one no amount of per-line editing fixes it: the
#    remedy is config, not the call site. Ch. 7's placement test settles it — a rule that must
#    hold whether or not anyone reads it, and is satisfied by one line of config, is not a
#    per-call warning.
# 2. IT WAS DEAD ANYWAY. The pattern `(?:Rails\.logger|logger)\.\w+\s` required WHITESPACE after
#    the method name, so it only ever matched paren-less Ruby (`Rails.logger.info "x"`). Every
#    parenthesized call — the dominant idiom, and the exact form request-tracing.md itself
#    writes — was invisible. The sibling check below uses the same alternation without the `\s`
#    and works, which is what proves the `\s` was an anomaly rather than a decision.
#
# The mechanism lives in the skill; the sensitive-data check below stays, because THAT is
# genuinely a property of the call site.


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
                    "per the `std-monitoring` skill. Never log passwords, tokens, PII, or secrets."
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
    warnings.extend(check_sensitive_data_in_logs(content))
    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
