#!/usr/bin/env python3
"""PreToolUse hook: Security scanner for file edits.
Blocks writes to protected files and detects hardcoded secrets."""

import json
import sys
import re

def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool not in ("Edit", "Write"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "") or tool_input.get("new_string", "")

    # Protected paths
    protected_patterns = [
        ".env", ".env.local", ".env.production",
        "secrets/", "credentials/", "private/",
        ".github/workflows/", ".gitlab-ci.yml",
        "production.config", "deploy.config",
        "id_rsa", "id_ed25519"
    ]

    for pattern in protected_patterns:
        if pattern in file_path.replace("\\", "/"):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason":
                        f"BLOCKED: '{file_path}' is a protected file. "
                        f"Matched pattern: '{pattern}'. "
                        "Modify protected files manually outside Claude Code."
                }
            }))
            sys.exit(0)

    # Secret detection patterns
    secret_patterns = [
        (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}', "API Key"),
        (r'(?:secret|password|passwd|pwd)\s*[:=]\s*["\'][^"\']{8,}', "Password/Secret"),
        (r'(?:token|auth_token|access_token)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{20,}', "Auth Token"),
        (r'(?:aws_access_key_id)\s*[:=]\s*["\']?AKIA[A-Z0-9]{16}', "AWS Access Key"),
        (r'(?:aws_secret_access_key)\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}', "AWS Secret Key"),
        (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private Key"),
        (r'(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}', "GitHub Token"),
        (r'sk-[A-Za-z0-9]{48,}', "OpenAI/Stripe Secret Key"),
        (r'xox[baprs]-[A-Za-z0-9\-]+', "Slack Token"),
    ]

    if content:
        for pattern, secret_type in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason":
                            f"BLOCKED: Potential {secret_type} detected in content "
                            f"being written to '{file_path}'. "
                            "Use environment variables or a secrets manager instead."
                    }
                }))
                sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
