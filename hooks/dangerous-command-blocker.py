#!/usr/bin/env python3
"""PreToolUse hook: Dangerous command blocker.

Blocks destructive commands, network exfiltration, and privilege escalation.
Fails closed: if the check itself errors, the command is denied rather than
silently allowed (a safety gate that cannot evaluate must not pass)."""

import re

import _hooklib as hooklib

# (pattern, description) grouped by category.
_DESTRUCTIVE = [
    (r'rm\s+-rf\s+/', "Recursive delete from root"),
    (r'rm\s+-rf\s+\*', "Recursive wildcard delete"),
    (r'rm\s+-rf\s+~', "Recursive home directory delete"),
    (r'mkfs\b', "Filesystem format"),
    (r'dd\s+if=.*of=/dev/', "Direct disk write"),
    (r':>\s*/', "File truncation from root"),
    (r'>\s*/dev/sd', "Direct device write"),
]

_DB_DESTRUCTIVE = [
    (r'DROP\s+(DATABASE|TABLE|SCHEMA)\b', "Database/table drop"),
    (r'TRUNCATE\s+TABLE\b', "Table truncation"),
    (r'DELETE\s+FROM\s+\w+\s*;?\s*$', "Unfiltered DELETE (no WHERE)"),
    (r'ALTER\s+TABLE\s+\w+\s+DROP\s+COLUMN', "Column drop"),
]

_PRIVILEGE = [
    (r'\bsudo\s+rm\b', "Sudo delete"),
    (r'chmod\s+777\b', "World-writable permissions"),
    (r'chmod\s+-R\s+777\b', "Recursive world-writable permissions"),
    (r'chown\s+-R\s+root\b', "Recursive root ownership change"),
]

_EXFIL = [
    (r'curl\s+.*-X\s*POST\s+https?://(?!localhost|127\.0\.0\.1)', "POST to external URL"),
    (r'wget\s+.*--post', "wget POST to external"),
    (r'nc\s+-l', "Netcat listener"),
    (r'ncat\b.*-e\b', "Ncat with execution"),
]

ALL_PATTERNS = (
    [(p, d, "DESTRUCTIVE") for p, d in _DESTRUCTIVE]
    + [(p, d, "DATABASE") for p, d in _DB_DESTRUCTIVE]
    + [(p, d, "PRIVILEGE") for p, d in _PRIVILEGE]
    + [(p, d, "NETWORK") for p, d in _EXFIL]
)


def check(event):
    if hooklib.tool_name(event) != "Bash":
        return
    command = hooklib.tool_input(event).get("command", "")
    for pattern, description, category in ALL_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            hooklib.deny(
                f"BLOCKED [{category}]: {description}. (Rule: the `std-security` skill.) "
                f"Command: '{command[:100]}...'. "
                "This action requires manual execution outside Claude Code."
            )
            return


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="dangerous-command")
