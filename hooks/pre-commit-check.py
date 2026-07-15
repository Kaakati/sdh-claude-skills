#!/usr/bin/env python3
"""PreToolUse hook: Git commit validator.

Enforces conventional commits and blocks force pushes to protected branches.
Fails open: this is a workflow-convention gate, not a safety gate, so a bug here
must not block every Bash command (run_pre_blocker default)."""

import re

import _hooklib as hooklib

COMMIT_PATTERN = r'git\s+commit\s+.*-m\s+["\'](.+?)["\']'
CONVENTIONAL_PATTERN = (
    r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)'
    r'(\(.+?\))?!?:\s.+'
)


# Built per-call rather than at import so SDH_PROTECTED_BRANCHES is honoured (Ch. 13,
# "configurable at the edges" — a plugin that hard-codes our branch names is unusable
# in a repo that calls its trunk something else). Defaults preserve the previous
# behaviour exactly: main|master|develop, plus release/* for force pushes.
def _force_push_pattern():
    return r'git\s+push\s+.*(-f|--force).*\s+(' + hooklib.branch_alternation(extra=("release",)) + r')'


def _direct_push_pattern():
    return r'git\s+push\s+(?:origin\s+)?(' + hooklib.branch_alternation() + r')\s*$'


def check(event):
    if hooklib.tool_name(event) != "Bash":
        return
    command = hooklib.tool_input(event).get("command", "")

    if re.search(_force_push_pattern(), command):
        # Name the remedy, not just the prohibition: a denial that says only what is
        # forbidden invites the model to retry variations; "denied because X, do Y
        # instead" invites Y (Ch. 25, "the model argues with a denial").
        hooklib.deny(
            "BLOCKED: Force push to a protected branch rewrites history other people have "
            "already pulled. Do this instead: to undo a bad commit on a shared branch, "
            "`git revert <sha>` and open a PR — it is reviewable and rewrites nothing. To "
            "tidy your own work, force-push your FEATURE branch (`git push --force-with-lease "
            "origin <your-branch>`), then open a PR."
        )
        return

    commit_match = re.search(COMMIT_PATTERN, command)
    if commit_match:
        message = commit_match.group(1)
        if not re.match(CONVENTIONAL_PATTERN, message):
            hooklib.deny(
                "BLOCKED: Commit message does not follow the conventional format required by the "
                "`std-git-workflow` skill. "
                f"Got: '{message}'. "
                "Expected: <type>(<scope>): <description> where type is one of: "
                "feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
            )
            return

    direct_push = re.search(_direct_push_pattern(), command)
    if direct_push:
        branch = direct_push.group(1)
        hooklib.ask(
            f"WARNING: Direct push to '{branch}' detected. "
            "Consider using a pull request instead. Allow this push?"
        )
        return


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="pre-commit-check")
