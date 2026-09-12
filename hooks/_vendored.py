#!/usr/bin/env python3
"""Vendored shadcn/ui primitive detection for the frontend PostToolUse checkers.

`shadcn add` copies registry source into the package, at the directory `components.json` names
in `aliases.ui`. Those files are CLI-owned: the house keeps them where the CLI wrote them, and a
later `add` resolves dependencies against that exact layout. So a size, style, label, copy or
test-coverage warning on `ui/sidebar.tsx` asks the model to rewrite (or split) upstream source,
and one Write of a stock primitive drew ten such warnings. Checkers ask `is_vendored_ui()` and
skip those checks there. Blocks install OUTSIDE aliases.ui and stay fully checked.

Resolution mirrors how the alias resolves at build time:
  1. `compilerOptions.paths` in tsconfig.json / tsconfig.app.json / jsconfig.json (JSONC, one
     `extends` hop) - covers `@/*` and monorepo `@workspace/ui/*` mappings;
  2. package.json `imports` for `#components/*` aliases;
  3. the `@/` convention: `<package>/src` when that directory exists, else `<package>`;
  4. a bare relative alias (`components/ui`) under the package.
When `aliases.ui` is absent, shadcn installs at `<aliases.components>/ui`.

Never raises: an unreadable or malformed config reads as "not vendored", so a broken
components.json degrades to every check running - never to silence. An alias broader than a
primitives folder is refused for the same reason: the package root or its src/, the
`aliases.components` directory itself, or a directory holding molecules/, organisms/ or
templates/. Any of those would exempt house components from six checkers.
"""

import json
import os
import re

_CONFIG = "components.json"
_TS_CONFIGS = ("tsconfig.json", "tsconfig.app.json", "jsconfig.json")
_HOUSE_TIERS = ("molecules", "organisms", "templates")
_JSONC_NOISE = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|,(?=\s*[}\]])', re.S)

_ROOT_BY_DIR = {}
_UI_DIR_BY_ROOT = {}


def is_vendored_ui(file_path):
    """True when `file_path` lives under the aliases.ui directory of its nearest components.json."""
    try:
        target = os.path.normcase(os.path.abspath(file_path))
        root = _package_root(os.path.dirname(target))
        ui_dir = _ui_dir(root) if root else ""
        return bool(ui_dir) and target.startswith(ui_dir + os.sep)
    except Exception:
        return False


def _package_root(start_dir):
    """Nearest ancestor holding components.json; the walk stops at the repository root (.git)."""
    if start_dir not in _ROOT_BY_DIR:
        found, current = None, start_dir
        while found is None:
            if os.path.isfile(os.path.join(current, _CONFIG)):
                found = current
            parent = os.path.dirname(current)
            if parent == current or os.path.exists(os.path.join(current, ".git")):
                break
            current = parent
        _ROOT_BY_DIR[start_dir] = found
    return _ROOT_BY_DIR[start_dir]


def _ui_dir(root):
    """Normalized absolute aliases.ui directory for a package root ("" when unresolvable)."""
    if root not in _UI_DIR_BY_ROOT:
        config = _read_jsonc(os.path.join(root, _CONFIG))
        aliases = config.get("aliases") if isinstance(config, dict) else None
        resolved = _resolve_alias(root, _ui_alias(aliases)) if isinstance(aliases, dict) else None
        ui_dir = os.path.normcase(os.path.normpath(resolved)) if resolved else ""
        _UI_DIR_BY_ROOT[root] = "" if _too_broad(root, aliases, ui_dir) else ui_dir
    return _UI_DIR_BY_ROOT[root]


def _too_broad(root, aliases, ui_dir):
    """An aliases.ui that would exempt house code, not just primitives: the package root or its
    src/, the `aliases.components` directory itself, or a directory holding the atomic tiers above
    primitives (molecules/, organisms/, templates/)."""
    if not ui_dir:
        return False
    if ui_dir in (os.path.normcase(root), os.path.normcase(os.path.join(root, "src"))):
        return True
    components = aliases.get("components")
    if isinstance(components, str) and components.strip():
        resolved = _resolve_alias(root, components.strip().rstrip("/"))
        if resolved and os.path.normcase(os.path.normpath(resolved)) == ui_dir:
            return True
    return any(os.path.isdir(os.path.join(ui_dir, tier)) for tier in _HOUSE_TIERS)


def _ui_alias(aliases):
    """aliases.ui, else `<aliases.components>/ui` (shadcn's own fallback), else `@/components/ui`."""
    for key, suffix in (("ui", ""), ("components", "/ui")):
        value = aliases.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().rstrip("/") + suffix
    return "@/components/ui"


def _resolve_alias(root, alias):
    """Absolute directory an import alias points at, or None when nothing maps it."""
    resolved = _via_ts_paths(root, alias) or _via_package_imports(root, alias)
    if resolved:
        return resolved
    if alias.startswith(("@/", "~/")):
        src = os.path.join(root, "src")
        return os.path.join(src if os.path.isdir(src) else root, alias[2:])
    if not alias.startswith(("@", "#", "~")):
        return os.path.join(root, alias)
    return None


def _via_ts_paths(root, alias):
    for name in _TS_CONFIGS:
        paths, base = _ts_paths(os.path.join(root, name), hops=1)
        hit = _match_mapping(paths, alias, base) if paths else None
        if hit:
            return hit
    return None


def _ts_paths(config_path, hops):
    """(paths, base dir) from a tsconfig, following one relative `extends` when it has none."""
    config = _read_jsonc(config_path)
    if not isinstance(config, dict):
        return None, None
    here = os.path.dirname(config_path)
    options = config.get("compilerOptions")
    options = options if isinstance(options, dict) else {}
    if isinstance(options.get("paths"), dict):
        return options["paths"], os.path.join(here, str(options.get("baseUrl") or "."))
    parent = config.get("extends")
    if hops and isinstance(parent, str) and parent.startswith("."):
        return _ts_paths(os.path.join(here, parent), hops - 1)
    return None, None


def _via_package_imports(root, alias):
    if not alias.startswith("#"):
        return None
    package = _read_jsonc(os.path.join(root, "package.json"))
    imports = package.get("imports") if isinstance(package, dict) else None
    return _match_mapping(imports, alias, root) if isinstance(imports, dict) else None


def _match_mapping(mapping, alias, base):
    """Apply a tsconfig `paths` / package.json `imports` map; the longest matching prefix wins."""
    for key in sorted(mapping, key=lambda k: len(str(k).split("*")[0]), reverse=True):
        rest = _wildcard_rest(str(key), alias)
        target = _first_target(mapping[key]) if rest is not None else None
        if target:
            return os.path.join(base, target.replace("*", rest, 1))
    return None


def _wildcard_rest(key, alias):
    """What `*` captures when `alias` matches `key` (`""` for an exact key); None on no match."""
    if "*" not in key:
        return "" if key == alias else None
    prefix, suffix = key.split("*", 1)
    fits = len(alias) >= len(prefix) + len(suffix)
    if fits and alias.startswith(prefix) and alias.endswith(suffix):
        return alias[len(prefix):len(alias) - len(suffix)]
    return None


def _first_target(targets):
    """First concrete path of a mapping value: a string, a fallback list, or a conditions object."""
    if isinstance(targets, str):
        return targets
    if isinstance(targets, list) and targets:
        return _first_target(targets[0])
    if isinstance(targets, dict) and targets:
        return _first_target(targets.get("default") or next(iter(targets.values())))
    return None


def _read_jsonc(path):
    """Parse JSON that may carry comments and trailing commas (tsconfig); None on any failure."""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            text = handle.read()
        cleaned = _JSONC_NOISE.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else "", text)
        return json.loads(cleaned)
    except (OSError, ValueError):
        return None
