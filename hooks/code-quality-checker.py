#!/usr/bin/env python3
"""
PostToolUse hook: Code quality checker.

Checks source files for function/file length limits, parameter counts,
and nesting depth per code-standards.md. Exits silently for non-source files.
"""
import os
import re

import _hooklib as hooklib


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")

# Domain-aware file limits (canonical framework-internal dirs, wrapper-agnostic)
MODEL_DIR = "app/models"
COMPONENT_DIRS = (
    "src/components", "src/screens", "src/pages",
    "app/components", "app/views",
)
COMPONENT_EXTENSIONS = (".tsx", ".jsx")
MODEL_LIMIT = 200
COMPONENT_LIMIT = 200
DEFAULT_LIMIT = 300

MAX_FUNCTION_LINES = 30
MAX_PARAMS = 4
MAX_NESTING = 3


def is_component(file_path, ext):
    # Canonical component dirs anywhere, OR a Next app-router .tsx/.jsx under app/.
    return hooklib.under_any(file_path, COMPONENT_DIRS) or (
        ext in COMPONENT_EXTENSIONS and hooklib.under(file_path, "app")
    )


def get_line_limit(file_path, ext):
    if hooklib.under(file_path, MODEL_DIR):
        return MODEL_LIMIT
    if is_component(file_path, ext):
        return COMPONENT_LIMIT
    return DEFAULT_LIMIT


def check_file_length(content, limit):
    lines = content.splitlines()
    if len(lines) > limit:
        return (
            f"WARNING: File exceeds {limit}-line limit "
            f"(currently {len(lines)} lines). Consider splitting responsibilities."
        )
    return None


def check_function_length(content, ext):
    warnings = []
    if ext == ".rb":
        pattern = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)
        end_pattern = re.compile(r"^\s*end\b", re.MULTILINE)
    elif ext == ".py":
        pattern = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)
        end_pattern = None  # Python uses indentation
    else:
        # JS/TS: function declarations and arrow functions
        pattern = re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()",
            re.MULTILINE,
        )
        end_pattern = None

    lines = content.splitlines()

    if ext == ".rb":
        i = 0
        while i < len(lines):
            m = pattern.match(lines[i])
            if m:
                name = m.group(1)
                start = i
                depth = 1
                i += 1
                while i < len(lines) and depth > 0:
                    if re.match(r"\s*def\s", lines[i]) or re.match(
                        r"\s*(?:class|module|if|unless|while|until|for|case|begin|do)\b",
                        lines[i],
                    ):
                        depth += 1
                    if end_pattern.match(lines[i]):
                        depth -= 1
                    i += 1
                func_lines = i - start
                if func_lines > MAX_FUNCTION_LINES:
                    warnings.append(
                        f"WARNING: Function '{name}' exceeds {MAX_FUNCTION_LINES}-line "
                        f"limit (currently {func_lines} lines). Consider decomposing."
                    )
            else:
                i += 1
    elif ext == ".py":
        for m in pattern.finditer(content):
            name = m.group(1)
            start_pos = m.start()
            start_line = content[:start_pos].count("\n")
            # Find indentation of def
            def_line = lines[start_line]
            def_indent = len(def_line) - len(def_line.lstrip())
            end_line = start_line + 1
            while end_line < len(lines):
                line = lines[end_line]
                if line.strip() and (len(line) - len(line.lstrip())) <= def_indent:
                    break
                end_line += 1
            func_lines = end_line - start_line
            if func_lines > MAX_FUNCTION_LINES:
                warnings.append(
                    f"WARNING: Function '{name}' exceeds {MAX_FUNCTION_LINES}-line "
                    f"limit (currently {func_lines} lines). Consider decomposing."
                )
    else:
        # JS/TS: use brace counting
        for m in pattern.finditer(content):
            name = m.group(1) or m.group(2)
            start_pos = m.start()
            start_line = content[:start_pos].count("\n")
            # Find opening brace
            brace_pos = content.find("{", m.end())
            if brace_pos == -1:
                continue
            depth = 1
            pos = brace_pos + 1
            while pos < len(content) and depth > 0:
                if content[pos] == "{":
                    depth += 1
                elif content[pos] == "}":
                    depth -= 1
                pos += 1
            end_line = content[:pos].count("\n")
            func_lines = end_line - start_line + 1
            if func_lines > MAX_FUNCTION_LINES:
                warnings.append(
                    f"WARNING: Function '{name}' exceeds {MAX_FUNCTION_LINES}-line "
                    f"limit (currently {func_lines} lines). Consider decomposing."
                )

    return warnings


def check_param_count(content, ext):
    warnings = []
    if ext == ".rb":
        pattern = re.compile(r"def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
    elif ext == ".py":
        pattern = re.compile(r"def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
    else:
        pattern = re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?)\(([^)]*)\)",
            re.MULTILINE,
        )

    for m in pattern.finditer(content):
        if ext in (".rb", ".py"):
            name = m.group(1)
            params_str = m.group(2)
        else:
            name = m.group(1) or m.group(2)
            params_str = m.group(3)

        if not params_str or not params_str.strip():
            continue

        # Count params (split by comma, ignore defaults)
        params = [p.strip() for p in params_str.split(",") if p.strip()]
        # For Python, exclude 'self' and 'cls'
        if ext == ".py":
            params = [p for p in params if p not in ("self", "cls")]

        if len(params) > MAX_PARAMS:
            warnings.append(
                f"WARNING: Function '{name}' has {len(params)} parameters "
                f"(max {MAX_PARAMS}). Use an options/config object."
            )

    return warnings


def check_nesting_depth(content, ext):
    if ext == ".py":
        # Python: count indentation levels
        max_depth = 0
        for line in content.splitlines():
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            # Assume 4-space indent
            depth = indent // 4
            max_depth = max(max_depth, depth)
        # Subtract 1 for class/function definition level
        effective = max_depth - 1
        if effective > MAX_NESTING:
            return (
                f"WARNING: Nesting depth exceeds {MAX_NESTING} levels. "
                "Use early returns or extract helper functions."
            )
    else:
        # Brace-based languages and Ruby
        max_depth = 0
        depth = 0
        for char in content:
            if char == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == "}":
                depth -= 1
        # Subtract 1 for function/class scope
        effective = max_depth - 1
        if effective > MAX_NESTING:
            return (
                f"WARNING: Nesting depth exceeds {MAX_NESTING} levels. "
                "Use early returns or extract helper functions."
            )
    return None


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []

    limit = get_line_limit(file_path, ext)
    w = check_file_length(content, limit)
    if w:
        warnings.append(w)

    warnings.extend(check_function_length(content, ext))
    warnings.extend(check_param_count(content, ext))

    w = check_nesting_depth(content, ext)
    if w:
        warnings.append(w)

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
