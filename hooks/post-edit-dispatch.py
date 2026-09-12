#!/usr/bin/env python3
"""PostToolUse dispatcher for advisory Edit/Write checkers.

Reads the hook event once, then runs every advisory checker in-process and
prints the combined warnings. This replaces 12 separate hook entries, removing
~12 Python cold-starts (and 12 bash + interpreter probes) per edit.

Each checker module exposes `check(event) -> list[str]`. Checkers are isolated:
a crash in one is swallowed so it cannot suppress the others (advisory hooks
fail open). `auto-format.py` is intentionally NOT dispatched here — it mutates
files and may invoke slow formatters, so it keeps its own hook entry/timeout.

Four failures around that loop used to look exactly like a clean edit:
  * An empty or unparseable event ran every checker on {} and printed nothing. It is now one
    HOOK ERROR line, and no checker runs on an event that does not exist.
  * Matching PostToolUse hooks run in PARALLEL, so checkers could read the file while
    auto-format was rewriting it, see "", and pass every rule. The dispatcher waits (bounded)
    for auto-format's "done" marker before the first checker reads the file.
  * One legacy file injected 402 warning lines. Each checker now shows its first
    PER_CHECKER_LINES and a count of the rest; HOOK ERROR lines are never dropped.
  * A quadratic checker on a 1 MB file pushed the whole reply past the hook timeout, which
    DISCARDS everything. Past BUDGET_SECONDS the remaining checkers are skipped and named.
"""

import importlib.util
import os
import sys
import time

import _hooklib as hooklib

# Run order mirrors the previous settings.json sequence.
CHECKERS = [
    "test-runner.py",
    "code-quality-checker.py",
    "error-handling-checker.py",
    "test-coverage-checker.py",
    "clean-architecture-checker.py",
    "i18n-checker.py",
    "accessibility-checker.py",
    "api-design-checker.py",
    "monitoring-checker.py",
    "atomic-design-checker.py",
    "rails-routes-checker.py",
    "terraform-checker.py",
    "design-token-checker.py",
    "database-design-checker.py",
    # Last on purpose: it reads the architecture index under its own 1.5 s budget, so a cold or
    # large index can never delay the checkers above.
    "orthogonality-checker.py",
]

PER_CHECKER_LINES = 5
BUDGET_SECONDS = 20.0   # hooks.json gives this hook 30 s; the rest is launcher start and emit
FORMATTER_GRACE = 0.5   # how long auto-format may take to START before we stop expecting it
FORMATTER_CAP = 8.0     # how long a running formatter may hold the checkers back

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(filename):
    """Load a hook module by file path; None when it cannot be specced."""
    path = os.path.join(_HOOKS_DIR, filename)
    module_name = "_checker_" + filename[:-3].replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_check(filename):
    """Load a checker module by file path and return its `check` callable."""
    module = _load_module(filename)
    return getattr(module, "check", None) if module else None


def _formattable(file_path):
    """True when auto-format.py maps this file's extension to a formatter."""
    try:
        extension = os.path.splitext(file_path)[1].lstrip(".")
        return extension in getattr(_load_module("auto-format.py"), "FORMATTER_MAP", {})
    except Exception:
        return False


def _marker_state(marker):
    """None (absent), "done", or "running" (present — including mid-write)."""
    if not os.path.exists(marker):
        return None
    return "done" if hooklib.read_file(marker).strip() == "done" else "running"


def _await_formatter(event, started):
    """Hold the checkers until auto-format has finished this edit's file. Returns a note or None."""
    marker = hooklib.formatter_marker(event)
    if not marker or not _formattable(hooklib.get_file_path(event)):
        return None
    while True:
        state, waited = _marker_state(marker), time.monotonic() - started
        if state == "done" or (state is None and waited > FORMATTER_GRACE):
            _discard(marker)
            return None
        if waited > FORMATTER_CAP:
            return (f"NOTE: auto-format was still rewriting this file after {FORMATTER_CAP:.0f}s, "
                    "so these checks may describe the pre-format text.")
        time.sleep(0.05)


def _discard(marker):
    try:
        os.remove(marker)
    except OSError:
        pass


def _run_one(filename, event):
    try:
        check = _load_check(filename)
        if check is None:
            return [hooklib.hook_error(filename, RuntimeError("exposes no check(event) function"))]
        return list(check(event) or [])
    except Exception as exc:
        # One bad checker must not break the chain (fail-open) — but it must not
        # do so silently, or a dead gate masquerades as a green one (Ch. 9).
        return [hooklib.hook_error(filename, exc)]


def _cap_checker(filename, lines):
    """One checker's first PER_CHECKER_LINES warnings, every HOOK ERROR, and a count of the rest."""
    kept, shown, extra = [], 0, 0
    for line in (entry for entry in lines if entry):
        is_error = str(line).startswith("HOOK ERROR")
        if is_error or shown < PER_CHECKER_LINES:
            kept.append(line)
            shown += 0 if is_error else 1
        else:
            extra += 1
    if extra:
        kept.append(f"...and {extra} more from {filename} (run it standalone with "
                    "SDH_HOOK_MAX_WARNINGS=0 for the full list).")
    return kept


def _run_checkers(event, started):
    warnings = []
    for index, filename in enumerate(CHECKERS):
        if time.monotonic() - started > BUDGET_SECONDS:
            warnings.append(
                f"HOOK ERROR: post-edit-dispatch.py hit its {BUDGET_SECONDS:.0f}s budget; "
                f"{', '.join(CHECKERS[index:])} did NOT run, so their rules were not enforced "
                "on this edit. Run them standalone on this file.")
            break
        warnings.extend(_cap_checker(filename, _run_one(filename, event)))
    return warnings


def main():
    started = time.monotonic()
    event, error = hooklib.load_event_strict()
    if error:
        hooklib.emit(hooklib.hook_error("post-edit-dispatch.py", ValueError(error)))
        sys.exit(0)
    note = _await_formatter(event, started)
    hooklib.emit(([note] if note else []) + _run_checkers(event, started))
    sys.exit(0)


if __name__ == "__main__":
    main()
