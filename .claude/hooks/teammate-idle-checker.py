#!/usr/bin/env python3
"""
TeammateIdle hook: Validate teammate completed meaningful work.

Checks that an idle teammate has actually produced deliverables rather than
only performing research. Verifies uncommitted changes exist if code was
modified, and reminds about test coverage for modified source files.

Exit codes:
  0 — teammate may idle (quality gates passed)
  2 — send feedback to keep teammate working (gates failed)
"""
import json
import os
import subprocess
import sys


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".tf")
TEST_PATTERNS = ("_test.", "_spec.", ".test.", ".spec.")


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
    """Get files modified in the working tree (staged + unstaged)."""
    diff_output = run_git(["diff", "--name-only", "HEAD"])
    staged_output = run_git(["diff", "--name-only", "--cached"])
    files = set()
    for line in (diff_output + "\n" + staged_output).splitlines():
        line = line.strip()
        if line:
            files.add(line)
    return files


def is_source_file(path):
    _, ext = os.path.splitext(path)
    return ext in SOURCE_EXTENSIONS


def has_test_file(source_path, all_files):
    """Check if a source file has a corresponding test file in the diff."""
    base = os.path.splitext(os.path.basename(source_path))[0]
    for f in all_files:
        fname = os.path.basename(f)
        if base in fname and any(p in fname for p in TEST_PATTERNS):
            return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    agent_name = data.get("agent_name", "teammate")
    task_description = data.get("task_description", "")

    modified_files = get_modified_files()
    source_files = [f for f in modified_files if is_source_file(f)]

    feedback = []

    # Gate 1: If the task implies code changes but none were made, flag it
    code_keywords = ("implement", "build", "create", "add", "fix", "refactor", "update")
    task_implies_code = any(kw in task_description.lower() for kw in code_keywords)

    if task_implies_code and not source_files:
        feedback.append(
            f"Task appears to require code changes but no source files were modified. "
            f"Please implement the changes before going idle."
        )

    # Gate 2: If source files were modified, check for test coverage
    if source_files:
        untested = []
        for sf in source_files:
            # Skip test files themselves
            if any(p in sf for p in TEST_PATTERNS):
                continue
            if not has_test_file(sf, modified_files):
                untested.append(sf)

        if untested:
            files_str = ", ".join(untested[:5])
            if len(untested) > 5:
                files_str += f" (+{len(untested) - 5} more)"
            feedback.append(
                f"Modified source files lack corresponding test changes: {files_str}. "
                f"Consider adding or updating tests."
            )

    if feedback:
        print(f"Quality gate feedback for {agent_name}:")
        for item in feedback:
            print(f"  - {item}")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
