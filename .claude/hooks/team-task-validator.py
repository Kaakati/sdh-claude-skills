#!/usr/bin/env python3
"""
TaskCompleted hook: Validate modified files pass linting/formatting.

Checks that files modified by a teammate pass basic quality checks
before allowing task completion. Runs lightweight checks inline and
reminds about formatter tools for violations.

Exit codes:
  0 — validation passed
  2 — reject completion with feedback (quality issues found)
"""
import json
import os
import subprocess
import sys


SOURCE_EXTENSIONS = {
    ".rb": "ruby",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".tf": "terraform",
}


def run_git(args):
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def get_modified_files():
    """Get files modified in the working tree (staged + unstaged + untracked)."""
    diff_output = run_git(["diff", "--name-only", "HEAD"])
    staged_output = run_git(["diff", "--name-only", "--cached"])
    files = set()
    for line in (diff_output + "\n" + staged_output).splitlines():
        line = line.strip()
        if line:
            files.add(line)
    return files


def check_file_quality(file_path):
    """Run basic quality checks on a file."""
    issues = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = content.splitlines()
    except (OSError, IOError):
        return issues

    _, ext = os.path.splitext(file_path)
    lang = SOURCE_EXTENSIONS.get(ext, "")

    # Check 1: File ends with newline
    if content and not content.endswith("\n"):
        issues.append("missing trailing newline")

    # Check 2: No mixed indentation (tabs + spaces in same file)
    has_tabs = any(line.startswith("\t") for line in lines if line.strip())
    has_spaces = any(
        line.startswith("  ") for line in lines if line.strip()
    )
    if has_tabs and has_spaces:
        issues.append("mixed indentation (tabs and spaces)")

    # Check 3: No debug statements left behind
    debug_patterns = {
        "ruby": ["binding.pry", "binding.irb", "byebug", "debugger"],
        "python": ["import pdb", "pdb.set_trace()", "breakpoint()"],
        "typescript": ["console.log(", "debugger;"],
        "javascript": ["console.log(", "debugger;"],
    }

    patterns = debug_patterns.get(lang, [])
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        for pattern in patterns:
            if pattern in stripped:
                issues.append(f"debug statement at line {i}: {pattern}")
                break

    return issues


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    modified_files = get_modified_files()
    source_files = [
        f for f in modified_files
        if os.path.splitext(f)[1] in SOURCE_EXTENSIONS
    ]

    if not source_files:
        sys.exit(0)

    all_issues = {}
    for f in source_files:
        if os.path.exists(f):
            issues = check_file_quality(f)
            if issues:
                all_issues[f] = issues

    if all_issues:
        feedback = ["Code quality issues found in modified files:"]
        for filepath, issues in list(all_issues.items())[:5]:
            feedback.append(f"  {filepath}:")
            for issue in issues[:3]:
                feedback.append(f"    - {issue}")

        feedback.append("")
        feedback.append(
            "Fix these issues before marking the task complete. "
            "Run the appropriate formatter (rubocop, prettier, terraform fmt)."
        )

        print("\n".join(feedback))
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
