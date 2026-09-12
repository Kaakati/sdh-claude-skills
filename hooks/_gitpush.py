#!/usr/bin/env python3
"""Which git commands a shell command runs, and where its pushes land.

ONE push parser, shared by `pre-commit-check` (deny a force push to a protected branch, ask on a
direct push) and `deployment-gate` (ask before a push that deploys), so the two can never disagree
about where a push lands. It reads commands through the `_shell` lexer, in the dialect of the tool
that runs them: `--follow-tags` and a chained `gh pr create --fill` are not `-f`, and a feature
branch named `...-main-nav` is not main.

A push that names no destination (`git push`, `git push origin HEAD`) still lands on a branch, so
`implied_pushes` asks the repository the push runs in: `@{push}` for a bare push (it honours
push.default), else the current branch. It answers only from the state the push will see: never
without the event's `cwd`, never for a push after a `cd`, `ssh` or `git checkout`/`switch`/`worktree`
earlier in the same command (`git checkout -b feature/x && git push -u origin HEAD` is read before the
checkout runs), and never through --git-dir/--work-tree. A git error, a timeout or a detached HEAD
leaves it silent.
"""

import collections
import fnmatch
import os
import re

import _hooklib as hooklib
import _shell as shell
import _teamgate as teamgate

GitCall = collections.namedtuple("GitCall", "name args options segment")
PushPlan = collections.namedtuple("PushPlan", "plain forced deleted is_forced open_ended")

_GIT_VALUE_OPTIONS = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                      "--config-env")
_PUSH_VALUE_OPTIONS = ("-o", "--push-option", "--repo", "--receive-pack", "--exec")
# Whole flags only: `-f` inside `--follow-tags`, `--fill` or `-fix` is not a force push.
_FORCE_FLAG = re.compile(
    r"^(?:--force|--force-with-lease(?:=.*)?|--force-if-includes|-[46dnquv]*f[46dnquv]*)$")
_DELETE_FLAG = re.compile(r"^(?:--delete|-[46fnquv]*d[46fnquv]*)$")
_EVERY_BRANCH = ("--all", "--branches", "--mirror")
# `$(git branch --show-current)` names the current branch as surely as HEAD does.
_CURRENT_BRANCH = re.compile(r"^(?:\$\(|`)\s*git\s+(?:branch\s+--show-current|rev-parse\s+--abbrev-ref\s+HEAD"
                             r"|symbolic-ref\s+--short\s+HEAD)\s*(?:\)|`)$")
_MOVES = ("cd", "pushd", "popd", "chdir", "set-location", "sl", "push-location", "pop-location", "ssh", "wsl")
_BRANCH_MOVES = ("checkout", "switch", "worktree")
_GIT_TIMEOUT = 2


def git_calls(command, dialect=shell.BASH):
    """GitCall(subcommand, args, global options, segment) for every `git` the command runs."""
    calls = [_git_call(program) for program in shell.programs(shell.executed_segments(command, dialect))]
    return [call for call in calls if call is not None]


def _git_call(program):
    if program.name != "git":
        return None
    index = 0
    while index < len(program.args) and program.args[index].startswith("-"):
        index += 2 if program.args[index] in _GIT_VALUE_OPTIONS else 1
    if index >= len(program.args):
        return None
    return GitCall(program.args[index], program.args[index + 1:], program.args[:index], program.segment)


def is_protected(branch, forcing=False):
    """Exact or glob match on SDH_PROTECTED_BRANCHES; a force push also guards release/*."""
    patterns = list(hooklib.protected_branches()) + (["release", "release/*"] if forcing else [])
    return any(fnmatch.fnmatchcase(branch, pattern) for pattern in patterns)


def push_plan(args):
    """Where a `git push` lands, judged per refspec: PushPlan(plain, forced, deleted branches,
    is_forced, open_ended — true when the command does not name every destination)."""
    flags, operands = _push_words(args)
    all_forced = any(_FORCE_FLAG.match(flag) for flag in flags) or "--mirror" in flags
    deleting = any(_DELETE_FLAG.match(flag) for flag in flags)
    plain, forced, deleted, any_plus = [], [], [], False
    open_ended = any(flag in _EVERY_BRANCH for flag in flags)
    for spec in operands[1:]:
        branch, plus, removes = _refspec(spec)
        any_plus = any_plus or plus
        if branch is None:
            open_ended = True
        elif removes or deleting:
            deleted.append(branch)
        else:
            (forced if plus or all_forced else plain).append(branch)
    if len(operands) < 2 and "--tags" not in flags:
        open_ended = True
    return PushPlan(plain, forced, deleted, all_forced or any_plus, open_ended)


def _push_words(args):
    flags, operands, index = [], [], 0
    while index < len(args):
        word = args[index]
        if word == "--":
            operands.extend(args[index + 1:])
            break
        if word.startswith("-") and len(word) > 1:
            flags.append(word)
            index += 2 if word in _PUSH_VALUE_OPTIONS else 1
            continue
        operands.append(word)
        index += 1
    return flags, operands


def _refspec(spec):
    """(destination branch — None when git picks it —, forced with '+', deletes with ':dst')."""
    plus = spec.startswith("+")
    source, colon, target = (spec[1:] if plus else spec).partition(":")
    destination = target if colon else source
    if destination.startswith("refs/heads/"):
        destination = destination[len("refs/heads/"):]
    if destination in ("", "HEAD", "@") or _CURRENT_BRANCH.match(destination):
        return None, plus, False
    return destination, plus, bool(colon) and not source


def implied_pushes(command, cwd, dialect=shell.BASH):
    """(branch, forced) for each push naming no destination, read from the repository it runs in;
    `forced` covers a force flag, a `+`/`:` refspec and --delete. See the module docstring for when
    it stays silent."""
    if not isinstance(cwd, str) or not cwd or not os.path.isdir(cwd):
        return []
    found = []
    for program in shell.programs(shell.executed_segments(command, dialect)):
        call = _git_call(program)
        if program.name in _MOVES or (call is not None and call.name in _BRANCH_MOVES):
            break
        if call is not None and call.name == "push":
            found.extend(_implied(call, cwd))
    return found


def _implied(call, cwd):
    flags, operands = _push_words(call.args)
    directory = _directory(call.options, cwd)
    if directory is None or any(flag in _EVERY_BRANCH + ("--tags",) for flag in flags):
        return []
    forced = any(_FORCE_FLAG.match(flag) or _DELETE_FLAG.match(flag) for flag in flags)
    if len(operands) < 2:
        branch = _push_branch(directory) or _current_branch(directory)
        return [(branch, forced)] if branch else []
    specs = [spec for spec in operands[1:] if _refspec(spec)[0] is None and spec.strip("+:")]
    branch = _current_branch(directory) if specs else None
    return [(branch, forced or any(spec.startswith(("+", ":")) for spec in specs))] if branch else []


def _directory(options, cwd):
    """The directory `git [options]` runs in: the event cwd joined with each `-C`; None when
    --git-dir or --work-tree points git somewhere the cwd does not say."""
    directory = cwd
    for index, option in enumerate(options):
        if option.startswith(("--git-dir", "--work-tree")):
            return None
        if option == "-C" and index + 1 < len(options):
            directory = os.path.join(directory, options[index + 1])
    return directory


def _push_branch(directory):
    """The branch a bare `git push` updates, from `@{push}` (`origin/main` -> `main`); None if unset."""
    code, out = teamgate.run_git(directory, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{push}"],
                                 _GIT_TIMEOUT)
    remote_branch = out.strip() if code == 0 else ""
    return remote_branch.split("/", 1)[1] if "/" in remote_branch else None


def _current_branch(directory):
    """The checked-out branch; None on a detached HEAD or any git error."""
    code, out = teamgate.run_git(directory, ["rev-parse", "--abbrev-ref", "HEAD"], _GIT_TIMEOUT)
    branch = out.strip() if code == 0 else ""
    return branch if branch and branch != "HEAD" else None
