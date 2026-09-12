#!/usr/bin/env python3
"""PostToolUse hook: Monitoring standards checker.

Checks .rb files under app/controllers/ and app/jobs/ (any wrapper) for sensitive
data in log statements — and .py files where request and job data meets logging: the house
FastAPI layout (app/routers/, app/api/), a services or tasks package, and a Django app's
views.py / viewsets.py / services.py / tasks.py — in f-strings, log keyword arguments, and
%-style positional arguments.

It does NOT check for request_id on each log line: that id is attached by Rails via
`config.log_tags`, so it is not present in the source, and the remedy for its absence
is config rather than an edit at the call site. See the `std-monitoring` skill.
Returns no warnings for non-matching files."""

import os
import re

import _hooklib as hooklib

ALLOWED_DIRS = ("app/controllers", "app/jobs")
# The Python face of the same rule: FastAPI's boundary dirs (std-fastapi), service and Celery task
# packages (the std-python src layout puts them under src/<package>/, not app/), and Django's
# per-app modules (std-django: `models.py serializers.py views.py services.py tasks.py`).
PY_ALLOWED_DIRS = ("app/routers", "app/api", "services", "tasks", "views")
PY_ALLOWED_FILES = ("views.py", "viewsets.py", "services.py", "tasks.py")
SENSITIVE_WORDS = ("password", "token", "secret", "ssn", "credit_card")

PY_LOG_CALL = re.compile(r"\b(?:logger|logging|log)\.\w+")  # \b: `catalog.update` is not `log.`
RB_LOG_CALL = re.compile(r"(?:Rails\.logger|logger)\.\w+")
MAX_CALL_CHARS = 1000

# "token" is the one sensitive word with a dominant innocent meaning on this stack: LLM usage
# (`{usage.output_tokens}`, `{token_count}`) and tokenizers, logged by every AI service. The kwarg
# and positional forms already let a suffix break the match (`token_count=` escapes); interpolation
# matched the word ANYWHERE inside the braces, so logging token usage read as leaking a secret.
TOKEN_IS_A_COUNT = r"(?!s\b|s_|_count|_usage|_limit|_budget|_type|iz)"

WARNING = ("WARNING: Potentially sensitive data in log statement "
           "per the `std-monitoring` skill. Never log passwords, tokens, PII, or secrets.")


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


def _py_leak(word):
    """Three ways a secret reaches a Python log call. `\\w*` prefixes let compound names
    (`access_token=`) match while `token_count=` still escapes — the suffix breaks the
    `=`/word-boundary adjacency."""
    tail = TOKEN_IS_A_COUNT if word == "token" else ""
    return (r"\{[^}]*" + word + tail            # f-string {access_token}
            + r"|\w*" + word + r"\s*="           # kwarg access_token=...
            + r"|,\s*\w*" + word + r"\b")        # positional ..., password)


def _rb_leak(word):
    """Ruby: `#{...}` interpolation, or a hash key — the structured (lograge) form the
    `std-monitoring` skill prescribes: `logger.info(event: "x", password: p)`, `:password =>`.
    The key must follow `(`, `,` or `{`, so `"token: #{id}"` inside a string is not a key."""
    tail = TOKEN_IS_A_COUNT if word == "token" else ""
    return (r"[#$]\{[^}]*" + word + tail
            + r"|[(,{]\s*\w*" + word + r":\s"
            + r"|[(,{]\s*[:\"']\w*" + word + r"[\"']?\s*=>")


def _call_text(content, name_end):
    """The log call's arguments: through the balanced `)` when the call has parentheses, so a
    call a formatter wrapped across lines (`ruff format` does, at 88 columns) is read whole;
    otherwise the rest of the line (paren-less Ruby, block form)."""
    rest = content[name_end:name_end + MAX_CALL_CHARS]
    stripped = rest.lstrip(" \t")
    if not stripped.startswith("("):
        return rest.split("\n", 1)[0]
    depth = 0
    for i, ch in enumerate(stripped):
        depth += 1 if ch == "(" else -1 if ch == ")" else 0
        if depth == 0:
            return stripped[:i + 1]
    return stripped


def check_sensitive_data_in_logs(content, ext=".rb"):
    """Check for sensitive data words in log interpolation, keyword/hash keys, and arguments.

    Plain string concatenation (`"pw " + password`) is the one idiom not matched."""
    call, leak_of = (PY_LOG_CALL, _py_leak) if ext == ".py" else (RB_LOG_CALL, _rb_leak)
    for m in call.finditer(content):
        text = _call_text(content, m.end()).lower()
        if any(word in text and re.search(leak_of(word), text) for word in SENSITIVE_WORDS):
            return [WARNING]  # One warning is enough
    return []


def _in_scope(file_path, ext):
    if ext == ".rb":
        return hooklib.under_any(file_path, ALLOWED_DIRS)
    if ext == ".py":
        return (hooklib.under_any(file_path, PY_ALLOWED_DIRS)
                or os.path.basename(file_path) in PY_ALLOWED_FILES)
    return False


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if not _in_scope(file_path, ext):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    return check_sensitive_data_in_logs(content, ext)


if __name__ == "__main__":
    hooklib.run_post_checker(check)
