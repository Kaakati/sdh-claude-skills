#!/usr/bin/env python3
"""PreToolUse hook: Deployment gate.

Detects deployment commands targeting production or protected branches and
requires explicit confirmation before allowing execution.

Monitored commands:
- git push to a protected branch (SDH_PROTECTED_BRANCHES; default main/master/develop), any force push
- aws ecs, vercel deploy/--prod, docker push
- store releases: fastlane release lanes and upload actions, eas submit/update
- gcloud run/app/functions deploy

Terraform is owned by `terraform-command-gate.py` (a three-tier gate), not this hook.

Every command is read through the shell lexer (`_shell.py`) and the push parser (`_gitpush.py`) —
the SAME parser pre-commit-check uses, so the two can never disagree about where a push lands. The
regex this replaced asked on any protected-branch WORD after `git push`: a feature branch named
`feature/TICKET-42-main-nav`, or a `gh pr create --base main` chained after the push. And it never
saw the house's own releases: `bundle exec fastlane ios beta`, `fastlane supply --track production`.

Emits an 'ask' (confirmation) decision when a deployment command is detected.
Fails open: a bug here must not block unrelated commands. The shared modules are imported at the
top, so a missing or broken copy exits 1 — a visible hook error, never a silent allow."""

import re

import _gitpush as gitpush
import _hooklib as hooklib
import _shell as shell

_DEPLOY_HINT = re.compile(r"\b(?:git|aws|vercel|docker|podman|fastlane|eas|eas-cli|gcloud)\b", re.I)
_FASTLANE_PLATFORMS = ("ios", "android", "mac")
_FASTLANE_ACTIONS = ("deliver", "pilot", "supply", "upload_to_play_store", "upload_to_testflight",
                     "upload_to_app_store", "appstore", "testflight")
_RELEASE_LANE = re.compile(
    r"^(?:beta|release|deploy|production|prod|internal|alpha|promote|submit|store)(?:_\w+)?$")


def _push_warnings(command, cwd, dialect):
    """Warnings for pushes that deploy: to a protected branch (named, or the branch a push naming none
    updates, read from the event's repository by `_gitpush.implied_pushes`), and any force push.

    `git push origin main` also draws pre-commit-check's direct-push ask. That is one prompt, not
    two: Claude Code combines every matching PreToolUse hook into a single decision (the most
    restrictive wins), and the reasons are different concerns — "open a PR" there, "verify CI and
    approval before this deploys" here. What the Terraform note below forbids is two hooks DECIDING
    one command differently (ask vs deny on -auto-approve); one shared push parser makes that
    impossible for pushes."""
    plans = [gitpush.push_plan(call.args) for call in gitpush.git_calls(command, dialect) if call.name == "push"]
    protected = [branch for plan in plans for branch in plan.plain + plan.forced if gitpush.is_protected(branch)]
    if any(plan.open_ended for plan in plans):
        protected += [branch for branch, _forced in gitpush.implied_pushes(command, cwd, dialect)
                      if gitpush.is_protected(branch)]
    warnings = [f"Pushing to protected branch '{protected[0]}'. "
                "Verify CI has passed and PR was approved per the `std-git-workflow` skill."] if protected else []
    if any(plan.is_forced for plan in plans):
        warnings.append(
            "Force push detected. This can overwrite remote history. "
            "Force pushes to protected branches are prohibited per the `std-git-workflow` skill."
        )
    return warnings


def _tail(words, names, program):
    """The words after the first word naming `program` (`bundle exec fastlane`, `npx vercel`)."""
    return words[names.index(program) + 1:] if program in names else None


def _operands(words):
    return [word for word in (words or []) if not word.startswith("-")]


def _next_operand(operands, word):
    index = operands.index(word) + 1 if word in operands else len(operands)
    return operands[index] if index < len(operands) else None


def _is_ecs_deploy(words, names):
    operands = _operands(_tail(words, names, "aws"))
    return _next_operand(operands, "ecs") in ("update-service", "create-service", "deploy")


def _is_vercel_deploy(words, names):
    tail = _tail(words, names, "vercel")
    operands = _operands(tail)
    return tail is not None and ("--prod" in tail or operands[:1] in (
        ["deploy"], ["promote"], ["rollback"], ["redeploy"]))


def _is_image_push(words, names):
    tail = _tail(words, names, "docker")
    tail = _tail(words, names, "podman") if tail is None else tail
    operands = _operands(tail)
    return operands[:1] == ["push"] or operands[:2] in (["image", "push"], ["compose", "push"]) \
        or (operands[:1] == ["buildx"] and "--push" in tail)


def _is_store_release(words, names):
    operands = _operands(_tail(words, names, "fastlane"))
    if operands[:1] and operands[0] in _FASTLANE_PLATFORMS:
        operands = operands[1:]
    return bool(operands) and (operands[0] in _FASTLANE_ACTIONS or bool(_RELEASE_LANE.match(operands[0])))


def _is_eas_release(words, names):
    tail = _tail(words, names, "eas")
    tail = _tail(words, names, "eas-cli") if tail is None else tail
    operands = _operands(tail)
    return operands[:1] in (["submit"], ["update"], ["deploy"]) \
        or (operands[:1] == ["build"] and "--auto-submit" in tail)


def _is_gcloud_deploy(words, names):
    operands = [word for word in _operands(_tail(words, names, "gcloud")) if word not in ("alpha", "beta")]
    return operands[:2] in (["run", "deploy"], ["app", "deploy"], ["functions", "deploy"])


_DEPLOYS = (
    (_is_ecs_deploy,
     "AWS ECS deployment detected. Verify: "
     "1) Target environment (staging vs production). "
     "2) Health checks are configured. "
     "3) Rollback strategy is ready per the `std-infrastructure` skill."),
    (_is_vercel_deploy,
     "Vercel deployment detected. Verify: "
     "1) Build passes locally. "
     "2) Environment variables are set. "
     "3) Preview deployment was tested per the `std-infrastructure` skill."),
    (_is_image_push,
     "Docker push detected. Verify: "
     "1) Image was built from tested code. "
     "2) Image tag matches the release version. "
     "3) Vulnerability scan passed."),
    (_is_store_release,
     "Store release via fastlane detected (TestFlight / App Store / Play track). Verify: "
     "1) The build number was bumped. "
     "2) The lane and track are the intended ones (internal vs production). "
     "3) Release notes and signing are right per the `mobile-beta-release` skill."),
    (_is_eas_release,
     "EAS submit/update detected — an `eas update` reaches installed apps on that channel at once. "
     "Verify: 1) The channel and runtime version. "
     "2) The build was tried on a preview channel first per the `mobile-beta-release` skill."),
    (_is_gcloud_deploy,
     "Google Cloud deploy detected. Verify: "
     "1) Target project and region. "
     "2) The image or source revision is the tested one. "
     "3) A previous revision is ready to roll back to per the `std-infrastructure` skill."),
)


def _deploy_warnings(command, dialect):
    warnings = []
    for segment in shell.executed_segments(command, dialect):
        names = [shell.basename(word).split("@")[0] for word in segment.words]
        for detect, warning in _DEPLOYS:
            if warning not in warnings and detect(segment.words, names):
                warnings.append(warning)
    return warnings


def check(event):
    if not hooklib.is_shell_tool(event):
        return

    command, dialect = hooklib.shell_command(event), hooklib.shell_dialect(event)
    if not _DEPLOY_HINT.search(command):
        return
    warnings = _push_warnings(command, event.get("cwd"), dialect) + _deploy_warnings(command, dialect)

    # NOTE: Terraform is deliberately NOT handled here. `terraform-command-gate.py` owns the
    # whole terraform surface with a proper three-tier gate (deny state-surgery/destroy/
    # -auto-approve, ask on apply with a checklist, allow the read-only surface). Two hooks
    # both emitting a decision for `terraform apply` meant two prompts for one command —
    # approval fatigue is how you get a human who stops reading (Ch. 20, layer 6) — and on
    # `apply -auto-approve` they disagreed outright (ask vs deny). One concern, one owner.

    if warnings:
        hooklib.ask(
            "Deployment gate — confirm before proceeding:\n"
            + "\n".join(f"- {w}" for w in warnings)
        )


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="deployment-gate")
