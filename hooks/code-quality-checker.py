#!/usr/bin/env python3
"""
PostToolUse hook: Code quality checker.

Checks source files for function/file length limits, parameter counts,
and nesting depth per the `std-code-standards` skill. Exits silently for non-source files.

Each measure replaced a confirmed false positive or negative. Parameters split on TOP-LEVEL
commas: `Map<string, number>`, `dict[str, int]` and a destructured `{ className, ...props }` (the
options object the remedy asks for) are one each. JS/TS length runs to the end of the BODY, past
the parameters and any return type - not to the destructuring `{`, where every long React
component used to pass. Python uses `ast`: trailing blank lines are not function lines, nesting is
control flow (not continuation lines, not `elif`), a method gets a module function's three levels,
and an unparseable (mid-edit) file gets only its length checked. Offsets map to lines through one
newline index; prefix slicing per match was quadratic and timed the dispatcher out. Vendored
shadcn/ui primitives (components.json `aliases.ui`) are CLI-owned size/style targets and skipped.
"""
import ast
import bisect
import functools
import os
import re

import _hooklib as hooklib
import _vendored as vendored
from _jsx import skip_token


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")
JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

# Domain-aware file limits (canonical framework-internal dirs, wrapper-agnostic)
MODEL_DIR = "app/models"
COMPONENT_DIRS = ("src/components", "src/screens", "src/pages", "app/components", "app/views")
COMPONENT_EXTENSIONS = (".tsx", ".jsx")
MODEL_LIMIT = 200
COMPONENT_LIMIT = 200
DEFAULT_LIMIT = 300

MAX_FUNCTION_LINES = 30
MAX_PARAMS = 4
MAX_NESTING = 3

PY_NESTING = tuple(getattr(ast, name) for name in ("If", "For", "AsyncFor", "While", "Try",
                   "TryStar", "With", "AsyncWith", "Match") if hasattr(ast, name))
PY_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
PY_SCOPES = PY_FUNCTIONS + (ast.ClassDef,)

JS_FUNCTION = re.compile(
    r"\bfunction\s*\*?\s*(\w+)\s*(?:<[^>(]*>\s*)?\("
    r"|\b(?:const|let|var)\s+(\w+)\s*(?::[^=;]+?)?=\s*(?:async\s+)?(?:<[^>(]*>\s*)?\("
)
RB_DEF = re.compile(r"^[ \t]*def\s+(?:self\.)?(\w+[?!=]?)[ \t]*(\()?", re.M)
RB_BLOCK_OPEN = re.compile(r"\s*(?:def|class|module|if|unless|while|until|for|case|begin|do)\b")
RB_END = re.compile(r"\s*end\b")
TOKEN = re.compile(r"//|/\*|[\"'`(){}\[\]]")
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")
BODY_START = re.compile(r"\s*(=>|\{|:)")
ARROW_BODY = re.compile(r"\s*([{(])")
TYPE_STEP = re.compile(r"=>|[{(\[;]")
TYPE_CONTEXT = ":<,|&(=?"


def get_line_limit(file_path, ext):
    if hooklib.under(file_path, MODEL_DIR):
        return MODEL_LIMIT
    # Django keeps a whole app's models in one FILE (`models.py`) the app/models rule never reaches.
    if ext == ".py" and os.path.basename(hooklib.normalize(file_path)) == "models.py":
        return MODEL_LIMIT
    # Canonical component dirs anywhere, OR a Next app-router .tsx/.jsx under app/.
    component = hooklib.under_any(file_path, COMPONENT_DIRS) or (
        ext in COMPONENT_EXTENSIONS and hooklib.under(file_path, "app"))
    return COMPONENT_LIMIT if component else DEFAULT_LIMIT


def check_file_length(content, limit):
    count = len(content.splitlines())
    return (f"WARNING: File exceeds {limit}-line limit (currently {count} lines). "
            "Consider splitting responsibilities.") if count > limit else None


def line_of(content):
    """Offset -> 1-based line in O(log n), from one newline index built per file."""
    starts = [m.end() for m in re.finditer("\n", content)]
    return lambda pos: bisect.bisect_right(starts, pos) + 1


def match_close(src, i):
    """Offset of the bracket closing the one at `i` (strings and comments skipped); -1 if none."""
    depth, pos = 0, i
    while True:
        m = TOKEN.search(src, pos)
        if not m:
            return -1
        tok, pos = m.group(), m.start()
        if tok in ("(", "[", "{"):
            depth += 1
        elif tok in (")", "]", "}"):
            depth -= 1
            if depth == 0:
                return pos
        else:
            pos = skip_token(src, pos)
            continue
        pos += 1


def split_top_level(params):
    """Split on commas at bracket depth 0, so generics, subscripts and destructuring stay whole."""
    parts, depth, start = [], 0, 0
    text = QUOTED.sub('""', params)
    for i, ch in enumerate(text):
        if ch in "([{<":
            depth += 1
        elif ch in ")]}" or (ch == ">" and text[i - 1:i] != "="):
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    return [p.strip() for p in parts + [text[start:]] if p.strip()]


def group_span(src, i):
    end = match_close(src, i)
    return (i, end) if end != -1 else None


def arrow_body(src, pos):
    """A block or parenthesised (JSX) arrow body; an expression body ends where it starts."""
    m = ARROW_BODY.match(src, pos)
    return group_span(src, m.start(1)) if m else (pos, pos)


def body_after_type(src, pos):
    """Skip a return type to the body: `: { a: T } {` and `Promise<{ a: T }>` groups are type."""
    while True:
        m = TYPE_STEP.search(src, pos)
        if not m or m.group() == ";":
            return None  # an overload or `declare` signature has no body
        if m.group() == "=>":
            return arrow_body(src, m.end())
        before = src[max(0, m.start() - 80):m.start()].rstrip()[-1:] if m.group() == "{" else ""
        if m.group() == "{" and before not in TYPE_CONTEXT:
            return group_span(src, m.start())
        end = match_close(src, m.start())
        if end == -1:
            return None
        pos = end + 1


def js_body_span(src, close):
    """(start, end) of the body of the function whose parameter list closes at `close`, or None."""
    m = BODY_START.match(src, close + 1)
    if not m:
        return None  # `const x = (a + b) * c` is a parenthesised expression, not a function
    if m.group(1) == "=>":
        return arrow_body(src, m.end())
    return body_after_type(src, m.end()) if m.group(1) == ":" else group_span(src, m.start(1))


def measure_js(content):
    """(name, lines, params) for JS/TS function declarations and arrow functions."""
    line, found = line_of(content), []
    for m in JS_FUNCTION.finditer(content):
        close = match_close(content, m.end() - 1)
        body = js_body_span(content, close) if close != -1 else None
        if body is not None:
            params = split_top_level(content[m.end():close])
            found.append((m.group(1) or m.group(2), line(body[1]) - line(m.start()) + 1, len(params)))
    return found


def ruby_def_end(lines, start):
    """Index just past the `end` closing the def at `start` (block keywords counted at line start)."""
    depth, i = 1, start + 1
    while i < len(lines) and depth > 0:
        depth += bool(RB_BLOCK_OPEN.match(lines[i])) - bool(RB_END.match(lines[i]))
        i += 1
    return i


def measure_ruby(content):
    """(name, lines, params) for each def; parameters only when parenthesised, as before."""
    lines, line, found = content.splitlines(), line_of(content), []
    for m in RB_DEF.finditer(content):
        start = line(m.start()) - 1
        close = match_close(content, m.end() - 1) if m.group(2) else -1
        params = split_top_level(content[m.end():close]) if close != -1 else []
        found.append((m.group(1), ruby_def_end(lines, start) - start, len(params)))
    return found


def brace_nesting(content):
    """Deepest `{` depth below the enclosing function/class scope; strings and comments skipped."""
    depth = deepest = pos = 0
    while True:
        m = TOKEN.search(content, pos)
        if not m:
            return max(0, deepest - 1)
        tok = m.group()
        if tok in ("{", "}"):
            depth += 1 if tok == "{" else -1
            deepest = max(deepest, depth)
        pos = m.end() if tok in "()[]{}" else skip_token(content, m.start())


def is_elif(parent, child):
    """`elif` parses as an If alone in its parent's orelse, at the parent's own column."""
    return (isinstance(parent, ast.If) and isinstance(child, ast.If) and len(parent.orelse) == 1
            and parent.orelse[0] is child and child.col_offset == parent.col_offset)


def python_nesting(node, depth):
    """Deepest control-flow nesting below `node`. Expressions hold no statements and are skipped."""
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.expr):
            continue
        if isinstance(child, PY_SCOPES):
            deepest = max(deepest, python_nesting(child, 0))
            continue
        nests = isinstance(child, PY_NESTING) and not is_elif(node, child)
        deepest = max(deepest, python_nesting(child, depth + nests))
    return deepest


def measure_python(content):
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return (), 0
    functions = []
    for node in sorted((n for n in ast.walk(tree) if isinstance(n, PY_FUNCTIONS)), key=lambda n: n.lineno):
        args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        params = [a.arg for a in args if a.arg not in ("self", "cls")]
        functions.append((node.name, node.end_lineno - node.lineno + 1, len(params)))
    return tuple(functions), python_nesting(tree, 0)


@functools.lru_cache(maxsize=8)
def measure(content, ext):
    """((name, lines, params), ...) and the deepest nesting - computed once per file content."""
    if ext == ".py":
        return measure_python(content)
    functions = measure_ruby(content) if ext == ".rb" else measure_js(content)
    return tuple(functions), brace_nesting(content)


def check_function_length(content, ext):
    return [f"WARNING: Function '{name}' exceeds {MAX_FUNCTION_LINES}-line limit "
            f"(currently {lines} lines). Consider decomposing."
            for name, lines, _ in measure(content, ext)[0] if lines > MAX_FUNCTION_LINES]


def check_param_count(content, ext):
    return [f"WARNING: Function '{name}' has {params} parameters (max {MAX_PARAMS}). "
            f"Use an options/config object."
            for name, _, params in measure(content, ext)[0] if params > MAX_PARAMS]


def check_nesting_depth(content, ext):
    return (f"WARNING: Nesting depth exceeds {MAX_NESTING} levels. Use early returns or extract "
            "helper functions.") if measure(content, ext)[1] > MAX_NESTING else None


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []
    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS or (ext in JS_EXTENSIONS and vendored.is_vendored_ui(file_path)):
        return []
    content = hooklib.read_file(file_path)
    if not content:
        return []
    warnings = [check_file_length(content, get_line_limit(file_path, ext))]
    warnings.extend(check_function_length(content, ext))
    warnings.extend(check_param_count(content, ext))
    warnings.append(check_nesting_depth(content, ext))
    return [w for w in warnings if w]


if __name__ == "__main__":
    hooklib.run_post_checker(check)
