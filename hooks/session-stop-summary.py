#!/usr/bin/env python3
"""
Stop hook: Summarize session activity.

Shows a brief summary of uncommitted changes and unpushed commits
so the user knows the state of their working tree when Claude stops.
Always exits 0 — informational only, never blocks.
"""
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
        sys.exit(0)

    notes = []

    # Count uncommitted changes
    status = run_git(["status", "--porcelain"])
    if status:
        lines = [l for l in status.splitlines() if l.strip()]
        staged = sum(1 for l in lines if l[0] != " " and l[0] != "?")
        unstaged = sum(1 for l in lines if len(l) > 1 and l[1] != " " and l[0] != "?")
        untracked = sum(1 for l in lines if l.startswith("??"))
        parts = []
        if staged:
            parts.append(f"{staged} staged")
        if unstaged:
            parts.append(f"{unstaged} modified")
        if untracked:
            parts.append(f"{untracked} untracked")
        notes.append(f"Working tree: {', '.join(parts)}")

    # Check for unpushed commits
    upstream = run_git(["rev-parse", "--abbrev-ref", "@{upstream}"])
    if upstream:
        ahead = run_git(["rev-list", "--count", f"{upstream}..HEAD"])
        if ahead and int(ahead) > 0:
            notes.append(f"Unpushed: {ahead} commit(s) ahead of {upstream}")

    if notes:
        print("Session summary: " + ". ".join(notes) + ".")

    sys.exit(0)


if __name__ == "__main__":
    main()
