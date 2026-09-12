#!/usr/bin/env python3
"""PreToolUse hook: Git commit validator.

Enforces conventional commits and blocks force pushes to protected branches.
Fails open: this is a workflow-convention gate, not a safety gate, so a bug here
must not block every Bash command (run_pre_blocker default).

It reads a command the way the shell will, not with a regex over the raw string. The regexes
this replaced validated the LAST `-m` (the Co-Authored-By trailer) instead of the subject, read a
heredoc message as the literal text `$(cat <<`, and took `--follow-tags` or a chained
`gh pr create --fill` for `-f` — so the house's own push-then-open-a-PR chain was denied as a
force push to main. A convention gate that denies correct work is a gate people route around.

The shell lexer is `_shell.py` and the push parser `_gitpush.py`, shared with deployment-gate so
the two gates can never disagree about where a push lands. Both are imported at the top: a missing
or broken copy exits 1, a visible hook error, never a silent allow. This file keeps only what is
this gate's own: reading the subject line a `git commit` will record.

The Bash, PowerShell and Monitor tools all reach it, each command read in its own dialect (a
PowerShell here-string commit message is a message, not `@`). A push that names no destination —
bare `git push` on main, `git push origin HEAD` — is resolved against the event's repository by
`_gitpush.implied_pushes`: a direct push to a protected branch asks, a forced one is denied.
"""

import os
import re

import _gitpush as gitpush
import _hooklib as hooklib
import _shell as shell

CONVENTIONAL_PATTERN = (
    r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)'
    r'(\(.+?\))?!?:\s.+'
)

_REUSED_MESSAGE = re.compile(
    r"^(?:-[a-zA-Z]*[cC]|--reuse-message|--reedit-message|--fixup|--squash)(?:=.*)?$")
_MESSAGE_FLAGS = (
    ("message", re.compile(r"^(?:-[a-zA-Z]*m|--message)$"), re.compile(r"^(?:-m|--message=)(.*)$", re.S)),
    ("file", re.compile(r"^(?:-[a-zA-Z]*F|--file)$"), re.compile(r"^(?:-F|--file=)(.+)$", re.S)),
)
_COMMIT_VALUE_OPTIONS = ("--author", "--date", "--trailer", "--cleanup", "-t", "--template",
                         "--pathspec-from-file")
_HEREDOC_MESSAGE = re.compile(
    r"^\s*\$\(\s*cat\s*<<-?\s*(['\"]?)([\w.-]+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*\n?\s*\)\s*$", re.S)
_GIT_WORD = re.compile(r"\bgit\b", re.I)


def commit_subject(call, cwd, written):
    """The subject line `git commit` will record; None when the command does not say (editor,
    -C/--fixup reuse, a message held in a variable). Bodies and trailers are never judged."""
    source = _message_source(call.args)
    if source is None:
        return None
    kind, value = source
    if kind == "file":
        value = _message_file(value, call, cwd, written)
    else:
        match = _HEREDOC_MESSAGE.match(value)
        value = match.group(3) if match else value
    subject = next((line.strip() for line in (value or "").splitlines() if line.strip()), None)
    return None if subject is None or subject[:1] in ("$", "`") else subject


def _message_source(args):
    """('message', the FIRST -m value) or ('file', the -F value); None when git takes it elsewhere."""
    options = args[:args.index("--")] if "--" in args else args
    if any(_REUSED_MESSAGE.match(word) for word in options):
        return None
    index = 0
    while index < len(options):
        following = options[index + 1] if index + 1 < len(options) else None
        for kind, bare, attached in _MESSAGE_FLAGS:
            if bare.match(options[index]):
                return (kind, following) if following is not None else None
            match = attached.match(options[index])
            if match:
                return kind, match.group(1)
        index += 2 if options[index] in _COMMIT_VALUE_OPTIONS else 1
    return None


def _message_file(path, call, cwd, written):
    """The -F message: the here-document for `-F -`; else the file, when it exists and this same
    command does not write it first (the stale copy would be judged instead of the new one)."""
    if path == "-":
        return call.segment.heredocs[0] if call.segment.heredocs else None
    if shell.basename(path) in written:
        return None
    for index, option in enumerate(call.options[:-1]):
        if option == "-C":
            cwd = os.path.join(cwd, call.options[index + 1])
    full = path if os.path.isabs(path) else os.path.join(cwd, path)
    return hooklib.read_file(full)[:65536] if os.path.isfile(full) else None


# ---------------------------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------------------------

def check(event):
    if not hooklib.is_shell_tool(event):
        return
    command, dialect = hooklib.shell_command(event), hooklib.shell_dialect(event)
    calls = gitpush.git_calls(command, dialect) if _GIT_WORD.search(command) else []
    plans = [gitpush.push_plan(call.args) for call in calls if call.name == "push"]
    implied = (gitpush.implied_pushes(command, event.get("cwd"), dialect)
               if any(plan.open_ended for plan in plans) else [])
    rewritten = [branch for plan in plans for branch in plan.forced + plan.deleted]
    rewritten += [branch for branch, forced in implied if forced]
    if any(gitpush.is_protected(branch, forcing=True) for branch in rewritten):
        _deny_rewrite()
        return
    subject = _unconventional_subject(calls, command, event)
    if subject is not None:
        _deny_subject(subject)
        return
    _ask_about_pushes(plans, implied)


def _unconventional_subject(calls, command, event):
    commits = [call for call in calls if call.name == "commit"]
    if not commits:
        return None
    segments = shell.executed_segments(command, hooklib.shell_dialect(event))
    written = {shell.basename(path) for path in shell.written_files(segments)}
    cwd = event.get("cwd") or os.getcwd()
    for call in commits:
        subject = commit_subject(call, cwd, written)
        if subject is not None and not re.match(CONVENTIONAL_PATTERN, subject):
            return subject
    return None


def _deny_rewrite():
    # Name the remedy, not just the prohibition: a denial that says only what is
    # forbidden invites the model to retry variations; "denied because X, do Y
    # instead" invites Y (Ch. 25, "the model argues with a denial").
    hooklib.deny(
        "BLOCKED: Force-pushing or deleting a protected branch rewrites history other people "
        "have already pulled. Do this instead: to undo a bad commit on a shared branch, "
        "`git revert <sha>` and open a PR — it is reviewable and rewrites nothing. To tidy your "
        "own work, force-push your FEATURE branch (`git push --force-with-lease "
        "origin <your-branch>`), then open a PR."
    )


def _deny_subject(subject):
    hooklib.deny(
        "BLOCKED: Commit message does not follow the conventional format required by the "
        "`std-git-workflow` skill. "
        f"Got subject: '{subject[:120]}'. "
        "Expected: <type>(<scope>): <description> where type is one of: "
        "feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert. "
        "Only the subject line is checked, so a body and trailers (Co-Authored-By) are fine."
    )


def _ask_about_pushes(plans, implied):
    """Ask on a direct push to a protected branch — named, or the branch a push naming none updates
    (`implied`: (branch, forced) from the repository) — then on a force push naming no destination."""
    protected = [branch for plan in plans for branch in plan.plain if gitpush.is_protected(branch)]
    protected += [branch for branch, forced in implied if not forced and gitpush.is_protected(branch)]
    if protected:
        hooklib.ask(
            f"WARNING: Direct push to '{protected[0]}' detected. "
            "Consider using a pull request instead (the `std-git-workflow` skill). "
            "Allow this push?"
        )
        return
    if any(plan.is_forced and plan.open_ended for plan in plans):
        hooklib.ask(
            "WARNING: Force push without a named destination — the command does not say which "
            "branch it rewrites (no refspec, HEAD, or --all/--mirror). Name it instead: "
            "`git push --force-with-lease origin <your-branch>` (the `std-git-workflow` skill). "
            "Allow this push?"
        )


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=False, gate_label="pre-commit-check")
