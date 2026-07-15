#!/usr/bin/env python3
"""PreToolUse hook: three-tier command gate for Terraform / OpenTofu.

Sorts every terraform invocation into three tiers (The Governed Agent, Ch. 10 Pattern 3):

  DENY   the never-legitimate — state surgery, force-unlock, destroy, apply -auto-approve
  ASK    the serious-but-real — apply (a human confirms, against a checklist)
  ALLOW  the read-only surface — plan / validate / fmt / output / state list|show (falls through)

FAIL-CLOSED by design: "a gate guarding `apply` that crashes must deny" (Ch. 9).

## Why this exists when permissions already deny some of it

Per the lowest-effective-layer principle (Ch. 11), the read-only surface is allow-listed and the
irreversible subcommands are denied in `permissions` (layer 4) — lower, surer, and impossible to
code wrong. This hook carries only what a tool+target permission pattern *cannot* express:

  * `-auto-approve` is a flag that can appear anywhere in the command, not a prefix
  * the `ask` tier needs a reasoned checklist, which a permission's generic prompt cannot carry

The overlap on destroy/state-surgery is deliberate: those are catastrophic, and catastrophic rules
get several layers (Ch. 20). A plugin cannot ship `permissions`, so if a consumer never copied the
deny floor (see the SessionStart sentinel), this hook is the only thing standing there.

## The honest caveat

Regex over shell strings is defeatable by wrappers, aliases, and indirection. This gate is defense
in depth, not a wall — its real value is catching the *model's* ordinary mistakes deterministically
and cheaply. Adversarial evasion is a different threat model and belongs at the permission layer
and above.
"""

import re

import _hooklib as hooklib

TERRAFORM = re.compile(r"\b(?:terraform|tofu)\b")

# State surgery and force-unlock: never legitimate from an agent.
STATE_SURGERY = re.compile(r"\bstate\s+(?:rm|mv|push|replace-provider)\b")
FORCE_UNLOCK = re.compile(r"\bforce-unlock\b")

# `destroy` as a SUBCOMMAND (`terraform destroy`), NOT the `-destroy` flag.
# `terraform plan -destroy` is a read-only preview of a destroy and must fall through —
# the book's template regexes a bare \bdestroy\b, which denies that legitimate command.
DESTROY_SUBCOMMAND = re.compile(r"\b(?:terraform|tofu)\s+(?:-[^\s]+\s+)*destroy\b")

APPLY = re.compile(r"\b(?:terraform|tofu)\s+(?:-[^\s]+\s+)*apply\b")
AUTO_APPROVE = re.compile(r"--?auto-approve\b")

APPLY_CHECKLIST = (
    "APPLY GATE — confirm before proceeding:\n"
    "- Was `terraform plan` run and the output actually reviewed?\n"
    "- Zero unexpected destroys or replacements in the plan?\n"
    "- Correct workspace / environment directory for this change?\n"
    "- State lock healthy (no stale lock from an interrupted run)?\n"
    "- Is this the intended account/region?"
)


def check(event):
    if hooklib.tool_name(event) != "Bash":
        return
    cmd = hooklib.tool_input(event).get("command", "")
    if not TERRAFORM.search(cmd):
        return

    # --- Tier 1: DENY the never-legitimate ---
    if STATE_SURGERY.search(cmd):
        hooklib.deny(
            "BLOCKED: Terraform state surgery (`state rm/mv/push`) is human-only — it edits the "
            "record of reality without touching reality, and a mistake orphans or destroys live "
            "infrastructure. Run it yourself outside the agent. To restructure safely, prefer "
            "`moved {}` blocks (see the terraform skill's state-move rule)."
        )
        return
    if FORCE_UNLOCK.search(cmd):
        hooklib.deny(
            "BLOCKED: `force-unlock` is human-only. A lock usually means another apply is in "
            "flight; breaking it can corrupt state. Verify no apply is running, then unlock "
            "manually."
        )
        return
    if DESTROY_SUBCOMMAND.search(cmd):
        hooklib.deny(
            "BLOCKED: `terraform destroy` is human-only and irreversible. If you intend to remove "
            "specific resources, remove them from the config and apply the plan instead — that is "
            "reviewable. (`terraform plan -destroy` is allowed: it only previews.)"
        )
        return

    # --- Tier 2: apply — deny the unreviewable, ask for the rest ---
    if APPLY.search(cmd):
        if AUTO_APPROVE.search(cmd):
            hooklib.deny(
                "BLOCKED: `apply -auto-approve` is prohibited — it removes the human from an "
                "irreversible action. Run `terraform plan`, review it, then apply without "
                "-auto-approve so the change is confirmed."
            )
            return
        hooklib.ask(APPLY_CHECKLIST)
        return

    # --- Tier 3: read-only surface (plan / validate / fmt / output / state list|show) ---
    return


if __name__ == "__main__":
    # Fail CLOSED: a gate guarding `apply` that cannot evaluate must deny (Ch. 9).
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="terraform-command-gate")
