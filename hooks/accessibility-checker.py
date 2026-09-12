#!/usr/bin/env python3
"""
PostToolUse hook: Accessibility checker for web UI files.

Replaces the agent-based accessibility hook with a deterministic command hook.
Checks .tsx/.jsx browser-React files (Vite/Next, any wrapper dir) for common a11y
violations per the `std-accessibility` skill. React Native files are skipped. Exits silently
(exit 0, no output) for non-matching files.

Opening tags are read JSX-aware: a `>` inside `{...}` or quotes does not end the tag. The old
`[^>]*` scan stopped at the `>` of an inline arrow handler, so an `alt` or `aria-label` written
after `onLoad={() => ...}` was never seen. An <input>/<img> that spreads its component's own rest
PARAMETER (`function Input({ className, ...props })` then `{...props}`) is a pass-through
primitive labelled at its call site; a call spread (`{...register("email")}`, `{...field}`) is
not, and is still checked. An input placed directly in shadcn's <FormControl> slot is labelled by
the FormLabel that shares its generated id.

Vendored shadcn/ui primitives (components.json `aliases.ui`) are CLI-owned: the alt, label and
focus-style checks are skipped there. The structural defects - a clickable <div>/<span>, an
interactive element hidden from assistive technology - are reported wherever they appear.
"""
import os
import re

import _hooklib as hooklib
import _vendored as vendored
from _jsx import scan_until


# Only check these extensions
# .css/.scss included: `outline: none` is CSS-declaration syntax and lives there. Excluding
# them while matching only CSS syntax is what made this check unreachable on this stack.
ALLOWED_EXTENSIONS = (".tsx", ".jsx", ".css", ".scss")

# `...props }: Props)` / `...rest })` - a rest element closing a destructured PARAMETER list.
REST_PARAMETER = re.compile(r"\.\.\.(\w+)\s*\}\s*[:)]")
SPREAD_ATTR = re.compile(r"\{\s*\.\.\.(\w+)\s*\}")
ON_CLICK = re.compile(r"\bonClick\s*=", re.IGNORECASE)
ARIA_HIDDEN_TRUE = re.compile(r"""aria-hidden\s*=\s*(?:["']true["']|\{\s*true\s*\})""", re.IGNORECASE)
FORM_CONTROL_SLOT = re.compile(r"<FormControl\b[^<]*>\s*$")
# hidden inputs need no label; submit/reset/button inputs are named by their value.
NAMED_BY_VALUE = re.compile(r"""\btype\s*=\s*["'](?:hidden|submit|reset|button)["']""")


def opening_tags(content, tag_pattern):
    """(match, attribute text) for each opening tag matching `tag_pattern` that closes nearby."""
    for match in re.finditer(tag_pattern, content):
        end = scan_until(content, match.end(), ">")
        if end != -1:
            yield match, content[match.end():end]


def passes_through(attrs, rest_names):
    """The tag spreads its component's own rest parameter, so the caller supplies the name."""
    return any(name in rest_names for name in SPREAD_ATTR.findall(attrs))


def check_non_semantic_clickable(content):
    """Check for <div onClick> or <span onClick> that should be <button>."""
    return [
        f"WARNING: Non-semantic <{match.group(1)} onClick> found. "
        f"Use <button> for interactive actions per the `std-accessibility` skill."
        for match, attrs in opening_tags(content, r"(?i)<(div|span)\b") if ON_CLICK.search(attrs)
    ]


def check_missing_alt_text(content, rest_names=()):
    """Check for <img> or <Image> without alt attribute."""
    return [
        f"WARNING: <{match.group(1)}> missing alt text per the `std-accessibility` skill."
        for match, attrs in opening_tags(content, r"(?i)<(img|Image)\b")
        if not re.search(r"\balt\s*=", attrs) and not passes_through(attrs, rest_names)
    ]


# An id/htmlFor is either a string literal (`id="email"`) or a JSX expression
# (`id={`settle-${row.id}`}`). The expression form is the NORM in React the moment a list is
# involved, and the old pattern only matched the literal — so every dynamic id fell through to
# the no-id branch and was warned at despite carrying a perfectly good label.
_ATTR_VALUE = r"""(?:["']([^"']+)["']|\{([^}]+)\})"""
ID_ATTR = re.compile(r"(?<![\w-])id\s*=\s*" + _ATTR_VALUE)
HTMLFOR_ATTR = re.compile(r"(?<![\w-])(?:htmlFor|for)\s*=\s*" + _ATTR_VALUE, re.IGNORECASE)
# A wrapping label needs no htmlFor at all — `<label>Email <input /></label>` is valid HTML and
# valid React. The old code named this case in a comment and then warned anyway.
LABEL_BLOCK = re.compile(r"<label\b[^>]*>.*?</label>", re.IGNORECASE | re.DOTALL)


def _norm(value):
    """Compare attribute values ignoring incidental whitespace inside a JSX expression."""
    return re.sub(r"\s+", "", value or "")


def check_input_without_label(content, rest_names=None):
    """Flag an <input> only when nothing associates a label with it.

    Ways an input is correctly labelled, and this checker used to recognise exactly one:

      1. `id="email"` + `<label htmlFor="email">`            — the literal form (was handled)
      2. `id={expr}`  + `<label htmlFor={expr}>`             — dynamic ids; the React norm
      3. `<label>Email <input /></label>`                    — a wrapping label, no id needed
      4. `<input {...props} />` inside `Input({ ...props })` — a primitive; its CALLER labels it

    2 and 3 were both flagged, and 4 fired on every shadcn Input. That matters more now than it
    did: these warnings used to go to a debug log nobody read, so a false positive cost nothing.
    They now reach the model on every edit, and a check that fires on correct code is the fastest
    way to teach everyone to ignore the whole layer — which this repo states as a rule
    (`migration-validator.py`) and then broke here.
    """
    if rest_names is None:
        rest_names = set(REST_PARAMETER.findall(content))
    label_spans = [m.span() for m in LABEL_BLOCK.finditer(content)]
    for_values = {_norm(m.group(1) or m.group(2)) for m in HTMLFOR_ATTR.finditer(content)}
    context = (label_spans, for_values, rest_names)
    warnings = []
    for match, attrs in opening_tags(content, r"(?i)<input\b"):
        problem = input_label_problem(content, match.start(), attrs, context)
        if problem:
            warnings.append(problem)
    return warnings


def input_label_problem(content, start, attrs, context):
    """The warning for one <input>, or None when something labels it or it needs no label."""
    label_spans, for_values, rest_names = context
    # (3) wrapped in a label, or a hidden/value-named input — needs no id, no htmlFor.
    if any(a <= start < b for a, b in label_spans) or NAMED_BY_VALUE.search(attrs):
        return None
    # (4) a pass-through primitive, or the shadcn <FormControl> slot that FormLabel points at.
    if passes_through(attrs, rest_names) or FORM_CONTROL_SLOT.search(content, max(0, start - 300), start):
        return None

    # (1) and (2) — an id in either form, paired with an htmlFor in either form.
    id_match = ID_ATTR.search(attrs)
    if id_match:
        if _norm(id_match.group(1) or id_match.group(2)) in for_values:
            return None
        return ("WARNING: <input> has an id but no <label htmlFor> matches it "
                "per the `std-accessibility` skill.")

    # No id at all — an aria-label (or aria-labelledby) is the remaining valid option.
    if re.search(r"\baria-label(?:ledby)?\s*=", attrs):
        return None
    return ("WARNING: <input> without associated <label> or aria-label "
            "per the `std-accessibility` skill.")


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
# The replacement must be on the SAME element: its opening tag, its class string, or its
# declaration block (a CSS rule, an inline style object). A +-3-line window read a neighbouring
# element's ring as this one's, and flagged a customised overlay whose Close button sat further down.
TAG_OPEN = re.compile(r"<([A-Za-z][\w.:-]*)")
QUOTED = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'|`[^`]*`")
NOT_TABBABLE = re.compile(r"""\btabIndex\s*=\s*(?:\{\s*-1\s*\}|["']-1["'])""")
# Overlay containers Radix and Base UI focus programmatically when they open (tabIndex -1): the Tab
# order never lands on them, so their `outline-none` removes no keyboard focus indicator. Tabs
# content stays checked, because Radix puts a tab panel in the Tab order.
FOCUS_MANAGED_CONTAINER = re.compile(
    r"^(?:Dialog|AlertDialog|Sheet|Drawer|Popover|DropdownMenu|ContextMenu|Menubar|Menu|Select|"
    r"HoverCard|PreviewCard|Tooltip|NavigationMenu|Combobox)(?:Primitive)?\.?(?:Sub)?(?:Content|Popup)$")
# ^ DialogContent (a composed wrapper), DialogPrimitive.Content (shadcn's Radix import),
#   Popover.Popup (Base UI's own namespace import), DropdownMenuPrimitive.SubContent.


def _opening_tag(content, offset):
    """(tag name, tag text) of the JSX opening tag holding `offset`, or None."""
    start = content.rfind("<", 0, offset)
    while start != -1 and not TAG_OPEN.match(content, start):
        start = content.rfind("<", 0, start)
    if start == -1:
        return None
    end = scan_until(content, start + 1, ">")
    return (TAG_OPEN.match(content, start).group(1), content[start:end]) if end > offset else None


def _declaration_block(content, offset):
    """The short `{...}` block holding `offset` (a CSS rule, an inline style object), or None."""
    open_at, close_at = content.rfind("{", 0, offset), content.find("}", offset)
    if open_at == -1 or close_at == -1 or "}" in content[open_at:offset]:
        return None
    block = content[open_at:close_at + 1]
    return block if block.count("\n") <= 12 else None


def _focus_unit(content, offset):
    """(tag name or None, text) an outline removal is judged in: its opening tag, its class
    string, its declaration block, else its line."""
    tag = _opening_tag(content, offset)
    if tag:
        return tag
    start = content.rfind("\n", 0, offset) + 1
    end = content.find("\n", offset)
    end = len(content) if end == -1 else end
    string = next((m.group() for m in QUOTED.finditer(content, start, end)
                   if m.start() <= offset < m.end()), None)
    return None, string or _declaration_block(content, offset) or content[start:end]


def check_focus_indicator_removed(content):
    """Flag a removed focus indicator only when nothing visible replaces it on the same element
    and that element can take keyboard focus. One warning is enough."""
    for match in FOCUS_REMOVED.finditer(content):
        name, unit = _focus_unit(content, match.start())
        if FOCUS_REPLACEMENT.search(unit) or NOT_TABBABLE.search(unit):
            continue
        if name and FOCUS_MANAGED_CONTAINER.match(name):
            continue
        line = content.count("\n", 0, match.start()) + 1
        return [f"WARNING: Focus indicator removed (line {line}) with no visible replacement on "
                f"the same element. Keyboard users lose all focus feedback. Add a ring "
                f"(e.g. `focus-visible:ring-2 focus-visible:ring-offset-2`) per the "
                f"`std-accessibility` skill."]
    return []


def check_aria_hidden_interactive(content):
    """Check for aria-hidden='true' on an element with onClick, in either attribute order."""
    for hidden in ARIA_HIDDEN_TRUE.finditer(content):
        start = content.rfind("<", 0, hidden.start())
        end = scan_until(content, start + 1, ">") if start != -1 else -1
        if end > hidden.start() and ON_CLICK.search(content, start, end):
            return [
                "WARNING: Interactive element hidden from assistive technology "
                "(aria-hidden=\"true\" with onClick) per the `std-accessibility` skill."
            ]
    return []


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in ALLOWED_EXTENSIONS:
        return []

    # Skip React Native — these a11y rules are for browser React (Vite/Next)
    if hooklib.is_react_native(file_path):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = check_non_semantic_clickable(content)
    # CLI-owned shadcn primitives take their alt text, label and focus styling from the call site.
    if not vendored.is_vendored_ui(file_path):
        rest_names = set(REST_PARAMETER.findall(content))
        warnings += check_missing_alt_text(content, rest_names)
        warnings += check_input_without_label(content, rest_names)
        warnings += check_focus_indicator_removed(content)
    warnings += check_aria_hidden_interactive(content)

    # Deduplicate similar warnings, keeping first-seen order
    return list(dict.fromkeys(warnings))


if __name__ == "__main__":
    hooklib.run_post_checker(check)
