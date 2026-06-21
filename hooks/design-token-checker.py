#!/usr/bin/env python3
"""
PostToolUse hook: Design token compliance checker.

Validates that component and style files use design tokens instead of hardcoded
values. Checks for hardcoded hex/rgb colors, arbitrary pixel spacing, Tailwind
arbitrary values, missing focus-visible states, and missing prefers-reduced-motion.
Outputs warnings only -- never blocks (exit 0).
"""
import os
import re

import _hooklib as hooklib


# File extensions to check
STYLE_EXTENSIONS = (".css", ".scss")
COMPONENT_EXTENSIONS = (".tsx", ".jsx", ".rb")
ALL_EXTENSIONS = STYLE_EXTENSIONS + COMPONENT_EXTENSIONS

# Canonical framework-internal dirs where design token rules apply (wrapper-agnostic)
COMPONENT_DIRS = (
    "src/components",
    "src/theme",
    "app/components",
    "app/views",
)

STYLE_DIRS = (
    "src/styles",
)

# Patterns to detect hardcoded values
# Hex colors: #fff, #ffffff, #ffffffff (but not CSS custom property definitions)
HEX_COLOR_PATTERN = re.compile(
    r"""(?<!var\()(?<!--)(?:^|[\s:,;(])#(?:[0-9a-fA-F]{3,4}){1,2}(?=[\s;,)"'])""",
    re.MULTILINE,
)

# RGB/RGBA/HSL/HSLA function calls in component files (not in CSS variable definitions)
COLOR_FUNCTION_PATTERN = re.compile(
    r"""(?:rgb|rgba|hsl|hsla)\s*\(\s*\d+""",
    re.MULTILINE,
)

# Tailwind arbitrary value classes: bg-[#...], text-[#...], p-[13px], etc.
TAILWIND_ARBITRARY_COLOR = re.compile(
    r"""(?:bg|text|border|ring|outline|shadow|fill|stroke)-\[#[0-9a-fA-F]+\]""",
)

TAILWIND_ARBITRARY_SPACING = re.compile(
    r"""(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|space-[xy]|w|h|min-w|min-h|max-w|max-h)-\[\d+px\]""",
)

TAILWIND_ARBITRARY_FONT = re.compile(
    r"""text-\[\d+px\]""",
)

# Interactive element patterns (buttons, links, inputs)
INTERACTIVE_ELEMENT_PATTERN = re.compile(
    r"""<(?:button|a|input|select|textarea|Button|Link|IconButton)\b""",
)

# Focus-visible pattern
FOCUS_VISIBLE_PATTERN = re.compile(
    r"""focus-visible:""",
)

# Motion/transition/animation patterns
MOTION_PATTERN = re.compile(
    r"""(?:transition|animate|animation|motion)""",
    re.IGNORECASE,
)

# motion-safe or prefers-reduced-motion
REDUCED_MOTION_PATTERN = re.compile(
    r"""(?:motion-safe:|motion-reduce:|prefers-reduced-motion)""",
)


def is_component_scope(path, ext):
    """Check if the file is in a component-style directory (wrapper-agnostic)."""
    return hooklib.under_any(path, COMPONENT_DIRS) or (
        ext in (".tsx", ".jsx") and hooklib.under(path, "app")
    )


def is_style_scope(path):
    """Check if the file is in a style directory (wrapper-agnostic)."""
    return hooklib.under_any(path, STYLE_DIRS) or hooklib.under(path, "src")


def is_in_scope(path, ext):
    """Check if the file is in a directory where design token rules apply."""
    if is_component_scope(path, ext) or is_style_scope(path):
        return True
    # Also check tailwind config and globals.css anywhere
    basename = os.path.basename(path)
    if basename in ("tailwind.config.ts", "tailwind.config.js", "globals.css"):
        return True
    return False


def get_display_path(path):
    """Extract a short display path for warning messages."""
    for sub in COMPONENT_DIRS + STYLE_DIRS:
        if hooklib.under(path, sub):
            marker = sub + "/"
            idx = path.find(marker)
            if idx != -1:
                return path[idx + len(marker):]
    for sub in ("app", "src"):
        if hooklib.under(path, sub):
            marker = sub + "/"
            idx = path.find(marker)
            if idx != -1:
                return path[idx + len(marker):]
    return os.path.basename(path)


def check_hardcoded_colors(content, ext, display_path):
    """Check for hardcoded hex/rgb colors in component files."""
    warnings = []

    # Skip CSS files that define custom properties (token definitions are OK)
    if ext in STYLE_EXTENSIONS:
        # Only warn about hex colors that aren't in variable definitions
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip CSS custom property definitions and comments
            if stripped.startswith("--") or stripped.startswith("/*") or stripped.startswith("//"):
                continue
            if HEX_COLOR_PATTERN.search(line):
                warnings.append(
                    f"WARNING: Design token — Hardcoded hex color in {display_path}:{i}. "
                    f"Use a design token (e.g., hsl(var(--primary))) instead."
                )
                if len(warnings) >= 3:
                    break
        return warnings

    # For component files, check both hex and rgb/hsl functions
    if ext in COMPONENT_EXTENSIONS:
        for match in TAILWIND_ARBITRARY_COLOR.finditer(content):
            warnings.append(
                f"WARNING: Design token — Tailwind arbitrary color '{match.group()}' in {display_path}. "
                f"Use a token class (e.g., bg-primary, text-foreground) instead."
            )
            if len(warnings) >= 3:
                break

    return warnings


def check_arbitrary_spacing(content, display_path):
    """Check for Tailwind arbitrary spacing values."""
    warnings = []
    for match in TAILWIND_ARBITRARY_SPACING.finditer(content):
        warnings.append(
            f"WARNING: Design token — Arbitrary spacing '{match.group()}' in {display_path}. "
            f"Use spacing scale tokens (e.g., p-4, gap-2, m-8) instead."
        )
        if len(warnings) >= 3:
            break
    return warnings


def check_arbitrary_font_size(content, display_path):
    """Check for Tailwind arbitrary font size values."""
    warnings = []
    for match in TAILWIND_ARBITRARY_FONT.finditer(content):
        warnings.append(
            f"WARNING: Design token — Arbitrary font size '{match.group()}' in {display_path}. "
            f"Use type scale tokens (e.g., text-sm, text-base, text-lg) instead."
        )
        if len(warnings) >= 3:
            break
    return warnings


def check_focus_visible(content, ext, display_path):
    """Check that interactive elements have focus-visible states."""
    warnings = []

    # Only check TSX/JSX component files
    if ext not in (".tsx", ".jsx"):
        return warnings

    has_interactive = INTERACTIVE_ELEMENT_PATTERN.search(content)
    has_focus_visible = FOCUS_VISIBLE_PATTERN.search(content)

    if has_interactive and not has_focus_visible:
        warnings.append(
            f"WARNING: Design token — Interactive elements in {display_path} lack "
            f"focus-visible: states. Add focus-visible:ring-2 focus-visible:ring-ring "
            f"for keyboard accessibility."
        )

    return warnings


def check_reduced_motion(content, ext, display_path):
    """Check that animations respect prefers-reduced-motion."""
    warnings = []

    if ext not in (".tsx", ".jsx", ".css", ".scss"):
        return warnings

    has_motion = MOTION_PATTERN.search(content)
    has_reduced_motion = REDUCED_MOTION_PATTERN.search(content)

    if has_motion and not has_reduced_motion:
        warnings.append(
            f"WARNING: Design token — Animations in {display_path} may lack "
            f"prefers-reduced-motion handling. Use motion-safe: prefix or "
            f"@media (prefers-reduced-motion: reduce) for accessibility."
        )

    return warnings


def check(event):
    if hooklib.tool_name(event) not in ("Edit", "Write"):
        return []

    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in ALL_EXTENSIONS:
        return []

    normalized = hooklib.normalize(file_path)

    if not is_in_scope(normalized, ext):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    display_path = get_display_path(normalized)

    warnings = []
    warnings.extend(check_hardcoded_colors(content, ext, display_path))
    warnings.extend(check_arbitrary_spacing(content, display_path))
    warnings.extend(check_arbitrary_font_size(content, display_path))
    warnings.extend(check_focus_visible(content, ext, display_path))
    warnings.extend(check_reduced_motion(content, ext, display_path))

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
