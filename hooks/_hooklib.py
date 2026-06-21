#!/usr/bin/env python3
"""Shared helpers for Claude Code hooks.

Centralizes event parsing, file reading, path normalization, and the run loops
for advisory checkers (PostToolUse) and gates (PreToolUse) so individual hooks
stay small and behave consistently across platforms.

Contract:
  * Advisory checker  -> `check(event) -> list[str]`  (warning lines; never blocks)
  * PreToolUse gate    -> `check(event) -> None`        (calls deny()/ask() to block)

Run a checker standalone with `run_post_checker(check)`; run a gate with
`run_pre_blocker(check, fail_closed=...)`. Both always exit 0 — blocking is
communicated to Claude Code via the permissionDecision JSON, not the exit code.
"""

import json
import os
import sys


def load_event(stream=None):
    """Parse the hook JSON event from stdin.

    Returns {} on any parse error. A malformed or empty event must not crash a
    hook (fail-open at the parse boundary); gates add their own fail-closed
    policy around the check logic via run_pre_blocker.
    """
    if stream is None:
        stream = sys.stdin
    try:
        return json.load(stream)
    except (json.JSONDecodeError, EOFError, ValueError):
        return {}


def tool_name(event):
    return event.get("tool_name", "") or ""


def tool_input(event):
    return event.get("tool_input", {}) or {}


def get_file_path(event):
    return tool_input(event).get("file_path", "") or ""


def get_content(event):
    """The content being written (Write -> content, Edit -> new_string)."""
    data = tool_input(event)
    return data.get("content", "") or data.get("new_string", "") or ""


def normalize(path):
    """Normalize Windows backslashes to forward slashes for path matching."""
    return (path or "").replace("\\", "/")


def read_file(path):
    """Read a file as UTF-8, replacing undecodable bytes. Returns "" on error."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, IOError):
        return ""


def emit(warnings):
    """Print each warning line. Accepts a list or a single string."""
    if isinstance(warnings, str):
        warnings = [warnings]
    for line in warnings or []:
        print(line)


def run_post_checker(check):
    """Standalone runner for an advisory PostToolUse checker.

    `check(event)` returns a list of warning lines. Always exits 0; a crash in an
    advisory checker must never block the tool, so exceptions are swallowed.
    """
    event = load_event()
    try:
        warnings = check(event) or []
    except Exception:  # advisory: degrade silently, never block the edit
        warnings = []
    emit(warnings)
    sys.exit(0)


def _decision(decision, reason, event_name="PreToolUse"):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


def deny(reason, event_name="PreToolUse"):
    """Emit a PreToolUse 'deny' decision."""
    _decision("deny", reason, event_name)


def ask(reason, event_name="PreToolUse"):
    """Emit a PreToolUse 'ask' (confirm) decision."""
    _decision("ask", reason, event_name)


def run_pre_blocker(check, fail_closed=False, gate_label="check"):
    """Runner for a PreToolUse gate.

    `check(event)` inspects the event and calls deny()/ask() to block, then
    returns. On an unexpected exception inside check():
      * fail_closed=True  -> emit a deny so a security gate never silently passes
      * fail_closed=False -> allow (advisory gates degrade open)
    Always exits 0; the decision travels via the permissionDecision JSON.
    """
    event = load_event()
    try:
        check(event)
    except Exception as exc:
        if fail_closed:
            deny(
                f"BLOCKED: the {gate_label} hook errored and is failing closed "
                f"({type(exc).__name__}). This action was not evaluated for safety. "
                "Fix the hook or run the action manually outside Claude Code."
            )
    sys.exit(0)


# ---------------------------------------------------------------------------
# Framework detection — wrapper-directory-agnostic.
#
# Conventions auto-load from each framework's own layout and marker files, NOT
# from a forced top-level folder name. Rails code works under backend/, api/, or
# the repo root; a Vite app under web/, frontend/, or root; a Next app under
# next/, web/, or root; React Native under mobile/, app/, or root.
#
#   under(path, "app/models")      -> matches the canonical layout anywhere
#                                     (backend/app/models, api/app/models, app/models)
#   replace_first_segment(...)     -> map source->test path, preserving the wrapper
#   detect_framework(path)         -> 'rails'|'nextjs'|'vite'|'react-native'|None
#                                     via on-disk markers, with a path-structure fallback
# ---------------------------------------------------------------------------

def under(path, subpath):
    """True if `subpath` (canonical framework-internal dir, e.g. 'app/models')
    appears as consecutive directory segments anywhere in `path`, regardless of
    the wrapper directory. Pure string work — no disk access, works for files
    that do not exist yet."""
    norm = normalize(path).strip("/")
    needle = subpath.strip("/")
    return ("/" + needle + "/") in ("/" + norm + "/")


def under_any(path, subpaths):
    """True if `under(path, s)` holds for any s in `subpaths`."""
    return any(under(path, s) for s in subpaths)


def replace_first_segment(path, old_seg, new_seg):
    """Replace the first path segment equal to `old_seg` with `new_seg`,
    preserving the wrapper prefix and the rest of the path. Wrapper-agnostic
    source->test mapping: 'api/app/models/u.rb' + (app, spec) ->
    'api/spec/models/u.rb'. Returns the normalized path unchanged if `old_seg`
    is not a segment."""
    norm = normalize(path)
    old_seg = old_seg.strip("/")
    new_seg = new_seg.strip("/")
    parts = norm.split("/")
    for i, part in enumerate(parts):
        if part == old_seg:
            parts[i] = new_seg
            return "/".join(parts)
    return norm


_NEXT_CONFIGS = ("next.config.js", "next.config.mjs", "next.config.ts", "next.config.cjs")
_VITE_CONFIGS = ("vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.cjs")
_RN_CONFIGS = ("metro.config.js", "metro.config.cjs", "app.json")
_RAILS_MARKERS = ("Gemfile", os.path.join("config", "application.rb"), os.path.join("bin", "rails"))


def _ancestors(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            return
        current = parent


def _deepest_existing_dir(file_path):
    """Deepest existing directory at or above file_path (the file itself may not
    exist yet, e.g. a Write of a new file)."""
    base = os.path.dirname(os.path.abspath(file_path)) or os.path.abspath(".")
    for d in _ancestors(base):
        if os.path.isdir(d):
            return d
    return None


def _has(directory, rel):
    return os.path.exists(os.path.join(directory, rel))


def _package_json(directory):
    try:
        with open(os.path.join(directory, "package.json"), "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, IOError):
        return ""


def detect_framework(file_path):
    """Best-effort framework for an edited file, independent of the wrapper
    directory name. Returns 'rails' | 'nextjs' | 'vite' | 'react-native' | None.

    Walks up from the file to the nearest framework marker (next.config /
    vite.config / metro.config / app.json / package.json deps / Gemfile), and
    falls back to canonical path structure when no marker is resolvable on disk
    (e.g. relative path outside the project, or a bare scaffold)."""
    norm = normalize(file_path)
    start = _deepest_existing_dir(file_path)
    if start:
        for d in _ancestors(start):
            if any(_has(d, c) for c in _NEXT_CONFIGS):
                return "nextjs"
            if any(_has(d, c) for c in _VITE_CONFIGS):
                return "vite"
            if _has(d, "metro.config.js") or _has(d, "metro.config.cjs"):
                return "react-native"
            pkg = _package_json(d)
            if pkg:
                if '"next"' in pkg:
                    return "nextjs"
                if '"react-native"' in pkg:
                    return "react-native"
                if '"vite"' in pkg:
                    return "vite"
            if _has(d, "app.json") and ("expo" in _package_json(d) or under(norm, "src")):
                # app.json is a weak RN/Expo signal; only trust with corroboration
                if '"react-native"' in pkg or '"expo"' in pkg:
                    return "react-native"
            if any(_has(d, m) for m in _RAILS_MARKERS):
                return "rails"
            if _has(d, ".git"):
                break  # do not walk above the repository root

    # Path-structure fallback (no markers, or path not resolvable on disk).
    if norm.endswith(".rb") and under_any(norm, ("app", "lib", "db", "config", "spec")):
        return "rails"
    if under_any(norm, ("src/screens", "src/navigation")):
        return "react-native"
    if under(norm, "src/pages"):
        return "vite"
    if under(norm, "src/app") or (under(norm, "app") and (norm.endswith(".tsx") or norm.endswith(".jsx"))):
        return "nextjs"
    return None


def is_react_native(file_path):
    return detect_framework(file_path) == "react-native"


def is_web_react(file_path):
    """A browser React file (Vite SPA or Next.js) — distinct from React Native."""
    return detect_framework(file_path) in ("vite", "nextjs")
