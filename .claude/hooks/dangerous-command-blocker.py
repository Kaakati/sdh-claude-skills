#!/usr/bin/env python3
"""PreToolUse hook: Dangerous command blocker.
Blocks destructive commands, network exfiltration, and privilege escalation."""

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

    # Destructive command patterns
    destructive_patterns = [
        (r'rm\s+-rf\s+/', "Recursive delete from root"),
        (r'rm\s+-rf\s+\*', "Recursive wildcard delete"),
        (r'rm\s+-rf\s+~', "Recursive home directory delete"),
        (r'mkfs\b', "Filesystem format"),
        (r'dd\s+if=.*of=/dev/', "Direct disk write"),
        (r':>\s*/', "File truncation from root"),
        (r'>\s*/dev/sd', "Direct device write"),
    ]

    # Database destructive patterns
    db_destructive = [
        (r'DROP\s+(DATABASE|TABLE|SCHEMA)\b', "Database/table drop"),
        (r'TRUNCATE\s+TABLE\b', "Table truncation"),
        (r'DELETE\s+FROM\s+\w+\s*;?\s*$', "Unfiltered DELETE (no WHERE)"),
        (r'ALTER\s+TABLE\s+\w+\s+DROP\s+COLUMN', "Column drop"),
    ]

    # Privilege escalation
    privilege_patterns = [
        (r'\bsudo\s+rm\b', "Sudo delete"),
        (r'chmod\s+777\b', "World-writable permissions"),
        (r'chmod\s+-R\s+777\b', "Recursive world-writable permissions"),
        (r'chown\s+-R\s+root\b', "Recursive root ownership change"),
    ]

    # Network exfiltration
    exfil_patterns = [
        (r'curl\s+.*-X\s*POST\s+https?://(?!localhost|127\.0\.0\.1)', "POST to external URL"),
        (r'wget\s+.*--post', "wget POST to external"),
        (r'nc\s+-l', "Netcat listener"),
        (r'ncat\b.*-e\b', "Ncat with execution"),
    ]

    all_patterns = (
        [(p, d, "DESTRUCTIVE") for p, d in destructive_patterns] +
        [(p, d, "DATABASE") for p, d in db_destructive] +
        [(p, d, "PRIVILEGE") for p, d in privilege_patterns] +
        [(p, d, "NETWORK") for p, d in exfil_patterns]
    )

    for pattern, description, category in all_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason":
                        f"BLOCKED [{category}]: {description}. "
                        f"Command: '{command[:100]}...'. "
                        "This action requires manual execution outside Claude Code."
                }
            }))
            sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
