#!/usr/bin/env python3
"""
SessionStart hook: Verify development environment is ready.

Checks git repository status, current branch, and working tree state.
Always exits 0 — informational only, never blocks the session.
"""
import json
import subprocess
import sys


def run_git(args):
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def main():
    # Consume stdin (hook protocol) — ignore content
    try:
        sys.stdin.read()
    except Exception:
        pass

    # Check if we're in a git repo
    toplevel = run_git(["rev-parse", "--show-toplevel"])
    if not toplevel:
        print("Environment: not a git repository.")
        sys.exit(0)

    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    status = run_git(["status", "--porcelain"])
    tree_state = "dirty working tree" if status else "clean working tree"

    parts = [f"Environment: {branch}", tree_state]

    if branch in ("main", "master"):
        parts.append("note: on protected branch — use a feature branch for new work")

    print(", ".join(parts) + ".")
    sys.exit(0)


if __name__ == "__main__":
    main()
