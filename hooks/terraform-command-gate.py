#!/usr/bin/env python3
"""PreToolUse hook: three-tier command gate for Terraform / OpenTofu.

Sorts every terraform invocation into three tiers (The Governed Agent, Ch. 10 Pattern 3):

  DENY   the never-legitimate — state surgery, force-unlock, destroy (as `destroy` or as
         `apply -destroy`), apply -auto-approve
  ASK    the serious-but-real — apply (a human confirms, against a checklist)
  ALLOW  the read-only surface — plan / validate / fmt / output / state list|show (falls through)

FAIL-CLOSED by design: "a gate guarding `apply` that crashes must deny" (Ch. 9).

## Why this exists when permissions already deny some of it

Per the lowest-effective-layer principle (Ch. 11), the read-only surface is allow-listed and the
irreversible subcommands are denied in `permissions` (layer 4) — lower, surer, and impossible to
code wrong. This hook carries only what a tool+target permission pattern *cannot* express:

  * `-auto-approve` and `-destroy` are flags that can appear anywhere in the command, not a prefix
  * the `ask` tier needs a reasoned checklist, which a permission's generic prompt cannot carry

The overlap on destroy/state-surgery is deliberate: those are catastrophic, and catastrophic rules
get several layers (Ch. 20). A plugin cannot ship `permissions`, so if a consumer never copied the
deny floor (see the SessionStart sentinel), this hook is the only thing standing there.

## Reading the command

`terraform apply -destroy` is Terraform's own spelling of a full destroy; the regex tiers this
replaced sent it to the ordinary apply checklist. They also denied a commit message that merely
mentioned `terraform state rm`. The command is now read through the shared shell lexer
(`_shell.py`): a tier fires on a `terraform`/`tofu` WORD and the arguments after it —
through `sudo`/`env`, `bash -c "..."`, a subshell `(cd infra && terraform destroy)`, `$(...)` and
`docker run hashicorp/terraform` — while a commit message or grep pattern that mentions terraform is
one quoted word, not an invocation. The Bash, PowerShell (`& terraform.exe destroy`) and Monitor tools
all reach it, each read in its own dialect.

## The honest caveat

Aliases, Makefiles, wrapper scripts and indirection stay invisible to any command parser. This gate
is defense in depth, not a wall — its real value is catching the *model's* ordinary mistakes
deterministically and cheaply. Adversarial evasion is a different threat model and belongs at the
permission layer and above.
"""

try:
    import _hooklib as hooklib
    import _shell as shell
except Exception as _import_error:  # a fail-closed gate whose modules will not load must still deny
    import json
    import sys
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "BLOCKED: terraform-command-gate could not load its shared modules (_hooklib, _shell: "
            "{}), so this command was not evaluated. Update or reinstall the sdh plugin, or run the "
            "command manually outside Claude Code.".format(type(_import_error).__name__)),
    }}))
    sys.exit(0)

import re

TERRAFORM = re.compile(r"\b(?:terraform|tofu)\b", re.I)

# State surgery: never legitimate from an agent.
_STATE_SURGERY = ("rm", "mv", "push", "replace-provider")
# `-destroy` on APPLY destroys; on PLAN it is a read-only preview and must fall through — the
# book's template regexes a bare \bdestroy\b, which denies that legitimate command.
_DESTROY_FLAG = re.compile(r"^--?destroy(?:=true)?$")
_AUTO_APPROVE = re.compile(r"^--?auto-approve(?:=true)?$")
_SEVERITY = ("state-surgery", "force-unlock", "destroy", "apply-destroy", "auto-approve", "apply")

APPLY_CHECKLIST = (
    "APPLY GATE — confirm before proceeding:\n"
    "- Was `terraform plan` run and the output actually reviewed?\n"
    "- Zero unexpected destroys or replacements in the plan?\n"
    "- Correct workspace / environment directory for this change?\n"
    "- State lock healthy (no stale lock from an interrupted run)?\n"
    "- Is this the intended account/region?"
)


def _invocations(command, dialect):
    """The arguments after every `terraform`/`tofu` word the command runs."""
    return [segment.words[index + 1:]
            for segment in shell.executed_segments(command, dialect)
            for index, word in enumerate(segment.words)
            if shell.basename(word) in ("terraform", "tofu")]


def _tier(args):
    index = 0
    while index < len(args) and args[index].startswith("-"):  # global flags: -chdir=, -help
        index += 1
    if index == len(args):
        return None
    subcommand, rest = args[index], args[index + 1:]
    if subcommand == "state":
        return "state-surgery" if rest[:1] and rest[0] in _STATE_SURGERY else None
    if subcommand in ("force-unlock", "destroy"):
        return subcommand
    if subcommand != "apply":
        return None
    if any(_DESTROY_FLAG.match(arg) for arg in rest):
        return "apply-destroy"
    return "auto-approve" if any(_AUTO_APPROVE.match(arg) for arg in rest) else "apply"


def _deny_state_tier(tier):
    if tier == "state-surgery":
        hooklib.deny(
            "BLOCKED: Terraform state surgery (`state rm/mv/push`) is human-only (see the "
            "`std-terraform-conventions` skill) — it edits the "
            "record of reality without touching reality, and a mistake orphans or destroys live "
            "infrastructure. Run it yourself outside the agent. To restructure safely, prefer "
            "`moved {}` blocks (see the terraform skill's state-move rule)."
        )
        return
    hooklib.deny(
        "BLOCKED: `force-unlock` is human-only. A lock usually means another apply is in "
        "flight; breaking it can corrupt state. Verify no apply is running, then unlock "
        "manually."
    )


def _deny_destroy_tier(tier):
    if tier == "destroy":
        hooklib.deny(
            "BLOCKED: `terraform destroy` is human-only and irreversible. If you intend to remove "
            "specific resources, remove them from the config and apply the plan instead — that is "
            "reviewable. (`terraform plan -destroy` is allowed: it only previews.)"
        )
    elif tier == "apply-destroy":
        hooklib.deny(
            "BLOCKED: `terraform apply -destroy` is `terraform destroy` under another name — "
            "human-only and irreversible (the `std-terraform-conventions` skill). To remove specific "
            "resources, delete them from the config instead, run `terraform plan`, review it, and "
            "apply that plan. (`terraform plan -destroy` is allowed: it only previews.)"
        )
    else:
        hooklib.deny(
            "BLOCKED: `apply -auto-approve` is prohibited — it removes the human from an "
            "irreversible action. Run `terraform plan`, review it, then apply without "
            "-auto-approve so the change is confirmed."
        )


def check(event):
    if not hooklib.is_shell_tool(event):
        return
    cmd = hooklib.shell_command(event)
    if not TERRAFORM.search(cmd):
        return

    tiers = {_tier(args) for args in _invocations(cmd, hooklib.shell_dialect(event))}
    tier = next((name for name in _SEVERITY if name in tiers), None)
    # --- Tier 1: DENY the never-legitimate ---
    if tier in ("state-surgery", "force-unlock"):
        _deny_state_tier(tier)
    elif tier in ("destroy", "apply-destroy", "auto-approve"):
        _deny_destroy_tier(tier)
    # --- Tier 2: apply — a human confirms against the checklist ---
    elif tier == "apply":
        hooklib.ask(APPLY_CHECKLIST)
    # --- Tier 3: read-only surface (plan / validate / fmt / output / state list|show) ---


if __name__ == "__main__":
    # Fail CLOSED: a gate guarding `apply` that cannot evaluate must deny (Ch. 9).
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="terraform-command-gate")
