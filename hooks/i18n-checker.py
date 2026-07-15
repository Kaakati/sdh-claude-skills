#!/usr/bin/env python3
"""
PostToolUse hook: Internationalization (i18n) checker.

Checks .tsx, .jsx, and .erb files for hardcoded user-facing strings
that should use translation keys per the `std-i18n` skill.
Exits silently for non-matching files.
"""
import os
import re

import _hooklib as hooklib


ALLOWED_EXTENSIONS = (".tsx", ".jsx", ".erb")
SOURCE_DIRS = ("app/views", "src", "app")
SKIP_PATTERNS = (".test.", ".spec.", "__tests__", ".config.", ".d.ts")


def check_jsx_hardcoded_strings(content):
    """Find plain text in JSX that isn't wrapped in t() or useTranslation."""
    # Match text content between JSX tags: >some text<
    # Ignore single chars, numbers, className values, HTML entities
    pattern = re.compile(r">([^<>{}\n]+)<", re.MULTILINE)
    for m in pattern.finditer(content):
        text = m.group(1).strip()
        if not text:
            continue
        # Skip single characters, pure numbers, whitespace, punctuation-only
        if len(text) <= 1:
            continue
        if re.match(r"^[\d\s.,;:!?@#$%^&*()\-+=\[\]{}|/\\]+$", text):
            continue
        # Skip if it looks like a JS expression result (contains {})
        if "{" in text or "}" in text:
            continue
        # This is likely a hardcoded user-facing string
        return True
    return False


def check_erb_hardcoded_strings(content):
    """Find plain text in ERB that isn't wrapped in t() or I18n.t()."""
    # Remove ERB tags to find plain text
    stripped = re.sub(r"<%.*?%>", "", content, flags=re.DOTALL)
    # Remove HTML tags
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    # Check remaining text for words (not just whitespace/punctuation)
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    # Filter out HTML-like words
    html_words = {"div", "span", "class", "href", "src", "alt", "type", "id", "br", "hr"}
    meaningful = [w for w in words if w.lower() not in html_words]
    return len(meaningful) > 0


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in ALLOWED_EXTENSIONS:
        return []

    normalized = hooklib.normalize(file_path)

    # Skip test/config files
    if any(p in normalized for p in SKIP_PATTERNS):
        return []

    # Only check files under UI source directories
    if not hooklib.under_any(file_path, SOURCE_DIRS):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    # Check if file already uses i18n
    uses_i18n = bool(re.search(r"\bt\s*\(|useTranslation|I18n\.t", content))
    if uses_i18n:
        return []

    found = False
    if ext in (".tsx", ".jsx"):
        found = check_jsx_hardcoded_strings(content)
    elif ext == ".erb":
        found = check_erb_hardcoded_strings(content)

    warnings = []
    if found:
        warnings.append(
            "WARNING: Hardcoded user-facing string detected. "
            "Use translation keys per the `std-i18n` skill — never hardcode user-facing strings."
        )

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
