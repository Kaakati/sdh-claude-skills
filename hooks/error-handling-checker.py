#!/usr/bin/env python3
"""
PostToolUse hook: Error handling checker.

Checks source files for empty catch/rescue/except blocks and
rescue Exception (should be StandardError) per the `std-error-handling` skill,
and — the Python analog — bare `except:` / `except BaseException` per the
`std-python` skill. Exits silently for non-source files.
"""
import os
import re

import _hooklib as hooklib


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")


def check_empty_handlers(content, ext):
    warnings = []
    if ext == ".rb":
        # rescue ... followed by end with nothing meaningful between
        pattern = re.compile(
            r"rescue\b[^\n]*\n(\s*#[^\n]*\n)*\s*end\b", re.MULTILINE
        )
        if pattern.search(content):
            warnings.append(
                "WARNING: Empty error handler found per the `std-error-handling` skill."
            )
    elif ext == ".py":
        # except ... : followed by pass or just a comment
        pattern = re.compile(
            r"except\b[^\n]*:\s*\n(\s*#[^\n]*\n)*\s*pass\b", re.MULTILINE
        )
        if pattern.search(content):
            warnings.append(
                "WARNING: Empty error handler found per the `std-error-handling` skill."
            )
    else:
        # JS/TS: catch(...) { } with nothing meaningful inside
        pattern = re.compile(
            r"catch\s*\([^)]*\)\s*\{\s*(//[^\n]*)?\s*\}", re.MULTILINE
        )
        if pattern.search(content):
            warnings.append(
                "WARNING: Empty error handler found per the `std-error-handling` skill."
            )
    return warnings


def check_rescue_exception(content, ext):
    if ext != ".rb":
        return []
    pattern = re.compile(r"rescue\s+Exception\b")
    if pattern.search(content):
        return [
            "WARNING: Rescue StandardError, not Exception per the `std-error-handling` skill."
        ]
    return []


def check_bare_except(content, ext):
    """Bare `except:` / `except BaseException` — the Python analog of `rescue Exception`:
    both catch SystemExit and KeyboardInterrupt, so shutdown and Ctrl-C die silently.
    Covers the tuple form (`except (BaseException, ValueError):`) and 3.11's
    `except*` groups. `except Exception:` is allowed here — whether it re-raises is a
    judgement call the `std-python` skill owns; this gate flags only the unambiguous
    width. Line-based, so a docstring QUOTING the anti-pattern can false-positive —
    deliberate parity with check_empty_handlers above."""
    if ext != ".py":
        return []
    pattern = re.compile(r"^\s*except\*?\s*(?::|[^:\n]*\bBaseException\b[^:\n]*:)", re.MULTILINE)
    if pattern.search(content):
        return [
            "WARNING: Catch Exception (or narrower) — never bare `except:` or "
            "`except BaseException` per the `std-python` skill."
        ]
    return []


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []
    warnings.extend(check_empty_handlers(content, ext))
    warnings.extend(check_rescue_exception(content, ext))
    warnings.extend(check_bare_except(content, ext))
    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
