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
# .css/.scss included: `outline: none` is CSS-declaration syntax and lives there. Excluding
# them while matching only CSS syntax is what made this check unreachable on this stack.
ALLOWED_EXTENSIONS = (".tsx", ".jsx", ".css", ".scss")


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


# An id/htmlFor is either a string literal (`id="email"`) or a JSX expression
# (`id={`settle-${row.id}`}`). The expression form is the NORM in React the moment a list is
# involved, and the old pattern only matched the literal — so every dynamic id fell through to
# the no-id branch and was warned at despite carrying a perfectly good label.
_ATTR_VALUE = r"""(?:["']([^"']+)["']|\{([^}]+)\})"""
ID_ATTR = re.compile(r"\bid\s*=\s*" + _ATTR_VALUE)
HTMLFOR_ATTR = re.compile(r"\b(?:htmlFor|for)\s*=\s*" + _ATTR_VALUE, re.IGNORECASE)
# A wrapping label needs no htmlFor at all — `<label>Email <input /></label>` is valid HTML and
# valid React. The old code named this case in a comment and then warned anyway.
LABEL_BLOCK = re.compile(r"<label\b[^>]*>.*?</label>", re.IGNORECASE | re.DOTALL)


def _norm(value):
    """Compare attribute values ignoring incidental whitespace inside a JSX expression."""
    return re.sub(r"\s+", "", value or "")


def check_input_without_label(content):
    """Flag an <input> only when nothing associates a label with it.

    Three ways an input is correctly labelled, and this checker used to recognise exactly one:

      1. `id="email"` + `<label htmlFor="email">`            — the literal form (was handled)
      2. `id={expr}`  + `<label htmlFor={expr}>`             — dynamic ids; the React norm
      3. `<label>Email <input /></label>`                    — a wrapping label, no id needed

    2 and 3 were both flagged. That matters more now than it did: these warnings used to go to a
    debug log nobody read, so a false positive cost nothing. They now reach the model on every
    edit, and a check that fires on correct code is the fastest way to teach everyone to ignore
    the whole layer — which this repo states as a rule (`migration-validator.py`) and then broke
    here.
    """
    warnings = []
    label_spans = [m.span() for m in LABEL_BLOCK.finditer(content)]
    for_values = {_norm(m.group(1) or m.group(2)) for m in HTMLFOR_ATTR.finditer(content)}

    for match in re.finditer(r"<input\s([^>]*?)/?>", content, re.IGNORECASE):
        attrs = match.group(1)

        # (3) wrapped in a label — needs no id, no htmlFor, no aria-label.
        start = match.start()
        if any(a <= start < b for a, b in label_spans):
            continue

        # (1) and (2) — an id in either form, paired with an htmlFor in either form.
        id_match = ID_ATTR.search(attrs)
        if id_match:
            if _norm(id_match.group(1) or id_match.group(2)) in for_values:
                continue
            warnings.append(
                "WARNING: <input> has an id but no <label htmlFor> matches it "
                "per the `std-accessibility` skill."
            )
            continue

        # No id at all — an aria-label (or aria-labelledby) is the remaining valid option.
        if not re.search(r"\baria-label(?:ledby)?\s*=", attrs):
            warnings.append(
                "WARNING: <input> without associated <label> or aria-label "
                "per the `std-accessibility` skill."
            )
    return warnings


# Removing the outline is only a defect when nothing visible replaces it — the docstring always
# said so, and the code never checked. `focus-visible:outline-none focus-visible:ring-2` is this
# repo's OWN recommended idiom (std-design-system/references/component-variants.md:79): it
# removes the browser outline and draws a ring. Warning on that would flag the correct pattern.
FOCUS_REPLACEMENT = re.compile(
    r"ring-\d|ring-\[|ring-offset|box-shadow|outline\s*:\s*(?!none|0)\S|outline-\d|"
    r"outline-\[|border-\d",
    re.IGNORECASE,
)
# Two syntaxes, because this stack has two. CSS declarations (`outline: none`) live in
# .css/.scss; Tailwind (`outline-none`, `focus:outline-none`) lives in .tsx/.jsx className
# strings. The old pattern only matched the CSS form — and the file scope only allowed .tsx/.jsx,
# so the two were disjoint and the check could never fire on this stack at all.
FOCUS_REMOVED = re.compile(r"outline\s*:\s*(?:none|0)\b|\boutline-none\b")


def check_focus_indicator_removed(content):
    """Flag a removed focus indicator only when nothing visible replaces it."""
    warnings = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if not FOCUS_REMOVED.search(line):
            continue
        # Look at the surrounding declaration/element, not just the one line: in CSS the
        # replacement is usually the next declaration; in JSX it is usually the same className.
        window = "\n".join(lines[max(0, i - 3):i + 4])
        if FOCUS_REPLACEMENT.search(window):
            continue
        warnings.append(
            f"WARNING: Focus indicator removed (line {i + 1}) with no visible replacement "
            f"nearby. Keyboard users lose all focus feedback. Add a ring "
            f"(e.g. `focus-visible:ring-2 focus-visible:ring-offset-2`) per the "
            f"`std-accessibility` skill."
        )
        break  # one warning is enough
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
