#!/usr/bin/env python3
"""
PostToolUse hook: Design token compliance checker.

Validates that component and style files use design tokens instead of hardcoded values, per the
`std-design-system` skill: hex colors, arbitrary spacing and font sizes, color utilities naming
no registered token, styled controls without focus-visible, and movement without a reduced-motion
path. Outputs warnings only -- never blocks (exit 0). Each rule replaced a confirmed false signal:
  * Focus is judged per HOST control (<button>, <a>, <input>, <select>, <textarea>, or a <Link>
    styled at the call site) carrying its own className. Using <Button> inherits the atom's ring,
    as does a className built from `buttonVariants(...)`/`cva(...)`. Tests, stories and React
    Native (which has no `focus-visible:`) are out.
  * Motion means movement (animate-*, keyframes, motion components, transform/size transitions;
    not `transition-colors`), and every house mechanism counts as handled: `motion-safe:`,
    `motion-reduce:`, `prefers-reduced-motion`, framer-motion `useReducedMotion` or `MotionConfig
    reducedMotion`, React Native `AccessibilityInfo.isReduceMotionEnabled` (with its own remedy).
  * CSS variables hold complete colors (`@theme inline { --color-x: var(--x) }`): use `var(--x)`.
  * A utility on a role the registry lacks (`bg-primary-600`) compiles to no CSS, silently.
    shadcn/ui's 15 token names are registered ALIASES of house roles, so stock primitives resolve.
  * Vendored shadcn/ui primitives (components.json `aliases.ui`) skip the style checks but keep
    the registry check - a class that compiles to nothing is a bug, not a style.
  * Scope is the hooks.json matcher, not a private tool list; package-root `components/` counts.
"""
import itertools
import os
import re

import _hooklib as hooklib
import _vendored as vendored
from _jsx import scan_until


STYLE_EXTENSIONS = (".css", ".scss")
COMPONENT_EXTENSIONS = (".tsx", ".jsx", ".rb")
ALL_EXTENSIONS = STYLE_EXTENSIONS + COMPONENT_EXTENSIONS
# Canonical framework-internal dirs where design token rules apply (wrapper-agnostic)
COMPONENT_DIRS = ("src/components", "src/theme", "app/components", "app/views")
STYLE_DIRS = ("src/styles",)

# The house color registry (skills/theming/references/platform-integration.md, `@theme`).
HOUSE_COLOR_TOKENS = frozenset((
    "background", "foreground", "primary", "primary-foreground", "secondary",
    "secondary-foreground", "accent", "accent-foreground", "muted", "muted-foreground", "card",
    "card-foreground", "popover", "popover-foreground", "success", "success-foreground",
    "warning", "warning-foreground", "error", "error-foreground", "info", "info-foreground",
    "border", "input", "ring",
))
# shadcn/ui token names, registered as aliases of house roles: destructive -> error,
# sidebar-* -> card/accent/primary/border/ring, chart-1..5 contrast-checked against the surfaces.
SHADCN_ALIAS_TOKENS = frozenset((
    "destructive", "destructive-foreground", "chart-1", "chart-2", "chart-3", "chart-4",
    "chart-5", "sidebar", "sidebar-foreground", "sidebar-primary", "sidebar-primary-foreground",
    "sidebar-accent", "sidebar-accent-foreground", "sidebar-border", "sidebar-ring",
))
REGISTERED_COLOR_TOKENS = HOUSE_COLOR_TOKENS | SHADCN_ALIAS_TOKENS
# Only utilities built on a role name are judged, so Tailwind's own `text-sm`, `border-2` and
# `bg-red-500` are never read as tokens. `danger` and `neutral` are the usual unregistered roles.
ROLE_ROOTS = frozenset({t.split("-")[0] for t in REGISTERED_COLOR_TOKENS} | {"danger", "neutral"})

# Hex colors: #fff, #ffffff, #ffffffff (but not CSS custom property definitions)
HEX_COLOR_PATTERN = re.compile(
    r"""(?<!var\()(?<!--)(?:^|[\s:,;(])#(?:[0-9a-fA-F]{3,4}){1,2}(?=[\s;,)"'])""", re.MULTILINE)
TAILWIND_ARBITRARY_COLOR = re.compile(r"(?:bg|text|border|ring|outline|shadow|fill|stroke)-\[#[0-9a-fA-F]+\]")
TAILWIND_ARBITRARY_SPACING = re.compile(
    r"(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|space-[xy]|w|h|min-w|min-h|max-w|max-h)-\[\d+px\]")
TAILWIND_ARBITRARY_FONT = re.compile(r"text-\[\d+px\]")
ARBITRARY_VALUE_RULES = (
    (TAILWIND_ARBITRARY_SPACING, "Arbitrary spacing", "Use spacing scale tokens (e.g., p-4, gap-2, m-8) instead."),
    (TAILWIND_ARBITRARY_FONT, "Arbitrary font size", "Use type scale tokens (e.g., text-sm, text-base, text-lg) instead."),
)

# Host controls draw focus themselves; <Button>/<IconButton> consumers inherit the atom's ring.
HOST_CONTROL = re.compile(r"<(button|a|input|select|textarea|Link)\b")
CLASS_ATTR = re.compile(r"(?<![\w-])class(?:Name)?\s*=\s*")
FOCUS_PROVIDED = re.compile(r"focus-visible:|\w*[vV]ariants\s*\(|\bcva\s*\(|\btv\s*\(")
NON_PRODUCT_FILES = (".test.", ".spec.", ".stories.")

# Movement, not any mention of "transition": fading colors and opacity is not motion.
_MOVEMENT = r"transform|translate|scale|rotate|skew|width|height|inset|left|right|top|bottom|margin"
MOTION_PATTERN = re.compile(
    r"(?<![\w-])animate-(?!none(?![\w-]))[\w\[]"
    r"|@keyframes\b|\banimation(?:-name)?\s*:\s*(?!none\b)\S"
    rf"|\btransition(?:-property)?\s*:[^;}}\n]*\b(?:{_MOVEMENT}|all)\b"
    rf"|(?<![\w-])transition-(?:transform|\[[^\]]*(?:{_MOVEMENT})[^\]]*\])"
    r"|<m(?:otion)?\.\w|\bAnimated\.(?:timing|spring|decay|loop|sequence|parallel)\b"
    r"|\bLayoutAnimation\.|\bwith(?:Timing|Spring|Decay|Repeat)\s*\("
    r"|scroll-behavior\s*:\s*smooth|(?<![\w-])scroll-smooth(?![\w-])"
)
# `transition` / `transition-all` moves things only when a state variant transforms them.
TRANSITION_ANY = re.compile(r"(?<![\w-])transition(?:-all)?(?![\w-])")
STATE_TRANSFORM = re.compile(r"[\w\]-]:-?(?:translate|scale|rotate|skew)-")
REDUCED_MOTION_PATTERN = re.compile(
    r"motion-safe:|motion-reduce:|prefers-reduced-motion|\buseReducedMotion\b|\breducedMotion\b"
    r"|\bisReduceMotionEnabled\b|\breduceMotionChanged\b|\bReduceMotion\."
)
WEB_MOTION_REMEDY = ("may lack prefers-reduced-motion handling. Use motion-safe: prefix or "
                     "@media (prefers-reduced-motion: reduce) for accessibility.")
NATIVE_MOTION_REMEDY = ("lack a reduced-motion path. React Native has no motion-safe: — gate them "
                        "on AccessibilityInfo.isReduceMotionEnabled() (a useReducedMotion hook).")

CLASS_STRING = re.compile(r'"([^"\n]*)"|\'([^\'\n]*)\'|`([^`]*)`')
# Strings bound to these attributes are ids, keys and URLs - never class lists.
NON_CLASS_ATTR = re.compile(
    r"(?<![\w-])(?:id|htmlFor|for|name|key|href|src|to|type|role|value|aria-[\w-]+|data-[\w-]+)\s*=\s*\{?\s*$")
COLOR_UTILITY = re.compile(
    r"(?<![\w-])(?:bg|text|border|ring-offset|ring|outline|fill|stroke|divide|placeholder|"
    r"accent|caret|decoration|shadow|from|via|to)-([a-z][a-z0-9-]*?)(?:/\d+)?(?![\w-])"
)


def is_in_scope(path, ext):
    """Component, style and token-config files, wrapper-agnostic."""
    if hooklib.under_any(path, COMPONENT_DIRS + STYLE_DIRS + ("src",)):
        return True
    if ext in (".tsx", ".jsx") and hooklib.under_any(path, ("app", "components")):
        return True
    return os.path.basename(path) in ("tailwind.config.ts", "tailwind.config.js", "globals.css")


def get_display_path(path):
    """Extract a short display path for warning messages."""
    for sub in COMPONENT_DIRS + STYLE_DIRS + ("app", "src", "components"):
        idx = path.find(sub + "/") if hooklib.under(path, sub) else -1
        if idx != -1:
            return path[idx + len(sub) + 1:]
    return os.path.basename(path)


def check_hardcoded_colors(content, ext, display_path):
    """Hex colors outside custom-property definitions (CSS); arbitrary color classes (components)."""
    if ext in STYLE_EXTENSIONS:
        hits = [i for i, line in enumerate(content.split("\n"), 1)
                if not line.strip().startswith(("--", "/*", "//")) and HEX_COLOR_PATTERN.search(line)]
        return [f"WARNING: Design token — Hardcoded hex color in {display_path}:{i}. Use a design "
                f"token (e.g., var(--primary)) instead — see the `std-design-system` skill."
                for i in hits[:3]]
    return [f"WARNING: Design token — Tailwind arbitrary color '{m.group()}' in {display_path}. "
            f"Use a token class (e.g., bg-primary, text-foreground) instead."
            for m in itertools.islice(TAILWIND_ARBITRARY_COLOR.finditer(content), 3)]


def check_arbitrary_values(content, display_path):
    """Tailwind arbitrary spacing and font sizes, at most three of each."""
    warnings = []
    for pattern, what, remedy in ARBITRARY_VALUE_RULES:
        warnings.extend(f"WARNING: Design token — {what} '{m.group()}' in {display_path}. {remedy}"
                        for m in itertools.islice(pattern.finditer(content), 3))
    return warnings


def class_attribute(content, tag_match):
    """The className/class value written on this opening tag, or None when it carries none."""
    end = scan_until(content, tag_match.end(), ">")
    attr = CLASS_ATTR.search(content[tag_match.end():end] if end != -1 else "")
    if not attr:
        return None
    value = content[tag_match.end() + attr.end():end]
    closer = {'"': '"', "'": "'", "{": "}"}.get(value[:1])
    if closer is None:
        return None
    close = scan_until(value, 1, "}") if closer == "}" else value.find(closer, 1)
    return value[:close + 1] if close != -1 else value


def check_focus_visible(content, ext, display_path):
    """A host control styled at this call site must carry its own focus-visible state."""
    if ext not in (".tsx", ".jsx"):
        return []
    for match in HOST_CONTROL.finditer(content):
        classes = class_attribute(content, match)
        # No className keeps the browser ring; `{className}` alone is styled somewhere else.
        if classes is None or not re.search(r"[\"'`]", classes) or FOCUS_PROVIDED.search(classes):
            continue
        line = content.count("\n", 0, match.start()) + 1
        return [f"WARNING: Design token — Interactive elements in {display_path} lack focus-visible: "
                f"states (<{match.group(1)}> at line {line}). Add focus-visible:ring-2 "
                f"focus-visible:ring-ring for keyboard accessibility."]
    return []


def has_motion(code):
    """Movement: animations, keyframes, motion components, or transitions that move things."""
    if MOTION_PATTERN.search(code):
        return True
    return bool(TRANSITION_ANY.search(code) and STATE_TRANSFORM.search(code))


def check_reduced_motion(content, ext, display_path, native=False):
    """Check that animations respect prefers-reduced-motion (AccessibilityInfo in React Native)."""
    if ext not in (".tsx", ".jsx", ".css", ".scss"):
        return []
    # `@import "tw-animate-css"` names a stylesheet; it animates nothing by itself.
    code = "\n".join(line for line in content.splitlines() if not line.lstrip().startswith("@import"))
    if not has_motion(code) or REDUCED_MOTION_PATTERN.search(code):
        return []
    remedy = NATIVE_MOTION_REMEDY if native else WEB_MOTION_REMEDY
    return [f"WARNING: Design token — Animations in {display_path} {remedy}"]


def class_strings(content, ext):
    """Text holding Tailwind classes: CSS `@apply` lists, or string literals used as class lists."""
    if ext in STYLE_EXTENSIONS:
        return re.findall(r"@apply\s+([^;}\n]+)", content)
    return [next(group for group in match.groups() if group is not None)
            for match in CLASS_STRING.finditer(content)
            if not NON_CLASS_ATTR.search(content, max(0, match.start() - 40), match.start())]


def unregistered_utilities(text, local_tokens):
    """Utilities in one class list whose role token no registry defines."""
    found = []
    for match in COLOR_UTILITY.finditer(text):
        name = match.group(1)
        if name.split("-")[0] not in ROLE_ROOTS or name in REGISTERED_COLOR_TOKENS:
            continue
        if name not in local_tokens and not re.fullmatch(r"neutral-\d{2,3}", name):
            found.append(match.group(0))  # not defined in this file, not Tailwind's own neutral palette
    return found


def check_unregistered_tokens(content, ext, display_path):
    """Color utilities on a role token the registry does not define compile to no CSS."""
    local_tokens = set(re.findall(r"--(?:color-)?([a-z][a-z0-9-]*)\s*:", content))
    utilities = []
    for text in class_strings(content, ext):
        utilities.extend(u for u in unregistered_utilities(text, local_tokens) if u not in utilities)
    return [f"WARNING: Design token — `{utility}` in {display_path} names no registered token, so it "
            f"compiles to no CSS. Use a registered role (bg-error, text-muted-foreground, "
            f"bg-primary/90) or register the token first — see the `std-design-system` skill."
            for utility in utilities[:3]]


def style_warnings(file_path, content, ext, display_path):
    """The style checks - skipped for CLI-owned shadcn primitives."""
    native = hooklib.is_react_native(file_path)
    product = not any(p in hooklib.normalize(file_path) for p in NON_PRODUCT_FILES)
    warnings = check_hardcoded_colors(content, ext, display_path)
    warnings.extend(check_arbitrary_values(content, display_path))
    if product and not native:
        warnings.extend(check_focus_visible(content, ext, display_path))
    warnings.extend(check_reduced_motion(content, ext, display_path, native))
    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []
    _, ext = os.path.splitext(file_path)
    normalized = hooklib.normalize(file_path)
    if ext not in ALL_EXTENSIONS or not is_in_scope(normalized, ext):
        return []
    content = hooklib.read_file(file_path)
    if not content:
        return []
    display_path = get_display_path(normalized)
    tokens = check_unregistered_tokens(content, ext, display_path)
    if vendored.is_vendored_ui(file_path):
        return tokens
    return style_warnings(file_path, content, ext, display_path) + tokens


if __name__ == "__main__":
    hooklib.run_post_checker(check)
