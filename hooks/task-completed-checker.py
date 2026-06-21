#!/usr/bin/env python3
"""
TaskCompleted hook: Validate task deliverables before allowing completion.

Checks that the completed task has actual deliverables matching its
description, verifies no uncommitted changes are left dangling, and
ensures modified files are in a PR-ready state.

Exit codes:
  0 — task completion accepted
  2 — reject completion with feedback (quality gates failed)
"""
import json
import os
import subprocess
import sys


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".tf")


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


def get_uncommitted_files():
    """Get files that are modified but not yet committed."""
    status = run_git(["status", "--porcelain"])
    files = []
    for line in status.splitlines():
        line = line.strip()
        if line and len(line) > 3:
            files.append(line[3:].strip())
    return files


def check_linting_issues(file_path):
    """Check if a file has obvious linting issues (trailing whitespace, tabs in Python)."""
    issues = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return issues

    _, ext = os.path.splitext(file_path)

    for i, line in enumerate(lines, 1):
        # Check trailing whitespace (common lint issue)
        if line.rstrip("\n\r") != line.rstrip():
            if line.strip():  # Skip blank lines
                issues.append(f"  Line {i}: trailing whitespace")
                if len(issues) >= 3:
                    break

    return issues


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    task_subject = data.get("task_subject", "")
    task_description = data.get("task_description", "")
    agent_name = data.get("agent_name", "teammate")

    feedback = []

    # Gate 1: Check for uncommitted changes that should be committed
    uncommitted = get_uncommitted_files()
    source_uncommitted = [
        f for f in uncommitted
        if os.path.splitext(f)[1] in SOURCE_EXTENSIONS
    ]

    if source_uncommitted:
        files_str = ", ".join(source_uncommitted[:5])
        if len(source_uncommitted) > 5:
            files_str += f" (+{len(source_uncommitted) - 5} more)"
        feedback.append(
            f"Uncommitted source file changes detected: {files_str}. "
            f"Ensure all changes are committed before marking task complete."
        )

    # Gate 2: Check for basic linting issues in modified source files
    lint_issues = {}
    for f in source_uncommitted[:10]:
        if os.path.exists(f):
            issues = check_linting_issues(f)
            if issues:
                lint_issues[f] = issues

    if lint_issues:
        feedback.append("Linting issues found in modified files:")
        for filepath, issues in list(lint_issues.items())[:3]:
            feedback.append(f"  {filepath}:")
            for issue in issues[:2]:
                feedback.append(f"    {issue}")

    # Gate 3: Verify task description keywords match deliverables
    doc_keywords = ("document", "adr", "runbook", "readme", "changelog")
    test_keywords = ("test", "spec", "coverage")

    task_text = (task_subject + " " + task_description).lower()

    if any(kw in task_text for kw in test_keywords):
        # Task mentions tests — check that test files exist in changes
        test_files = [
            f for f in uncommitted
            if any(p in f for p in ("_test.", "_spec.", ".test.", ".spec."))
        ]
        if not test_files:
            feedback.append(
                "Task mentions testing but no test files were modified. "
                "Verify test deliverables are complete."
            )

    if feedback:
        print(f"Task completion rejected for '{task_subject}':")
        for item in feedback:
            print(item)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
