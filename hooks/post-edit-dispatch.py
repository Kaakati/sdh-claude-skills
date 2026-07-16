#!/usr/bin/env python3
"""PostToolUse dispatcher for advisory Edit/Write checkers.

Reads the hook event once, then runs every advisory checker in-process and
prints the combined warnings. This replaces 12 separate hook entries, removing
~12 Python cold-starts (and 12 bash + interpreter probes) per edit.

Each checker module exposes `check(event) -> list[str]`. Checkers are isolated:
a crash in one is swallowed so it cannot suppress the others (advisory hooks
fail open). `auto-format.py` is intentionally NOT dispatched here — it mutates
files and may invoke slow formatters, so it keeps its own hook entry/timeout."""

import importlib.util
import os
import sys

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
]

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_check(filename):
    """Load a checker module by file path and return its `check` callable."""
    path = os.path.join(_HOOKS_DIR, filename)
    module_name = "_checker_" + filename[:-3].replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "check", None)


def main():
    event = hooklib.load_event()
    warnings = []
    for filename in CHECKERS:
        try:
            check = _load_check(filename)
            if check is None:
                warnings.append(
                    hooklib.hook_error(filename, RuntimeError("exposes no check(event) function")))
                continue
            warnings.extend(check(event) or [])
        except Exception as exc:
            # One bad checker must not break the chain (fail-open) — but it must not
            # do so silently, or a dead gate masquerades as a green one (Ch. 9).
            warnings.append(hooklib.hook_error(filename, exc))
            continue
    hooklib.emit(warnings)
    sys.exit(0)


if __name__ == "__main__":
    main()
