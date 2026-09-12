#!/usr/bin/env python3
"""
PostToolUse hook: Internationalization (i18n) checker.

Checks .tsx, .jsx, and .erb files for hardcoded user-facing strings
that should use translation keys per the `std-i18n` skill.
Exits silently for non-matching files.

JSX text is found by walking elements, not by grabbing whatever sits between a `>` and a `<`:
the old regex read `{page > 1 && page < pageCount && ...}` as copy, and `&hellip;` too. Each text
node is judged on its own, so one `t(` call no longer exempts a whole file and a half-translated
page is still checked. Text inside <code>, <pre>, <kbd>, <samp>, <script>, <style> and <Trans>
(whose children are the translation's default) is not copy. The warning names the first line.

Vendored shadcn/ui primitives (components.json `aliases.ui`) are skipped: their sr-only defaults
("Close", "Toggle Sidebar") are translated through label props filled from t() at the call site,
per the std-shadcn-ui skill, not by rewriting CLI-owned source line by line.
"""
import os
import re

import _hooklib as hooklib
import _vendored as vendored
from _jsx import scan_until, skip_token


ALLOWED_EXTENSIONS = (".tsx", ".jsx", ".erb")
JSX_EXTENSIONS = (".tsx", ".jsx")
SOURCE_DIRS = ("app/views", "src", "app")
# shadcn's no-src layout keeps blocks and compositions at <package>/components.
JSX_SOURCE_DIRS = SOURCE_DIRS + ("components",)
SKIP_PATTERNS = (".test.", ".spec.", "__tests__", ".config.", ".d.ts", ".stories.")

MESSAGE = ("Use translation keys per the `std-i18n` skill — never hardcode user-facing strings.")
CODE_TOKEN = re.compile(r"//|/\*|[\"'`{}<]")
CHILD_STOP = re.compile(r"[<{]")
TAG_NAME = re.compile(r"<(/?)([A-Za-z][\w.:-]*)?")
TYPE_PARAMETER = re.compile(r"<[A-Za-z][\w.]*\s*(?:,|extends\b)")
ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|\w+);")
LETTER = re.compile(r"[^\W\d_]")
NOT_COPY_TAGS = frozenset({"code", "pre", "kbd", "samp", "script", "style", "Trans"})
JSX_PRECEDERS = "(,=?:&|{}[;>"


def starts_jsx(src, at):
    """`<` opens JSX only before a tag name or `>`, after an operator, `(` or `return`.

    Never `a < b`, `useState<T>()`, or an arrow's type parameters `<T,>` / `<T extends U>`.
    """
    after = src[at + 1:at + 2]
    if not (after.isalpha() or after == ">") or TYPE_PARAMETER.match(src, at):
        return False
    k = at - 1
    while k >= 0 and src[k].isspace():
        k -= 1
    return k < 0 or src[k] in JSX_PRECEDERS or src[max(0, k - 5):k + 1] == "return"


def enter_tag(src, at, stack):
    """Open or close the element whose tag starts at `at`; return the offset after the tag."""
    closing, name = TAG_NAME.match(src, at).groups()
    end = scan_until(src, at + 1, ">")
    if end == -1:
        return len(src)
    if closing and stack[-1].startswith("<"):
        stack.pop()
    elif not closing and src[end - 1] != "/":
        stack.append("<" + (name or ""))
    return end + 1


def scan_children(src, pos, stack, nodes):
    """Record the text up to the next `<` or `{`, then enter that tag or expression."""
    match = CHILD_STOP.search(src, pos)
    end = match.start() if match else len(src)
    if not any(frame[1:] in NOT_COPY_TAGS for frame in stack):
        nodes.append((pos, src[pos:end]))
    if not match:
        return len(src)
    if match.group() == "{":
        stack.append("expr")
        return end + 1
    return enter_tag(src, end, stack)


def scan_code(src, pos, stack):
    """Skip strings and comments, track braces, and enter JSX where `<` can only open an element."""
    match = CODE_TOKEN.search(src, pos)
    if not match:
        return len(src)
    tok, at = match.group(), match.start()
    if tok == "{":
        stack.append("{")
    elif tok == "}":
        if len(stack) > 1:
            stack.pop()  # leaving an `expr` frame drops back into the element's children
    elif tok == "<":
        return enter_tag(src, at, stack) if starts_jsx(src, at) else at + 1
    else:
        return skip_token(src, at)
    return at + 1


def jsx_text_nodes(src):
    """(offset, text) for every JSX text node, walking elements so `a > b` and `=>` stay code."""
    nodes, stack, pos = [], ["js"], 0
    while pos < len(src):
        if stack[-1].startswith("<"):
            pos = scan_children(src, pos, stack, nodes)
        else:
            pos = scan_code(src, pos, stack)
    return nodes


def is_copy(text):
    """Literal text a person reads: letters remain once entities and whitespace are stripped."""
    text = ENTITY.sub(" ", text).strip()
    return len(text) > 1 and bool(LETTER.search(text))


def hardcoded_jsx_text(content):
    """(offset, text) for each JSX text node that is literal copy, in file order."""
    return [(offset, " ".join(ENTITY.sub(" ", raw).split()))
            for offset, raw in jsx_text_nodes(content) if is_copy(raw)]


def check_jsx_hardcoded_strings(content):
    """True when any JSX text node is literal copy."""
    return bool(hardcoded_jsx_text(content))


def check_erb_hardcoded_strings(content):
    """Find plain text in ERB that isn't wrapped in t() or I18n.t()."""
    # Remove ERB tags to find plain text
    stripped = re.sub(r"<%.*?%>", "", content, flags=re.DOTALL)
    # Remove HTML tags and entities (&nbsp; is markup, not a word)
    stripped = ENTITY.sub(" ", re.sub(r"<[^>]+>", " ", stripped))
    # Check remaining text for words (not just whitespace/punctuation)
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    # Filter out HTML-like words
    html_words = {"div", "span", "class", "href", "src", "alt", "type", "id", "br", "hr"}
    meaningful = [w for w in words if w.lower() not in html_words]
    return len(meaningful) > 0


def jsx_warnings(content):
    copy = hardcoded_jsx_text(content)
    if not copy:
        return []
    offset, text = copy[0]
    line = content.count("\n", 0, offset + len(content[offset:]) - len(content[offset:].lstrip())) + 1
    more = f", and {len(copy) - 1} more" if len(copy) > 1 else ""
    sample = text if len(text) <= 40 else text[:37] + "..."
    return [f"WARNING: Hardcoded user-facing string detected (line {line}: \"{sample}\"{more}). {MESSAGE}"]


def erb_warnings(content):
    # ERB keeps the file-level signal: its text scan has no element structure to judge per node.
    if re.search(r"\bt\s*\(|I18n\.t", content) or not check_erb_hardcoded_strings(content):
        return []
    return [f"WARNING: Hardcoded user-facing string detected. {MESSAGE}"]


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in ALLOWED_EXTENSIONS:
        return []

    normalized = hooklib.normalize(file_path)

    # Skip test/config/story files
    if any(p in normalized for p in SKIP_PATTERNS):
        return []

    # Only check files under UI source directories; CLI-owned shadcn primitives are out
    jsx = ext in JSX_EXTENSIONS
    if not hooklib.under_any(file_path, JSX_SOURCE_DIRS if jsx else SOURCE_DIRS):
        return []
    if jsx and vendored.is_vendored_ui(file_path):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    return jsx_warnings(content) if jsx else erb_warnings(content)


if __name__ == "__main__":
    hooklib.run_post_checker(check)
