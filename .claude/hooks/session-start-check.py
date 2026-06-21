#!/usr/bin/env python3
"""
SessionStart hook: Verify development environment is ready.

Checks git repository status, current branch, and working tree state, and — for
monorepos/large codebases — detects which framework area the session launched in
so Claude knows which conventions apply (see docs/monorepo-setup.md).
Always exits 0 — informational only, never blocks the session.
"""
import json
import os
import subprocess
import sys

# Relevant rule files per framework area (wrapper-directory-agnostic detection).
AREA_RULES = {
    "rails": "rails-conventions, phlex-conventions, api-design, database, monitoring, clean-architecture",
    "nextjs": "nextjs, accessibility, i18n, testing, clean-architecture",
    "vite": "reactjs, accessibility, i18n, testing, clean-architecture",
    "react-native": "react-native, accessibility, i18n, clean-architecture",
}


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


def launch_dir():
    """The directory the session started in (SessionStart provides `cwd`)."""
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    return data.get("cwd") or os.getcwd()


def detect_area(cwd):
    """Detect the framework area of the launch directory via on-disk markers,
    using the shared _hooklib detection. Returns a framework label or None."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _hooklib
        # Pass a sentinel file inside cwd so detection resolves from that dir.
        return _hooklib.detect_framework(os.path.join(cwd, "__session__"))
    except Exception:
        return None


def main():
    cwd = launch_dir()

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

    area = detect_area(cwd)
    if area in AREA_RULES:
        parts.append(f"detected {area} area — these rules auto-load: {AREA_RULES[area]}")

    print(", ".join(parts) + ".")
    sys.exit(0)


if __name__ == "__main__":
    main()
