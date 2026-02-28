#!/usr/bin/env python3
"""
PostToolUse hook: Accessibility checker for web UI files.

Replaces the agent-based accessibility hook with a deterministic command hook.
Checks .tsx/.jsx files under web/, next/, or frontend/ for common a11y violations
per accessibility.md. Exits silently (exit 0, no output) for non-matching files.
"""
import json
import os
import re
import sys


# Only check these extensions
ALLOWED_EXTENSIONS = (".tsx", ".jsx")

# Only check files under these directory prefixes (forward-slash normalized)
ALLOWED_PREFIXES = ("web/", "next/", "frontend/")


def normalize_path(path):
    """Normalize path separators to forward slashes for consistent matching."""
    return path.replace("\\", "/")


def read_file(path):
    """Read file content, return empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def check_non_semantic_clickable(content):
    """Check for <div onClick> or <span onClick> that should be <button>."""
    warnings = []
    pattern = re.compile(r"<(div|span)\s[^>]*onClick", re.IGNORECASE)
    for match in pattern.finditer(content):
        tag = match.group(1)
        warnings.append(
            f"WARNING: Non-semantic <{tag} onClick> found. "
            f"Use <button> for interactive actions per accessibility.md."
        )
    return warnings


def check_missing_alt_text(content):
    """Check for <img> or <Image> without alt attribute."""
    warnings = []
    # Match <img or <Image tags that don't have alt= before the closing >
    pattern = re.compile(r"<(img|Image)\s([^>]*)(/?>)", re.IGNORECASE)
    for match in pattern.finditer(content):
        attrs = match.group(2)
        if not re.search(r"\balt\s*=", attrs):
            tag = match.group(1)
            warnings.append(
                f"WARNING: <{tag}> missing alt text per accessibility.md."
            )
    return warnings


def check_input_without_label(content):
    """Check for <input> without associated <label>."""
    warnings = []
    # Find input tags with an id
    input_pattern = re.compile(
        r"<input\s([^>]*)(/?>)", re.IGNORECASE
    )
    for match in input_pattern.finditer(content):
        attrs = match.group(1)
        # Check if there's an id attribute
        id_match = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs)
        if id_match:
            input_id = id_match.group(1)
            # Check if there's a matching htmlFor/for label
            label_pattern = re.compile(
                r"<label\s[^>]*htmlFor\s*=\s*[\"']"
                + re.escape(input_id)
                + r"[\"']",
                re.IGNORECASE,
            )
            if not label_pattern.search(content):
                # Also check for wrapping <label> (heuristic: label before input on same line group)
                # Simple heuristic — if no htmlFor match found, warn
                warnings.append(
                    "WARNING: <input> without associated <label> "
                    "per accessibility.md."
                )
        elif not re.search(r"\baria-label\s*=", attrs):
            # No id and no aria-label — likely missing label association
            warnings.append(
                "WARNING: <input> without associated <label> or aria-label "
                "per accessibility.md."
            )
    return warnings


def check_focus_indicator_removed(content):
    """Check for outline:none or outline:0 without visible focus replacement."""
    warnings = []
    pattern = re.compile(r"outline\s*:\s*(none|0)\b")
    if pattern.search(content):
        warnings.append(
            "WARNING: Focus indicator removed (outline:none/0) "
            "without visible replacement per accessibility.md."
        )
    return warnings


def check_aria_hidden_interactive(content):
    """Check for aria-hidden='true' on elements with onClick."""
    warnings = []
    pattern = re.compile(
        r"<\w+\s[^>]*aria-hidden\s*=\s*[\"']true[\"'][^>]*onClick"
        r"|<\w+\s[^>]*onClick[^>]*aria-hidden\s*=\s*[\"']true[\"']",
        re.IGNORECASE,
    )
    if pattern.search(content):
        warnings.append(
            "WARNING: Interactive element hidden from assistive technology "
            "(aria-hidden=\"true\" with onClick) per accessibility.md."
        )
    return warnings


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")

    if not file_path:
        sys.exit(0)

    # Check extension
    _, ext = os.path.splitext(file_path)
    if ext not in ALLOWED_EXTENSIONS:
        sys.exit(0)

    # Check directory prefix
    normalized = normalize_path(file_path)
    if not any(prefix in normalized for prefix in ALLOWED_PREFIXES):
        sys.exit(0)

    # Read and analyze file
    content = read_file(file_path)
    if not content:
        sys.exit(0)

    warnings = []
    warnings.extend(check_non_semantic_clickable(content))
    warnings.extend(check_missing_alt_text(content))
    warnings.extend(check_input_without_label(content))
    warnings.extend(check_focus_indicator_removed(content))
    warnings.extend(check_aria_hidden_interactive(content))

    if warnings:
        # Deduplicate similar warnings
        seen = set()
        for w in warnings:
            if w not in seen:
                seen.add(w)
                print(w)

    sys.exit(0)


if __name__ == "__main__":
    main()
