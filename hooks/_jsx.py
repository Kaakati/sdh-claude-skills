#!/usr/bin/env python3
"""JSX-aware scanning shared by the frontend PostToolUse checkers.

`accessibility-checker`, `design-token-checker` and `i18n-checker` read an opening tag to its real
end: a `>` inside `{...}`, a quoted string or a template literal does not close it (the old `[^>]*`
scan stopped at the `>` of `onLoad={() => ...}`). `code-quality-checker` and `i18n-checker` skip
comments and strings the same way. One copy, so a fix to the scanner reaches every checker; the
trigger-precision matrix in hooks/tests/run-all.py is the safety net for all four.
"""
import re

TAG_TOKEN = re.compile(r"[\"'`{}>]")
TAG_SCAN_LIMIT = 4000


def scan_until(src, start, closer):
    """Offset of `closer` outside quotes and nested braces, from `start`; -1 when not nearby."""
    depth, pos, stop = 0, start, min(len(src), start + TAG_SCAN_LIMIT)
    while True:
        match = TAG_TOKEN.search(src, pos, stop)
        if not match:
            return -1
        ch, pos = match.group(), match.end()
        if ch in "\"'`":
            close = src.find(ch, pos, stop)
            pos = close + 1 if close != -1 else pos
        elif ch == closer and depth <= 0:
            return match.start()
        elif ch in "{}":
            depth += 1 if ch == "{" else -1


def skip_token(src, i):
    """Offset past the comment or string starting at `i`; `i + 1` for a quote with no partner on its
    line, which is an apostrophe in JSX text ("Don't"), not a string."""
    if src.startswith("//", i):
        end = src.find("\n", i)
        return len(src) if end == -1 else end
    if src.startswith("/*", i):
        end = src.find("*/", i + 2)
        return len(src) if end == -1 else end + 2
    quote, j = src[i], i + 1
    stops = "`" if quote == "`" else quote + "\n"
    while j < len(src) and src[j] not in stops:
        j += 2 if src[j] == "\\" else 1
    return j + 1 if j < len(src) and src[j] == quote else i + 1
