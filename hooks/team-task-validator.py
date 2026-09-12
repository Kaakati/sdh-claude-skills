#!/usr/bin/env python3
"""
TaskCompleted hook: files the task changed must be free of leftover debug statements and basic
formatting faults before the task closes.

Same event and contract as task-completed-checker.py (exit 2, reason on stderr), and the same
shared helpers in `_teamgate.py`: git state in the event cwd (repo-root-relative paths joined to
the repo root, so a session launched from a monorepo package no longer checks nothing, and
untracked files count), plus the attribution that limits this gate to files the TASK touched (a
teammate's own worktree, or changes since the task's TaskCreated baseline). With no attribution it
stays quiet: rejecting a completion over someone else's work in progress names a remedy the
completing agent must not carry out.

Checks per file:
  - trailing whitespace, missing final newline, mixed tab/space indentation;
  - debug statements matched as STATEMENTS: outside comments (//, /* */, JSDoc, #, =begin, Python
    docstrings) and string literals, and never in tests, scripts, bin/ or *.config.* files, where
    console output is the point. `config.debugger_enabled = false` is not a debugger statement.
"""
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS_DIR)
import _hooklib as hooklib  # noqa: E402
import _teamgate as teamgate  # noqa: E402

LANGUAGE = {".ts": "js", ".tsx": "js", ".js": "js", ".jsx": "js", ".rb": "rb", ".py": "py"}
FORMAT_ONLY = (".tf",)
DEBUG_PATTERNS = {
    "js": (re.compile(r"\bconsole\.log\s*\("), re.compile(r"(?:^|[;{}])\s*debugger\s*(?:;|$)")),
    "rb": (re.compile(r"\bbinding\.(?:pry|irb)\b"),
           re.compile(r"(?:^|;)\s*(?:byebug|debugger)\s*(?:;|$)")),
    "py": (re.compile(r"\bbreakpoint\s*\(\s*\)"), re.compile(r"\bi?pdb\.set_trace\s*\("),
           re.compile(r"^\s*(?:import\s+i?pdb\b|from\s+i?pdb\s+import\b)")),
}
SCRIPT_LIKE = re.compile(r"(^|/)(scripts?|bin)/|\.config\.[cm]?[jt]s$")
STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`')
LINE_COMMENT_JS = re.compile(r"(^|[\s;{}(),])//.*$")
LINE_COMMENT_HASH = re.compile(r"(^|\s)#.*$")


def strip_js(line, in_block):
    """JS/TS code on this line with string literals, // comments and /* */ blocks removed."""
    if in_block:
        if "*/" not in line:
            return "", True
        line = line.split("*/", 1)[1]
    line = LINE_COMMENT_JS.sub(r"\1", STRING_LITERAL.sub('""', line))
    line = re.sub(r"/\*.*?\*/", " ", line)
    if "/*" in line:
        return line.split("/*", 1)[0], True
    return line, False


def strip_comments(line, lang, in_block):
    """(code, still inside a block comment or docstring) for one line."""
    if lang == "js":
        return strip_js(line, in_block)
    if lang == "py" and (in_block or '"""' in line or "'''" in line):
        toggles = line.count('"""') + line.count("'''")
        return "", in_block != (toggles % 2 == 1)
    if lang == "rb" and (in_block or line.startswith("=begin")):
        return "", not line.startswith("=end")
    return LINE_COMMENT_HASH.sub(r"\1", STRING_LITERAL.sub('""', line)), False


def debug_issues(lines, lang):
    issues, in_block = [], False
    for number, line in enumerate(lines, 1):
        code, in_block = strip_comments(line, lang, in_block)
        if code.strip() and any(p.search(code) for p in DEBUG_PATTERNS[lang]):
            issues.append(f"debug statement at line {number}: {line.strip()[:60]}")
    return issues[:3]


def format_issues(content, lines):
    issues = []
    if not content.endswith("\n"):
        issues.append("missing trailing newline")
    indented = [line for line in lines if line.strip()]
    if any(l.startswith("\t") for l in indented) and any(l.startswith("  ") for l in indented):
        issues.append("mixed indentation (tabs and spaces)")
    trailing = [n for n, line in enumerate(lines, 1) if line.strip() and line != line.rstrip()]
    if trailing:
        more = f" (+{len(trailing) - 1} more)" if len(trailing) > 1 else ""
        issues.append(f"trailing whitespace at line {trailing[0]}{more}")
    return issues


def check_file_quality(top, path):
    """Issues for one repo-root-relative path; [] for a deleted or empty file."""
    content = hooklib.read_file(os.path.join(top, path))
    if not content:
        return []
    lines = content.splitlines()
    issues = format_issues(content, lines)
    lang = LANGUAGE.get(os.path.splitext(path)[1])
    if lang and not teamgate.is_test_file(path) and not SCRIPT_LIKE.search(path):
        issues += debug_issues(lines, lang)
    return issues


def report(found):
    lines = ["Code quality issues found in files this task changed:"]
    for path, issues in list(found.items())[:5]:
        lines.append(f"  {path}:")
        lines.extend(f"    - {issue}" for issue in issues[:3])
    lines.append("")
    lines.append("Fix these before marking the task complete: remove debug statements (log through "
                 "the logger, per the `std-code-standards` skill) and run the formatter (rubocop, "
                 "prettier, ruff format, terraform fmt; the `toolchain` skill).")
    return lines


def main():
    data = hooklib.load_event()
    if not isinstance(data, dict) or not data:
        sys.exit(0)
    repo = teamgate.repo_state(str(data.get("cwd") or os.getcwd()))
    scope = teamgate.touched_scope(repo, data) if repo else None
    if not scope:
        sys.exit(0)
    checked = sorted(p for p in scope if p.endswith(tuple(LANGUAGE) + FORMAT_ONLY))
    found = {path: issues for path in checked
             for issues in [check_file_quality(repo["top"], path)] if issues}
    if found:
        teamgate.block(data, "team-task-validator", report(found))
    sys.exit(0)


if __name__ == "__main__":
    main()
