#!/usr/bin/env python3
"""Framework detection and project-relative path matching, wrapper-directory-agnostic.

Split out of `_hooklib.py` by responsibility. `_hooklib` re-exports every name here, so hooks keep
calling `hooklib.under(...)`, `hooklib.rel_to_root(...)` and `hooklib.detect_framework(...)`.

Conventions auto-load from each framework's own layout and marker files, NOT from a forced
top-level folder name. Rails code works under backend/, api/, or the repo root; a Vite app under
web/, frontend/, or root; a Next app under next/, web/, or root; React Native under mobile/, app/,
or root; a Python service (FastAPI or Django) under svc/, api/, ml/, or root.

  under(path, "app/models")      -> matches the canonical layout inside the project
                                    (backend/app/models, api/app/models, app/models)
  replace_first_segment(...)     -> map source->test path, preserving the wrapper
  project_root / rel_to_root     -> the directory that matching is relative to
  detect_framework(path)         -> 'rails'|'nextjs'|'vite'|'react-native'
                                    |'django'|'fastapi'|None
                                    via on-disk markers, with a path-structure fallback

The running hook's event `cwd` is the last project-root fallback. `_hooklib` hands every event it
parses to `set_current_event`, so this module never imports `_hooklib` (no import cycle).
"""

import functools
import os
import re
import sys

_CURRENT_EVENT = [{}]  # [the event the running hook parsed]; `_hooklib` keeps it current
_PACKAGE_MARKERS = ("Gemfile", "package.json", "pyproject.toml", "manage.py")


def set_current_event(event):
    """Record the event the running hook parsed: its `cwd` is a project-root and audit fallback."""
    _CURRENT_EVENT[0] = event if isinstance(event, dict) else {}


def normalize(path):
    """Normalize Windows backslashes to forward slashes for path matching."""
    return (path or "").replace("\\", "/")


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, IOError):
        return ""


def under(path, subpath):
    """True if `subpath` (canonical framework-internal dir, e.g. 'app/models')
    appears as consecutive directory segments in `path` BELOW its project root,
    regardless of the wrapper directory. Works for files that do not exist yet.

    An absolute path is matched relative to `project_root`: a directory ABOVE the project (Docker's
    WORKDIR /app, a C:\\src checkout, a scratch folder named `app`) is not framework structure,
    yet it made every Rails file under /app "untested" and turned Vite hooks into screens. A
    relative path is pure string work, exactly as before."""
    norm = rel_to_root(path).strip("/")
    needle = subpath.strip("/")
    return ("/" + needle + "/") in ("/" + norm + "/")


def under_any(path, subpaths):
    """True if `under(path, s)` holds for any s in `subpaths`."""
    return any(under(path, s) for s in subpaths)


def replace_first_segment(path, old_seg, new_seg):
    """Replace the first path segment equal to `old_seg` with `new_seg`,
    preserving the wrapper prefix and the rest of the path. Wrapper-agnostic
    source->test mapping: 'api/app/models/u.rb' + (app, spec) ->
    'api/spec/models/u.rb'. Only segments below the project root are candidates,
    so an `app` ancestor above the project is never the one rewritten. Returns the
    normalized path unchanged if `old_seg` is not a segment."""
    norm = normalize(path)
    rel = rel_to_root(path)
    prefix = norm[: len(norm) - len(rel)]
    parts = rel.split("/")
    for i, part in enumerate(parts):
        if part == old_seg.strip("/"):
            parts[i] = new_seg.strip("/")
            return prefix + "/".join(parts)
    return norm


def project_root(path, event=None):
    """The directory framework structure is matched relative to, or None.

    The nearest ancestor holding a package marker (Gemfile, package.json, pyproject.toml,
    manage.py), never walking above the repository root (.git). Without either, CLAUDE_PROJECT_DIR
    or the event's `cwd` when it contains the file. None for a relative path.
    """
    if not path or not os.path.isabs(path):
        return None
    start = _deepest_existing_dir(path)
    return (_package_root(start) if start else None) or _session_root(path, event)


def rel_to_root(path, event=None):
    """`path` normalized and relative to `project_root`, or just normalized when there is none."""
    norm = normalize(path)
    root = project_root(path, event)
    prefix = normalize(root).rstrip("/") if root else ""
    if not prefix or not _fold(norm).startswith(_fold(prefix) + "/"):
        return norm
    return norm[len(prefix) + 1:]


@functools.lru_cache(maxsize=512)
def _package_root(start):
    for directory in _ancestors(start):
        if _has(directory, ".git") or any(_has(directory, m) for m in _PACKAGE_MARKERS):
            return directory
    return None


def _session_root(path, event=None):
    event = event if isinstance(event, dict) else _CURRENT_EVENT[0]
    for candidate in (os.environ.get("CLAUDE_PROJECT_DIR"), event.get("cwd")):
        prefix = normalize(candidate).rstrip("/") if isinstance(candidate, str) else ""
        if prefix and _fold(normalize(path)).startswith(_fold(prefix) + "/"):
            return candidate
    return None


def _fold(text):
    return text.lower() if os.name == "nt" or sys.platform == "darwin" else text


_NEXT_CONFIGS = ("next.config.js", "next.config.mjs", "next.config.ts", "next.config.cjs")
_VITE_CONFIGS = ("vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.cjs")
_RN_CONFIGS = ("metro.config.js", "metro.config.cjs", "app.json")
_RAILS_MARKERS = ("Gemfile", os.path.join("config", "application.rb"), os.path.join("bin", "rails"))
# A bare Gemfile is NOT a Rails app when a JS marker sits beside it: React Native/Expo roots carry
# a CocoaPods Gemfile. Only the app's own files break a bundler/backend tie.
_RAILS_APP_MARKERS = (os.path.join("config", "application.rb"), os.path.join("bin", "rails"))
_BACKEND_EXTENSIONS = (".rb", ".rake", ".erb", ".py")


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
    return _read_text(os.path.join(directory, "package.json"))


def _pyproject(directory):
    """pyproject.toml content, lowercased for dependency grepping ("" if unreadable).

    Lowercased because dependency tables write both `django` and `Django`; the
    grep is for a dependency NAME, and pip/uv names are case-insensitive."""
    return _read_text(os.path.join(directory, "pyproject.toml")).lower()


def _pyproject_dep(pyp, name):
    """True when `name` appears as a DEPENDENCY in lowercased pyproject content —
    a quoted PEP 621 requirement ("django>=5.0", "fastapi[standard]") or a Poetry
    table key (django = "^5.0"). A plain substring grep matched prose and comments
    ("# not a django project") and misclassified plain libraries; anchoring to the
    two dependency spellings is the pyproject analog of package.json's '"next"'."""
    return bool(
        re.search(r"[\"']" + name + r"[\"'\[><=~!;@ ]", pyp)
        or re.search(r"^\s*" + name + r"\s*=", pyp, re.M)
    )


def detect_framework(file_path):
    """Best-effort framework for an edited file, independent of the wrapper
    directory name. Returns 'rails' | 'nextjs' | 'vite' | 'react-native' |
    'django' | 'fastapi' | None.

    Walks up from the file to the nearest framework marker (next.config /
    vite.config / metro.config / app.json / package.json deps / Gemfile /
    manage.py / pyproject.toml deps / alembic.ini), and falls back to canonical
    path structure when no marker is resolvable on disk (e.g. relative path
    outside the project, or a bare scaffold). A directory with both a bundler
    and a backend marker (vite_ruby, django-vite) answers per file: see
    `_label_for_dir`."""
    start = _deepest_existing_dir(file_path)
    for directory in _ancestors(start) if start else ():
        label = _label_for_dir(directory, file_path)
        if label:
            return label
        if _has(directory, ".git"):
            break  # do not walk above the repository root
    return _structure_label(normalize(file_path))


def _label_for_dir(directory, file_path):
    """The framework one directory's markers declare for this file, or None.

    A Rails root using vite_ruby, or a Django root using django-vite, carries a bundler marker AND
    a backend marker. Checking the bundler first classified app/models/user.rb as 'vite' and made
    SessionStart announce std-reactjs for a Rails app. The file decides the tie: Ruby/Python files
    and extensionless probes (SessionStart's `__session__`) take the backend label, the rest the
    bundler's.
    """
    js = _js_label(directory)
    backend = _backend_label(directory, strict_rails=bool(js))
    if js and backend:
        ext = os.path.splitext(os.path.basename(normalize(file_path)))[1]
        return backend if ext in _BACKEND_EXTENSIONS or not ext else js
    return js or backend


def _js_label(directory):
    if any(_has(directory, c) for c in _NEXT_CONFIGS):
        return "nextjs"
    if any(_has(directory, c) for c in _VITE_CONFIGS):
        return "vite"
    if _has(directory, "metro.config.js") or _has(directory, "metro.config.cjs"):
        return "react-native"
    pkg = _package_json(directory)
    for dependency, label in (('"next"', "nextjs"), ('"react-native"', "react-native"),
                              ('"vite"', "vite")):
        if dependency in pkg:
            return label
    # app.json is a weak RN/Expo signal; only trust it with an expo dependency beside it
    if _has(directory, "app.json") and '"expo"' in pkg:
        return "react-native"
    return None


def _backend_label(directory, strict_rails=False):
    """Rails first: it is the primary backend, so on the (unlikely) mixed root Rails wins the tie."""
    if any(_has(directory, m) for m in (_RAILS_APP_MARKERS if strict_rails else _RAILS_MARKERS)):
        return "rails"
    if _has(directory, "manage.py"):
        # Django's canonical marker (a legacy Flask-Script manage.py
        # would also match — Flask is off-stack).
        return "django"
    pyp = _pyproject(directory)
    # Dependency-anchored grep (see _pyproject_dep). fastapi first: a FastAPI service never
    # DEPENDS on django; a Django repo's "migrate to fastapi" comment does not count.
    if pyp and _pyproject_dep(pyp, "fastapi"):
        return "fastapi"
    if pyp and _pyproject_dep(pyp, "django"):
        return "django"
    if _has(directory, "alembic.ini") and _has(directory, os.path.join("app", "main.py")):
        return "fastapi"  # house FastAPI layout: app/main.py + alembic
    return None


def _structure_label(norm):
    """Path-structure fallback (no markers, or path not resolvable on disk)."""
    if norm.endswith(".rb") and under_any(norm, ("app", "lib", "db", "config", "spec")):
        return "rails"
    if under_any(norm, ("src/screens", "src/navigation")):
        return "react-native"
    if under(norm, "src/pages"):
        return "vite"
    # The .py branch must run BEFORE the src/app Next.js rule: `src/app/` is also the Python
    # src-layout for a package named `app`, and the Next rule has no extension guard.
    if norm.endswith(".py"):
        # Django-idiomatic filenames and its migrations dirs (alembic's default is alembic/versions).
        if norm.endswith("/manage.py") or norm == "manage.py" or under(norm, "migrations"):
            return "django"
        # House FastAPI package shape (std-fastapi): routers/schemas under app/.
        if under_any(norm, ("app/routers", "app/api", "app/schemas")) or norm.endswith("/app/main.py"):
            return "fastapi"
        return None
    if under(norm, "src/app") or (under(norm, "app") and (norm.endswith(".tsx") or norm.endswith(".jsx"))):
        return "nextjs"
    return None


def is_react_native(file_path):
    return detect_framework(file_path) == "react-native"


def is_web_react(file_path):
    """A browser React file (Vite SPA or Next.js) — distinct from React Native."""
    return detect_framework(file_path) in ("vite", "nextjs")
