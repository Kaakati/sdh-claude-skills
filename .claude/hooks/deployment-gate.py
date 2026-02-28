#!/usr/bin/env python3
"""
PreToolUse hook: Deployment gate.

Detects deployment commands targeting production or protected branches
and requires explicit confirmation before allowing execution.

Monitored commands:
- git push to main/master/develop
- aws ecs, vercel deploy, terraform apply
- docker push to production registries

Exit codes:
  0 = allow (not a deployment command, or informational warning)
"""
import json
import sys
import re


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    warnings = []

    # Git push to protected branches
    protected_branch_push = re.search(
        r'git\s+push\s+.*\b(main|master|develop)\b', command
    )
    if protected_branch_push:
        branch = protected_branch_push.group(1)
        warnings.append(
            f"Pushing to protected branch '{branch}'. "
            "Verify CI has passed and PR was approved per git-workflow.md."
        )

    # Force push detection
    if re.search(r'git\s+push\s+.*(-f|--force)\b', command):
        warnings.append(
            "Force push detected. This can overwrite remote history. "
            "Force pushes to protected branches are prohibited per git-workflow.md."
        )

    # AWS ECS deployments
    if re.search(r'aws\s+ecs\s+(update-service|create-service|deploy)', command):
        warnings.append(
            "AWS ECS deployment detected. Verify: "
            "1) Target environment (staging vs production). "
            "2) Health checks are configured. "
            "3) Rollback strategy is ready per infrastructure.md."
        )

    # Vercel deployments
    if re.search(r'vercel\s+(deploy|--prod)', command):
        warnings.append(
            "Vercel deployment detected. Verify: "
            "1) Build passes locally. "
            "2) Environment variables are set. "
            "3) Preview deployment was tested per infrastructure.md."
        )

    # Terraform apply (production changes)
    if re.search(r'terraform\s+apply\b', command):
        warnings.append(
            "Terraform apply detected. Verify: "
            "1) 'terraform plan' output was reviewed. "
            "2) No unexpected resource deletions. "
            "3) State file is locked per infrastructure.md."
        )

    # Docker push to production registries
    if re.search(r'docker\s+push\b', command):
        warnings.append(
            "Docker push detected. Verify: "
            "1) Image was built from tested code. "
            "2) Image tag matches the release version. "
            "3) Vulnerability scan passed."
        )

    if warnings:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    "Deployment gate — confirm before proceeding:\n"
                    + "\n".join(f"- {w}" for w in warnings)
                )
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
