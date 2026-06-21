#!/usr/bin/env python3
"""PreToolUse hook: Git commit validator.

Enforces conventional commits and blocks force pushes to protected branches.
Fails open: this is a workflow-convention gate, not a safety gate, so a bug here
must not block every Bash command (run_pre_blocker default)."""

import re

import _hooklib as hooklib

FORCE_PUSH_PATTERN = r'git\s+push\s+.*(-f|--force).*\s+(main|master|develop|release)'
COMMIT_PATTERN = r'git\s+commit\s+.*-m\s+["\'](.+?)["\']'
CONVENTIONAL_PATTERN = (
    r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)'
    r'(\(.+?\))?!?:\s.+'
)
DIRECT_PUSH_PATTERN = r'git\s+push\s+(?:origin\s+)?(main|master|develop)\s*$'


def check(event):
    if hooklib.tool_name(event) != "Bash":
        return
    command = hooklib.tool_input(event).get("command", "")

    if re.search(FORCE_PUSH_PATTERN, command):
        hooklib.deny(
            "BLOCKED: Force push to protected branch detected. "
            "Force pushing to main/master/develop/release is prohibited."
        )
        return

    commit_match = re.search(COMMIT_PATTERN, command)
    if commit_match:
        message = commit_match.group(1)
        if not re.match(CONVENTIONAL_PATTERN, message):
            hooklib.deny(
                "BLOCKED: Commit message does not follow conventional format. "
                f"Got: '{message}'. "
                "Expected: <type>(<scope>): <description> where type is one of: "
                "feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
            )
            return

    direct_push = re.search(DIRECT_PUSH_PATTERN, command)
    if direct_push:
        branch = direct_push.group(1)
        hooklib.ask(
            f"WARNING: Direct push to '{branch}' detected. "
            "Consider using a pull request instead. Allow this push?"
        )
        return


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="pre-commit-check")
