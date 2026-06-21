#!/usr/bin/env python3
"""PreToolUse hook: Security scanner for file edits.

Blocks writes to protected files and detects hardcoded secrets. Fails closed:
if the scan errors, the write is denied rather than silently allowed."""

import re

import _hooklib as hooklib

PROTECTED_PATTERNS = [
    ".env", ".env.local", ".env.production",
    "secrets/", "credentials/", "private/",
    ".github/workflows/", ".gitlab-ci.yml",
    "production.config", "deploy.config",
    "id_rsa", "id_ed25519",
]

SECRET_PATTERNS = [
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


def check(event):
    if hooklib.tool_name(event) not in ("Edit", "Write"):
        return

    file_path = hooklib.get_file_path(event)
    content = hooklib.get_content(event)

    normalized = hooklib.normalize(file_path)
    for pattern in PROTECTED_PATTERNS:
        if pattern in normalized:
            hooklib.deny(
                f"BLOCKED: '{file_path}' is a protected file. "
                f"Matched pattern: '{pattern}'. "
                "Modify protected files manually outside Claude Code."
            )
            return

    if content:
        for pattern, secret_type in SECRET_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                hooklib.deny(
                    f"BLOCKED: Potential {secret_type} detected in content "
                    f"being written to '{file_path}'. "
                    "Use environment variables or a secrets manager instead."
                )
                return


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="security-scan")
