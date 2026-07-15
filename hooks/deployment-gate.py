#!/usr/bin/env python3
"""PreToolUse hook: Deployment gate.

Detects deployment commands targeting production or protected branches and
requires explicit confirmation before allowing execution.

Monitored commands:
- git push to main/master/develop
- aws ecs, vercel deploy
- docker push to production registries

Terraform is owned by `terraform-command-gate.py` (a three-tier gate), not this hook.

Emits an 'ask' (confirmation) decision when a deployment command is detected.
Fails open: a bug here must not block unrelated commands."""

import re

import _hooklib as hooklib


def check(event):
    if hooklib.tool_name(event) != "Bash":
        return

    command = hooklib.tool_input(event).get("command", "")
    warnings = []

    protected_branch_push = re.search(r'git\s+push\s+.*\b(main|master|develop)\b', command)
    if protected_branch_push:
        branch = protected_branch_push.group(1)
        warnings.append(
            f"Pushing to protected branch '{branch}'. "
            "Verify CI has passed and PR was approved per git-workflow.md."
        )

    if re.search(r'git\s+push\s+.*(-f|--force)\b', command):
        warnings.append(
            "Force push detected. This can overwrite remote history. "
            "Force pushes to protected branches are prohibited per git-workflow.md."
        )

    if re.search(r'aws\s+ecs\s+(update-service|create-service|deploy)', command):
        warnings.append(
            "AWS ECS deployment detected. Verify: "
            "1) Target environment (staging vs production). "
            "2) Health checks are configured. "
            "3) Rollback strategy is ready per infrastructure.md."
        )

    if re.search(r'vercel\s+(deploy|--prod)', command):
        warnings.append(
            "Vercel deployment detected. Verify: "
            "1) Build passes locally. "
            "2) Environment variables are set. "
            "3) Preview deployment was tested per infrastructure.md."
        )

    # NOTE: Terraform is deliberately NOT handled here. `terraform-command-gate.py` owns the
    # whole terraform surface with a proper three-tier gate (deny state-surgery/destroy/
    # -auto-approve, ask on apply with a checklist, allow the read-only surface). Two hooks
    # both emitting a decision for `terraform apply` meant two prompts for one command —
    # approval fatigue is how you get a human who stops reading (Ch. 20, layer 6) — and on
    # `apply -auto-approve` they disagreed outright (ask vs deny). One concern, one owner.

    if re.search(r'docker\s+push\b', command):
        warnings.append(
            "Docker push detected. Verify: "
            "1) Image was built from tested code. "
            "2) Image tag matches the release version. "
            "3) Vulnerability scan passed."
        )

    if warnings:
        hooklib.ask(
            "Deployment gate — confirm before proceeding:\n"
            + "\n".join(f"- {w}" for w in warnings)
        )


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="deployment-gate")
