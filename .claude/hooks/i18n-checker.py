#!/usr/bin/env python3
"""
PostToolUse hook: Internationalization (i18n) checker.

Checks .tsx, .jsx, and .erb files for hardcoded user-facing strings
that should use translation keys per i18n.md.
Exits silently for non-matching files.
"""
import json
import os
import re
import sys


ALLOWED_EXTENSIONS = (".tsx", ".jsx", ".erb")
SOURCE_PREFIXES = ("backend/app/views/", "mobile/src/", "web/src/", "next/")
SKIP_PATTERNS = (".test.", ".spec.", "__tests__", ".config.", ".d.ts")


def normalize(path):
    return path.replace("\\", "/")


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


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


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    _, ext = os.path.splitext(file_path)
    if ext not in ALLOWED_EXTENSIONS:
        sys.exit(0)

    normalized = normalize(file_path)

    # Skip test/config files
    if any(p in normalized for p in SKIP_PATTERNS):
        sys.exit(0)

    # Only check files under UI source directories
    if not any(p in normalized for p in SOURCE_PREFIXES):
        sys.exit(0)

    content = read_file(file_path)
    if not content:
        sys.exit(0)

    # Check if file already uses i18n
    uses_i18n = bool(re.search(r"\bt\s*\(|useTranslation|I18n\.t", content))
    if uses_i18n:
        sys.exit(0)

    found = False
    if ext in (".tsx", ".jsx"):
        found = check_jsx_hardcoded_strings(content)
    elif ext == ".erb":
        found = check_erb_hardcoded_strings(content)

    if found:
        print(
            "WARNING: Hardcoded user-facing string detected. "
            "Use translation keys per i18n.md — never hardcode user-facing strings."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
