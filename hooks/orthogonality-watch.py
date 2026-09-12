#!/usr/bin/env python3
"""PostToolUse hook (asyncRewake): the orthogonality checks the dispatched checker cannot see.

Registered with `asyncRewake: true` on PostToolUse `Edit|Write|MultiEdit|Bash|PowerShell` and the MCP file
writers, and on PostToolUseFailure `Bash|PowerShell`: `npm install ky && npm test` wrote package.json even
when the test fails. A command the user interrupted (`is_interrupt`) wakes nobody.
Package installs (`npm install ky`, `uv add requests`, `bundle add httparty`) and generators
(`rails g model Client`, `manage.py startapp`, `alembic revision`) write files through Bash, where
the Edit/Write matchers of `post-edit-dispatch.py` never look. This hook runs in the background, so
an edit does not wait on it, and it wakes Claude only when it has something new to say.

What `_archhooks.watch` (in `_archwatch`) does:
  * Shell tools (Bash; PowerShell and Monitor carry the same `tool_input.command`): it continues only for
    a package-manager add/install, a generator or a tree-rewriting git command, read with the house shell
    lexer (quoted text is data, not a command) and looking through runner prefixes (`bundle exec`,
    `uv run`-style runners, `python -m`, `docker compose run`). File tools: only for in-scope source files
    and dependency manifests inside a project root;
  * when another writer holds the index lock it waits up to 15 s, then checks read-only and keeps the
    paths out of the first baseline, so an install made during the first index build is still reported;
  * it writes the index incrementally for the changed paths (untracked-aware git status after a Bash
    command), then runs CM1, DK1, DK2 and BC2 on changed manifests, models and migrations. A
    file-tool edit adds no detector lines, because `orthogonality-checker.py` already reported that
    file;
  * installed community tools (packwerk, import-linter, tach, dependency-cruiser, jscpd, squawk) run
    only with SDH_ORTHOGONALITY_TOOLS=1. None is ever installed, and nothing is launched through
    npx, pnpm dlx, yarn dlx, bunx, uvx, uv run or pipx run.

Wake contract: asyncRewake "wakes Claude on exit code 2", and the hook's stderr is shown to Claude
as a system reminder. Exit 2 carries at most five stderr lines, only for findings new since the
baseline and not yet shown this session. Every other outcome exits 0 and prints nothing, a crash
included: the engine records it in the index status table and `orthogonality-checker.py` reports it
once per session, so a traceback never wakes Claude. Nothing here asks, denies or blocks.
`SDH_ORTHOGONALITY=off` disables it; policy, declarations and full scans are the `orthogonality`
skill's.
"""
import os
import re
import sys

import _hooklib as hooklib

# An incremental pass over the changed paths takes well under a second. A large `git pull` stops at
# this budget and commits a partial index, which the next pass or session completes. A
# non-interactive session may run an asyncRewake hook in the foreground, so this also bounds what one
# Bash call can cost there; installed tools keep their own budget inside the 150 s hooks.json timeout.
# A watcher that waited on another writer's lock (at most `_archwatch.LOCK_WAIT_SECONDS`) skips the tools.
REFRESH_BUDGET_SECONDS = 25.0
SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")

# Pre-filters that let an irrelevant event exit before the index modules are imported. Each is a
# SUPERSET of what `_archhooks.watch` acts on, so it can only let an event through, never drop one:
# every program the engine classifies has one of these names, and every path it keeps ends in a
# source extension or is a manifest (`Gemfile`, `package.json`, `pyproject.toml`,
# `pnpm-workspace.yaml`, `requirements*.txt|.in`).
TRIGGER_PROGRAM = re.compile(
    r"(?<![\w-])(?:npm|pnpm|yarn|bun|bundle|uv|poetry|pip3?|rails|alembic|git)(?![\w-])|manage\.py")
MAYBE_IN_SCOPE = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".sql",
                  ".json", ".toml", ".yaml", ".txt", ".in", "")


def worth_a_look(event):
    """False only for an event the engine would ignore: a shell command naming no trigger program (a
    runner prefix such as `uv run` or `docker compose run` still names the program it runs), or a file
    whose extension no in-scope file or manifest has."""
    if hooklib.tool_name(event) in SHELL_TOOLS:
        return bool(TRIGGER_PROGRAM.search(str(hooklib.tool_input(event).get("command") or "")))
    file_path = hooklib.get_file_path(event)
    name = str(file_path or "").replace("\\", "/").rsplit("/", 1)[-1]
    return bool(name) and os.path.splitext(name)[1].lower() in MAYBE_IN_SCOPE


def wake_lines(event):
    """(exit code, stderr lines) from the engine; (0, []) on any failure (see the docstring)."""
    try:
        import _archhooks
        code, text = _archhooks.watch(event, budget=REFRESH_BUDGET_SECONDS)
        lines = [line for line in str(text or "").splitlines() if line.strip()]
        return code, lines[:_archhooks.WATCH_MAX_LINES]
    except Exception:
        return 0, []


def main():
    event, error = hooklib.load_event_strict()
    if error or event.get("is_interrupt") is True or not worth_a_look(event):
        sys.exit(0)
    code, lines = wake_lines(event)
    if code == 2 and lines:
        sys.stderr.write("\n".join(lines) + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
