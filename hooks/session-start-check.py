#!/usr/bin/env python3
"""
SessionStart hook: Verify development environment is ready.

Three jobs:
1. Git status — repository, branch, working tree state.
2. Framework-area detection — which conventions apply here (wrapper-agnostic).
3. **The sentinel check** — verify the layer-4 permission floor is actually present
   in the consuming project. A plugin CANNOT ship `permissions`, so the deny list
   must be copied by hand into each project's `.claude/settings.json`. When it is
   skipped, every visible signal (skills load, hooks fire) says "protected" while
   the innermost enforcement ring is silently absent — the "plugin trap". This turns
   that silent structural absence into a loud warning on every session until fixed.

Always exits 0 — informational only, never blocks the session.
"""
import json
import os
import subprocess
import sys

# Imported defensively: this hook carries the layer-4 permission sentinel, and "a plugin
# without this check is distributing a false sense of protection, which is worse than
# distributing none" (Ch. 13). It must still run if the shared lib cannot be imported, so
# every use of `hooklib` here falls back rather than raising.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import _hooklib as hooklib
except Exception:  # pragma: no cover - defensive
    hooklib = None


def protected_branches():
    if hooklib is None:
        return list(("main", "master", "develop"))
    return hooklib.protected_branches()

# Relevant convention skills per framework area (wrapper-directory-agnostic detection).
AREA_RULES = {
    "rails": "std-rails-conventions, std-phlex-conventions, std-api-design, std-database, std-monitoring, std-clean-architecture",
    "nextjs": "std-nextjs, std-accessibility, std-i18n, std-testing, std-clean-architecture",
    "vite": "std-reactjs, std-accessibility, std-i18n, std-testing, std-clean-architecture",
    "react-native": "std-react-native, std-accessibility, std-i18n, std-clean-architecture",
    "django": "std-python, std-django, std-python-performance, std-api-design, std-database, std-clean-architecture",
    "fastapi": "std-python, std-fastapi, std-python-performance, std-api-design, std-database, std-clean-architecture",
}

# Fallback sentinels: a representative sample of the critical tiers (secrets,
# privilege, remote-exec). Used ONLY when the plugin's reference floor cannot be
# read. The authoritative check diffs against the plugin's own reference settings
# (see _plugin_reference_floor) — a hardcoded sample can prove a floor is ABSENT
# but never that it is CURRENT, and a floor that silently went stale is the same
# invisible gap in slower motion.
PERMISSION_SENTINELS = [
    "Read(**/.env)",
    "Read(**/secrets/**)",
    "Bash(sudo:*)",
    "Bash(curl * | bash)",
]


def _plugin_reference_floor():
    """The authoritative deny floor — the plugin's own reference `.claude/settings.json`.

    Located relative to THIS file (hooks/ -> plugin root) so it needs no environment
    variable and works under --plugin-dir, a marketplace install, or a plain clone.
    Returns the deny list, or None when it cannot be read (then we fall back to the
    hardcoded sample).
    """
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ref = os.path.join(root, ".claude", "settings.json")
        with open(ref, "r", encoding="utf-8") as handle:
            deny = json.load(handle).get("permissions", {}).get("deny", [])
        return deny or None
    except Exception:
        return None


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


def check_permission_sentinels(cwd):
    """Verify the layer-4 permission floor was copied into the consuming project.

    A plugin cannot ship `permissions`, so this reads the PROJECT's own
    .claude/settings.json (never the plugin's) and reports any missing sentinel
    deny rules. Returns a warning string, or "" when the floor is present.
    """
    settings_path = os.path.join(cwd, ".claude", "settings.json")
    if not os.path.exists(settings_path):
        return (
            "GOVERNANCE GAP: no .claude/settings.json in this project — the `sdh` plugin "
            "cannot ship permission rules, so the deny floor (secrets, privilege "
            "escalation, remote-exec) is ABSENT. Skills and hooks still fire, which hides "
            "the gap. Copy the `permissions` block from the plugin's .claude/settings.json "
            "before doing sensitive work."
        )
    try:
        with open(settings_path, "r", encoding="utf-8") as handle:
            deny = json.load(handle).get("permissions", {}).get("deny", []) or []
    except Exception:
        return (
            "GOVERNANCE GAP: .claude/settings.json could not be parsed — the permission "
            "floor cannot be verified. Fix the file, then confirm the `permissions.deny` "
            "block is present."
        )

    present = set(deny)

    # Prefer the plugin's own reference floor: it is always current, so this catches a
    # STALE floor (copied once, never updated as the plugin's deny list grew) — not just
    # a missing one. Fall back to the hardcoded sample if the reference is unreadable.
    reference = _plugin_reference_floor()
    if reference:
        missing = [r for r in reference if r not in present]
        if missing:
            stale = bool(present)  # they copied something, just not the current floor
            head = (
                "GOVERNANCE GAP: this project's permission floor is STALE — it was copied "
                "from an older version of the `sdh` plugin and is missing rules added since."
                if stale else
                "GOVERNANCE GAP: this project's permission deny floor is missing."
            )
            shown = ", ".join(missing[:8]) + (f" (+{len(missing) - 8} more)" if len(missing) > 8 else "")
            return (
                f"{head} A plugin cannot ship `permissions`, so these must be copied by hand; "
                f"until then the hooks carry rules they were not meant to carry alone. "
                f"Missing {len(missing)} of {len(reference)}: {shown}. "
                f"Re-copy the `permissions` block from the plugin's .claude/settings.json."
            )
        return ""

    missing = [s for s in PERMISSION_SENTINELS if s not in present]
    if missing:
        return (
            "GOVERNANCE GAP: permission deny rules missing from .claude/settings.json — "
            "the `sdh` plugin cannot ship these, so they must be copied by hand. The "
            "hooks are carrying rules they were not meant to carry alone. Missing: "
            + ", ".join(missing)
            + ". Copy the `permissions` block from the plugin's .claude/settings.json."
        )
    return ""


def main():
    cwd = launch_dir()

    # Layer-4 sentinel runs regardless of git state — a missing permission floor
    # matters even outside a repo, and it must never be hidden behind an early exit.
    gap = check_permission_sentinels(cwd)
    if gap:
        print(gap)

    # Check if we're in a git repo
    toplevel = run_git(["rev-parse", "--show-toplevel"])
    if not toplevel:
        print("Environment: not a git repository.")
        sys.exit(0)

    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    status = run_git(["status", "--porcelain"])
    tree_state = "dirty working tree" if status else "clean working tree"

    parts = [f"Environment: {branch}", tree_state]

    if branch in protected_branches():
        parts.append("note: on protected branch — use a feature branch for new work")

    area = detect_area(cwd)
    if area in AREA_RULES:
        # "scoped", not "auto-load": paths: limits WHEN a skill may load; Claude
        # still chooses to read it (the v3.1.0 docs correction, applied here too).
        parts.append(f"detected {area} area — the scoped convention skills for it: {AREA_RULES[area]}")

    print(", ".join(parts) + ".")
    sys.exit(0)


if __name__ == "__main__":
    main()
