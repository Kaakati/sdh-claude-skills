#!/usr/bin/env python3
"""SessionStart hook (async): refresh this project's orthogonality architecture index.

Registered for the `startup|resume|fork` sources only, as its own `async: true` entry, apart from
`session-start-check.py`: that entry carries the permission-floor sentinel and must never wait on an
index build. `clear` and `compact` change no files, so they never refresh.

`_archhooks.session_refresh` does the work, shared with the `orthogonality` skill's arch_index.py:
it seeds a new linked worktree's index from the main checkout, refreshes by (size, mtime_ns) and
content hash, commits per file, and stamps the findings baseline (record existing, report new) the
first time the index is complete. It stops at REFRESH_BUDGET_SECONDS and commits a partial index
(`complete: false`), which the next session or `orthogonality-watch.py` pass continues; the baseline
shares that budget, and a detector that does not finish is stamped in a later session. A session
started outside a project (no .git or package manifest at its root, the home directory, a filesystem
root) builds nothing.

Output: none. A failure inside the refresh goes to the index `status` table, and
`orthogonality-checker.py` reports it once per session, so a broken refresh is visible without a
message on every session start. Only a failure before the refresh can record anything (a broken
import) prints one HOOK ERROR line. Always exits 0; never asks, denies or blocks.
`SDH_ORTHOGONALITY=off` disables it.

The index lives under `${CLAUDE_PLUGIN_DATA}/orthogonality/<project key>/`: a rebuildable cache,
removed with the plugin, with a temp-directory fallback when CLAUDE_PLUGIN_DATA is unset and an
`SDH_ORTHOGONALITY_DIR` override. Nothing is written into the project.
"""
import sys

import _hooklib as hooklib

# Claude Code does not enforce `timeout` on an `async: true` command hook, so this budget is the
# real cap on a background build. A stopped pass loses nothing: facts are committed per file.
REFRESH_BUDGET_SECONDS = 120.0


def main():
    event = hooklib.load_event()
    try:
        import _archhooks
        _archhooks.session_refresh(event, budget=REFRESH_BUDGET_SECONDS)
    except Exception as exc:
        hooklib.emit(hooklib.hook_error("orthogonality-index.py", exc), event_name="SessionStart")
    sys.exit(0)


if __name__ == "__main__":
    main()
