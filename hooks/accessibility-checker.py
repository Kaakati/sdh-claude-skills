#!/usr/bin/env python3
"""
PostToolUse hook: Accessibility checker for web UI files.

Replaces the agent-based accessibility hook with a deterministic command hook.
Checks .tsx/.jsx browser-React files (Vite/Next, any wrapper dir) for common a11y
violations per the `std-accessibility` skill. React Native files are skipped. Exits silently
(exit 0, no output) for non-matching files.
"""
import os
import re

import _hooklib as hooklib


# Only check these extensions
ALLOWED_EXTENSIONS = (".tsx", ".jsx")


def check_non_semantic_clickable(content):
    """Check for <div onClick> or <span onClick> that should be <button>."""
    warnings = []
    pattern = re.compile(r"<(div|span)\s[^>]*onClick", re.IGNORECASE)
    for match in pattern.finditer(content):
        tag = match.group(1)
        warnings.append(
            f"WARNING: Non-semantic <{tag} onClick> found. "
            f"Use <button> for interactive actions per the `std-accessibility` skill."
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
                f"WARNING: <{tag}> missing alt text per the `std-accessibility` skill."
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
                    "per the `std-accessibility` skill."
                )
        elif not re.search(r"\baria-label\s*=", attrs):
            # No id and no aria-label — likely missing label association
            warnings.append(
                "WARNING: <input> without associated <label> or aria-label "
                "per the `std-accessibility` skill."
            )
    return warnings


def check_focus_indicator_removed(content):
    """Check for outline:none or outline:0 without visible focus replacement."""
    warnings = []
    pattern = re.compile(r"outline\s*:\s*(none|0)\b")
    if pattern.search(content):
        warnings.append(
            "WARNING: Focus indicator removed (outline:none/0) "
            "without visible replacement per the `std-accessibility` skill."
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
            "(aria-hidden=\"true\" with onClick) per the `std-accessibility` skill."
        )
    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)

    if not file_path:
        return []

    # Check extension
    _, ext = os.path.splitext(file_path)
    if ext not in ALLOWED_EXTENSIONS:
        return []

    # Skip React Native — these a11y rules are for browser React (Vite/Next)
    if hooklib.is_react_native(file_path):
        return []

    # Read and analyze file
    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []
    warnings.extend(check_non_semantic_clickable(content))
    warnings.extend(check_missing_alt_text(content))
    warnings.extend(check_input_without_label(content))
    warnings.extend(check_focus_indicator_removed(content))
    warnings.extend(check_aria_hidden_interactive(content))

    if warnings:
        # Deduplicate similar warnings
        result = []
        seen = set()
        for w in warnings:
            if w not in seen:
                seen.add(w)
                result.append(w)
        return result

    return []


if __name__ == "__main__":
    hooklib.run_post_checker(check)
