#!/usr/bin/env python3
"""
PostToolUse hook: Auto-format files after edits.
Reads JSON from stdin, extracts file_path, runs the appropriate formatter.

A missing formatter is NOT an error — this plugin has to work on day one in a
repo it did not design, where rubocop or prettier may simply not be installed.
But it is not silent either: Ch. 13 says such a hook "should say so once and exit
0, not crash on every write", and Ch. 9 adds that silent failure is invisible
failure. So the first edit of a filetype whose formatter is absent prints one
actionable line naming the binary; every later edit stays quiet.

Requires no external dependencies beyond Python 3.
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib as hooklib  # noqa: E402


FORMATTER_MAP = {
    # `-a/--autocorrect` ("only when it's safe"), NOT `-A/--autocorrect-all`
    # ("safe and unsafe"). RuboCop 1.87's own default.yml marks 53 cops
    # `SafeAutoCorrect: false` — its maintainers flag those corrections as able to change
    # behaviour. This hook runs unattended on every write and sends its output to DEVNULL,
    # so `-A` silently applied semantic rewrites to code nobody re-read. A formatter may
    # reshape code; it must not change what the code MEANS. Unsafe corrections are a
    # deliberate human act: run `rubocop -A` yourself and read the diff.
    "rb":    ("rubocop", ["rubocop", "--autocorrect", "--fail-level=error"]),
    "rake":  ("rubocop", ["rubocop", "--autocorrect", "--fail-level=error"]),
    "js":    ("prettier", ["prettier", "--write"]),
    "jsx":   ("prettier", ["prettier", "--write"]),
    "ts":    ("prettier", ["prettier", "--write"]),
    "tsx":   ("prettier", ["prettier", "--write"]),
    "css":   ("prettier", ["prettier", "--write"]),
    "scss":  ("prettier", ["prettier", "--write"]),
    "json":  ("prettier", ["prettier", "--write"]),
    "yaml":  ("prettier", ["prettier", "--write"]),
    "yml":   ("prettier", ["prettier", "--write"]),
    "erb":   ("htmlbeautifier", ["htmlbeautifier"]),
    # `ruff format`, NOT `ruff check --fix`: format is the layout-only, black-compatible
    # half (the house toolchain per std-python); `--fix` applies lint rewrites, which is
    # the deliberate-human-act category this hook must never run unattended.
    "py":    ("ruff", ["ruff", "format", "--quiet"]),
    "tf":    ("terraform", ["terraform", "fmt"]),
    "tfvars": ("terraform", ["terraform", "fmt"]),
}


# How to get each formatter, so the notice names a remedy instead of just a gap.
INSTALL_HINT = {
    "rubocop": "gem install rubocop (or add it to your Gemfile)",
    "prettier": "npm install --save-dev prettier",
    "htmlbeautifier": "gem install htmlbeautifier",
    "ruff": "pip install ruff (or: uv tool install ruff)",
    "terraform": "https://developer.hashicorp.com/terraform/install",
}


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")

    if not file_path or not os.path.isfile(file_path):
        sys.exit(0)

    _, ext = os.path.splitext(file_path)
    ext = ext.lstrip(".")

    if ext not in FORMATTER_MAP:
        sys.exit(0)

    binary_name, cmd_parts = FORMATTER_MAP[ext]

    if not shutil.which(binary_name):
        # Say so once per session, then never again for this formatter.
        hooklib.notice_once(
            data,
            f"missing-formatter-{binary_name}",
            f"sdh: `{binary_name}` is not on PATH, so .{ext} files will not be auto-formatted "
            f"this session. Install it ({INSTALL_HINT.get(binary_name, binary_name)}), or ignore "
            f"this — nothing is blocked either way. This notice appears once per session.",
        )
        sys.exit(0)

    try:
        subprocess.run(
            cmd_parts + [file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        # A formatter exiting non-zero is normal (unfixable offenses) and does not land
        # here. This is the formatter failing to RUN — swallowing that silently would
        # leave the user watching formatting quietly never happen.
        hooklib.notice_once(
            data,
            f"formatter-failed-{binary_name}",
            f"sdh: `{binary_name}` could not be run — {type(exc).__name__}: {exc}. "
            f".{ext} files are not being auto-formatted. Nothing is blocked. "
            f"This notice appears once per session.",
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
