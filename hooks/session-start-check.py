#!/usr/bin/env python3
"""
SessionStart hook: environment state for the model, a governance warning the developer sees.

Three jobs:
1. Git status and framework-area detection (wrapper-agnostic): which conventions apply here.
2. **The sentinel check.** A plugin CANNOT ship `permissions`, so the deny floor must reach a
   settings source Claude Code reads. When it is missing, every visible signal (skills load, hooks
   fire) still says "protected" while the innermost ring is absent: the "plugin trap".
3. **Delivery.** Output is one JSON object. `hookSpecificOutput.additionalContext` carries the
   environment line to the model. The gap also goes out as `systemMessage`, which the hooks docs
   define as the "warning message shown to the user". additionalContext "doesn't appear as a chat
   message in the interface", so the old plain print reached the model but never the developer
   this docstring promised a loud warning to.

Sources the floor may live in (settings docs): project `.claude/settings.json` and
`.claude/settings.local.json` (in the launch dir, the repo root and, from a worktree, the main
checkout), user settings (`$CLAUDE_CONFIG_DIR` or `~/.claude`), and file-based managed settings
(`managed-settings.json` plus `managed-settings.d/*.json` under `/Library/Application
Support/ClaudeCode`, `/etc/claude-code`, or `%ProgramFiles%/ClaudeCode` on Windows, never the legacy
ProgramData path). MDM, registry and server-managed policy are invisible to a hook, and the
message says so rather than claiming the floor is absent everywhere. SDH_USER_SETTINGS and
SDH_MANAGED_SETTINGS point the user and managed files elsewhere (drop-ins are read from the managed
file's sibling `managed-settings.d/`), which keeps tests independent of the machine.

Tiers: only a missing secrets, privilege, remote-exec or infrastructure rule is a GOVERNANCE GAP,
and a `PowerShell(...)` mirror counts exactly like the `Bash(...)` rule it mirrors: a Bash rule
never matches the PowerShell tool. The build-artifact Read denies are "a context-economy concern,
NOT a security one" (the managed template), so their absence is a note to the model, not a banner.
`Read(**/*secret*)` is the project tier: required like any security rule, except where managed
settings carry the whole managed tier (`managed_tier`), because the template deliberately keeps it
out of non-overridable policy; there its absence is a note too. CI's managed-floor-sync job checks
the template against the same `managed_tier`.

Always exits 0: informational only, never blocks the session.
"""
import glob
import json
import os
import re
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
    "nextjs": "std-nextjs, std-shadcn-ui, std-accessibility, std-i18n, std-testing, std-clean-architecture",
    "vite": "std-reactjs, std-shadcn-ui, std-accessibility, std-i18n, std-testing, std-clean-architecture",
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
    "PowerShell(Invoke-Expression:*)",
]

# The context-economy tier of the reference floor. Any rule NOT matched here is critical, so a
# rule added to the floor later is treated as security until someone says otherwise.
ADVISORY_RULE = re.compile(
    r"^Read\(\*\*/(?:dist|build|\.next|coverage|vendor|public/assets|public/packs|tmp/cache)/\*\*\)$"
    r"|^Read\(\*\*/\*\.(?:generated\.\*|min\.js|min\.css)\)$"
)

# The project tier: security rules the managed template leaves to project settings. A broad name
# glob is a team's call, not the catastrophic tier non-overridable org policy is limited to.
PROJECT_TIER_RULE = re.compile(r"^Read\(\*\*/\*secret\*\)$")


def managed_tier(reference):
    """The rules a managed-settings floor must carry: the reference floor minus the context-economy
    and project tiers. CI's managed-floor-sync job requires exactly these of the managed template."""
    return [rule for rule in reference if not ADVISORY_RULE.match(rule) and not PROJECT_TIER_RULE.match(rule)]


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


def run_git(cwd, args, timeout=3):
    """Lock-free git stdout for `cwd` (unstripped), or "" on failure: `_teamgate.run_git`, shared
    with the team gates. Imported here, defensively: git state is optional, the sentinel is not."""
    try:
        from _teamgate import run_git as lock_free_git
        code, out = lock_free_git(cwd, args, timeout)
    except Exception:
        return ""
    return out if code == 0 else ""


def read_event():
    """The SessionStart event (`cwd`, `source`, ...), or {} when stdin is not a JSON object."""
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


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


def project_roots(cwd):
    """Directories whose .claude/ may hold project settings: launch dir, repo root, main checkout."""
    roots = [cwd]
    lines = run_git(cwd, ["rev-parse", "--show-toplevel", "--git-common-dir"]).splitlines()
    if len(lines) >= 2:
        roots.append(lines[0])
        common = os.path.abspath(os.path.join(cwd, lines[1]))
        if os.path.basename(common) == ".git":
            roots.append(os.path.dirname(common))
    unique = {}
    for root in roots:
        unique.setdefault(os.path.normcase(os.path.abspath(root)), root)
    return list(unique.values())


def managed_settings_files():
    primary = os.environ.get("SDH_MANAGED_SETTINGS")
    if not primary and sys.platform == "darwin":
        primary = "/Library/Application Support/ClaudeCode/managed-settings.json"
    elif not primary and os.name == "nt":
        program_files = os.environ.get("ProgramFiles") or "C:/Program Files"
        primary = os.path.join(program_files, "ClaudeCode", "managed-settings.json")
    elif not primary:
        primary = "/etc/claude-code/managed-settings.json"
    dropins = sorted(glob.glob(os.path.join(os.path.dirname(primary), "managed-settings.d", "*.json")))
    return [primary] + dropins


def settings_files(roots):
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    files = [os.path.join(root, ".claude", name)
             for root in roots for name in ("settings.json", "settings.local.json")]
    files.append(os.environ.get("SDH_USER_SETTINGS") or os.path.join(config_dir, "settings.json"))
    return files + managed_settings_files()


def read_deny(path):
    """(deny rules, unparseable) for one settings file; ([], False) when it does not exist."""
    if not os.path.isfile(path):
        return [], False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            deny = json.load(handle).get("permissions", {}).get("deny", []) or []
        return [rule for rule in deny if isinstance(rule, str)], False
    except Exception:
        return [], True


def gap_message(missing, reference, present, broken):
    ordered = sorted(missing, key=lambda rule: bool(ADVISORY_RULE.match(rule)))
    shown = ", ".join(ordered[:8]) + (f" (+{len(missing) - 8} more)" if len(missing) > 8 else "")
    if present & set(reference):
        head = ("GOVERNANCE GAP: the permission floor across this project's settings sources is "
                "STALE or incomplete: it holds part of the current `sdh` floor (a copy from an older "
                "plugin version, or an org policy with a narrower list) and lacks the rules below.")
    else:
        head = ("GOVERNANCE GAP: no permission deny floor in project settings (.claude/settings.json, "
                ".claude/settings.local.json), user settings or a file-based managed-settings file, "
                "so the deny floor (secrets, privilege escalation, remote-exec) is ABSENT unless MDM "
                "or server-managed policy supplies it. Skills and hooks still fire, which hides the gap.")
    parse = f" Could not parse {', '.join(broken)}, so its rules were not counted." if broken else ""
    return (f"{head}{parse} A plugin cannot ship `permissions`, so these must be copied by hand or "
            f"deployed org-wide (.claude/managed-settings.template.json); until then the hooks carry "
            f"rules they were not meant to carry alone. Missing {len(missing)} of {len(reference)}: "
            f"{shown}. Copy the `permissions` block from the plugin's .claude/settings.json before "
            f"doing sensitive work.")


def _union(paths):
    """(deny rules across `paths`, the paths among them that would not parse)."""
    present, broken = set(), []
    for path in paths:
        rules, unparseable = read_deny(path)
        present.update(rules)
        if unparseable:
            broken.append(path)
    return present, broken


def _left_to_projects(reference, managed):
    """Project-tier rules that are not required: the managed settings carry the whole managed tier."""
    tier = managed_tier(reference)
    if not tier or not managed.issuperset(tier):
        return set()
    return {rule for rule in reference if PROJECT_TIER_RULE.match(rule)}


def floor_note(quiet, left_to_projects):
    """The model-facing note for missing rules that are not a GOVERNANCE GAP; "" when none."""
    advisory = [rule for rule in quiet if rule not in left_to_projects]
    project = [rule for rule in quiet if rule in left_to_projects]
    notes = []
    if advisory:
        notes.append("Permission floor note: the context-economy Read denies are missing from every "
                     f"readable settings source ({', '.join(advisory)}), so build artifacts are "
                     "readable. That costs context, not security.")
    if project:
        notes.append("Permission floor note: the managed settings carry the org's catastrophic-tier "
                     f"floor, which leaves {', '.join(project)} to project settings, and no settings "
                     "source holds it, so files matching it are readable. Copy it from the plugin's "
                     ".claude/settings.json into the project to deny those reads.")
    return " ".join(notes)


def check_permission_sentinels(cwd, roots=None):
    """(gap warning for the developer, floor note for the model); "" when none.

    Reads every settings source this machine exposes (never the plugin's own file as a source)
    and diffs their union against the plugin's reference floor."""
    present, broken = _union(settings_files(roots or [cwd]))
    managed, _unparseable = _union(managed_settings_files())
    reference = _plugin_reference_floor() or PERMISSION_SENTINELS
    missing = [rule for rule in reference if rule not in present]
    left_to_projects = _left_to_projects(reference, managed)
    quiet = [rule for rule in missing if ADVISORY_RULE.match(rule) or rule in left_to_projects]
    if len(quiet) < len(missing):
        return gap_message(missing, reference, present, broken), ""
    return "", floor_note(quiet, left_to_projects)


def environment_line(cwd):
    status = run_git(cwd, ["status", "--porcelain=v2", "--branch"], timeout=5)
    if not status:
        return "Environment: not a git repository."
    lines = status.splitlines()
    branch = next((l[len("# branch.head "):] for l in lines if l.startswith("# branch.head ")), "unknown")
    dirty = any(line and not line.startswith("#") for line in lines)
    parts = [f"Environment: {branch}", "dirty working tree" if dirty else "clean working tree"]
    if branch in protected_branches():
        parts.append("note: on protected branch, use a feature branch for new work")
    area = detect_area(cwd)
    if area in AREA_RULES:
        # "scoped", not "auto-load": paths: limits WHEN a skill may load; Claude
        # still chooses to read it (the v3.1.0 docs correction, applied here too).
        parts.append(f"detected {area} area; the scoped convention skills for it: {AREA_RULES[area]}")
    return ", ".join(parts) + "."


def main():
    data = read_event()
    cwd = str(data.get("cwd") or os.getcwd())
    # Layer-4 sentinel runs regardless of git state: a missing permission floor matters even
    # outside a repo, and it must never be hidden behind an early exit.
    gap, note = check_permission_sentinels(cwd, project_roots(cwd))
    context = "\n".join(part for part in (environment_line(cwd), gap, note) if part)
    output = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    if gap and data.get("source") != "compact":
        output["systemMessage"] = gap  # the developer sees it; a mid-session compaction does not repeat it
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
