#!/usr/bin/env python3
"""PreToolUse hook: Git commit validator.
Enforces conventional commits, blocks force pushes to protected branches."""

import json
import sys
import re

def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # Block force pushes to protected branches
    force_push_pattern = r'git\s+push\s+.*(-f|--force).*\s+(main|master|develop|release)'
    if re.search(force_push_pattern, command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason":
                    "BLOCKED: Force push to protected branch detected. "
                    "Force pushing to main/master/develop/release is prohibited."
            }
        }))
        sys.exit(0)

    # Validate conventional commit messages
    commit_match = re.search(r'git\s+commit\s+.*-m\s+["\'](.+?)["\']', command)
    if commit_match:
        message = commit_match.group(1)
        conventional_pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+?\))?!?:\s.+'
        if not re.match(conventional_pattern, message):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason":
                        f"BLOCKED: Commit message does not follow conventional format. "
                        f"Got: '{message}'. "
                        "Expected: <type>(<scope>): <description> where type is one of: "
                        "feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
                }
            }))
            sys.exit(0)

    # Block direct pushes to protected branches without PR
    direct_push = re.search(r'git\s+push\s+(?:origin\s+)?(main|master|develop)\s*$', command)
    if direct_push:
        branch = direct_push.group(1)
        # Allow if it looks like a PR merge (trust the developer's judgment here)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason":
                    f"WARNING: Direct push to '{branch}' detected. "
                    "Consider using a pull request instead. Allow this push?"
            }
        }))
        sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
