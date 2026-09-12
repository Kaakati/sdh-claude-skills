#!/usr/bin/env python3
"""Direct-dependency extraction from manifests, for the competing-mechanism detectors (CM1).

    Gemfile                  gem "x" (groups from `group ... do` blocks and `group:` options)
    package.json             dependencies / devDependencies / peerDependencies / optionalDependencies
    pyproject.toml           PEP 621 dependencies and optional-dependencies, [dependency-groups],
                             Poetry dependencies and groups (tomllib, or the `_archtoml` subset)
    requirements*.txt        one requirement per line; `-r` includes are noted, not followed
    config/importmap.rb      pin "x" (a Rails importmap is the app's JS manifest)
    pnpm-workspace.yaml      presence marks a workspace root (tooling concerns only)

Every parser returns {"deps": [{ecosystem, package, group, line}], "workspace_root": bool,
"errors": [..]}. Transitive dependencies (lockfiles) are never counted. Names are normalized per
ecosystem: PyPI per PEP 503, npm and RubyGems as written.
"""
import json
import os
import re

import _archtoml

DEV_GROUPS = ("dev", "development", "test", "tests", "testing", "lint", "typing", "docs")
_GEM = re.compile(r"""^\s*gem\s+["']([^"']+)["']([^\n]*)""", re.M)
_GROUP_OPEN = re.compile(r"^\s*group\s+([^\n]*?)\s+do\b", re.M)
_GEM_GROUP = re.compile(r"""\bgroups?:\s*(\[[^\]]*\]|:\w+|["']\w+["'])""")
_PIN = re.compile(r"""^\s*pin\s+["']([^"']+)["']""", re.M)
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_PEP508_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize_package(ecosystem, name):
    name = (name or "").strip()
    if ecosystem == "pypi":
        return re.sub(r"[-_.]+", "-", name).lower()
    return name


def _line_at(text, offset):
    return text.count("\n", 0, offset) + 1


def _group_of(label):
    words = re.findall(r"\w+", label or "")
    if not words:
        return "prod"
    return "dev" if all(w.lower() in DEV_GROUPS for w in words) else ("dev" if words[0].lower() in DEV_GROUPS else "optional")


def _dep(ecosystem, package, group, line):
    return {"ecosystem": ecosystem, "package": normalize_package(ecosystem, package), "group": group, "line": line}


def parse_gemfile(text):
    """Gems with the innermost `group ... do` label (or an inline `group:` option) as their group."""
    blocks = []
    for match in _GROUP_OPEN.finditer(text):
        end = re.compile(r"^" + re.escape(re.match(r"^\s*", match.group(0)).group(0)) + r"end\b", re.M).search(text, match.end())
        blocks.append((match.start(), end.end() if end else len(text), _group_of(match.group(1))))
    deps = []
    for match in _GEM.finditer(text):
        inline = _GEM_GROUP.search(match.group(2))
        group = _group_of(inline.group(1)) if inline else "prod"
        for start, end, label in blocks:
            if start < match.start() < end and not inline:
                group = label
        deps.append(_dep("rubygems", match.group(1), group, _line_at(text, match.start())))
    return {"deps": deps, "workspace_root": False, "errors": []}


def _json_key_line(text, section_offset, name):
    found = text.find('"%s"' % name, section_offset)
    return _line_at(text, found) if found >= 0 else 1


def parse_package_json(text):
    try:
        data = json.loads(text)
    except ValueError as exc:
        return {"deps": [], "workspace_root": False, "errors": ["package.json: %s" % exc]}
    if not isinstance(data, dict):
        return {"deps": [], "workspace_root": False, "errors": ["package.json is not an object"]}
    deps = []
    for section, group in (("dependencies", "prod"), ("devDependencies", "dev"),
                           ("peerDependencies", "peer"), ("optionalDependencies", "optional")):
        table = data.get(section)
        offset = text.find('"%s"' % section)
        for name in (table if isinstance(table, dict) else {}):
            deps.append(_dep("npm", name, group, _json_key_line(text, max(offset, 0), name)))
    return {"deps": deps, "workspace_root": "workspaces" in data, "errors": []}


def _requirement_name(entry):
    match = _PEP508_NAME.match(entry) if isinstance(entry, str) else None
    return match.group(1) if match else None


def _pyproject_groups(data):
    """(group label, [requirement strings]) for every dependency list pyproject.toml can hold."""
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    yield "prod", project.get("dependencies") or []
    for name, items in (project.get("optional-dependencies") or {}).items():
        yield _group_of(name), items
    for name, items in (data.get("dependency-groups") or {}).items():
        yield _group_of(name), items
    poetry = ((data.get("tool") or {}).get("poetry") or {}) if isinstance(data.get("tool"), dict) else {}
    yield "prod", [k for k in (poetry.get("dependencies") or {}) if k.lower() != "python"]
    yield "dev", list(poetry.get("dev-dependencies") or {})
    for name, group in (poetry.get("group") or {}).items():
        yield _group_of(name), list((group or {}).get("dependencies") or {}) if isinstance(group, dict) else []


def parse_pyproject(text, force_subset=False):
    data, errors = _archtoml.parse_toml(text, force_subset)
    deps = []
    for group, items in _pyproject_groups(data if isinstance(data, dict) else {}):
        for entry in items if isinstance(items, list) else []:
            name = _requirement_name(entry)
            if name:
                found = re.search(r"""["']?%s\b""" % re.escape(name), text)
                deps.append(_dep("pypi", name, group, _line_at(text, found.start()) if found else 1))
    return {"deps": deps, "workspace_root": False, "errors": ["pyproject.toml %s" % e for e in errors]}


def parse_requirements(text, rel):
    base = os.path.basename(rel).lower()
    group = "dev" if re.search(r"dev|test|lint|doc", base + os.path.dirname(rel).lower()) else "prod"
    deps, notes = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-r", "--requirement", "-c")):
            notes.append("line %d: include not followed (%s)" % (number, line))
            continue
        match = _REQUIREMENT.match(line) if not line.startswith("-") else None
        if match:
            deps.append(_dep("pypi", match.group(1), group, number))
    return {"deps": deps, "workspace_root": False, "errors": notes}


def parse_importmap(text):
    deps = [_dep("npm", m.group(1), "importmap", _line_at(text, m.start())) for m in _PIN.finditer(text)]
    return {"deps": deps, "workspace_root": False, "errors": []}


def is_manifest(rel):
    base = os.path.basename(rel)
    if base in ("Gemfile", "package.json", "pyproject.toml", "pnpm-workspace.yaml"):
        return True
    if re.match(r"requirements[\w.-]*\.(txt|in)$", base):
        return True
    return rel.replace("\\", "/").endswith("config/importmap.rb")


def parse_manifest(rel, text):
    """Dispatch on the manifest's file name; unknown names yield no dependencies."""
    base = os.path.basename(rel)
    if base == "Gemfile":
        return parse_gemfile(text)
    if base == "package.json":
        return parse_package_json(text)
    if base == "pyproject.toml":
        return parse_pyproject(text)
    if base == "pnpm-workspace.yaml":
        return {"deps": [], "workspace_root": True, "errors": []}
    if rel.replace("\\", "/").endswith("config/importmap.rb"):
        return parse_importmap(text)
    if is_manifest(rel):
        return parse_requirements(text, rel)
    return {"deps": [], "workspace_root": False, "errors": []}
