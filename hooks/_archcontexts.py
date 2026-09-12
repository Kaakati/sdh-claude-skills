#!/usr/bin/env python3
"""Bounded contexts for one project, and the dependency rules declared between them.

Precedence per subtree (the nearest declaration wins): packwerk (`packwerk.yml`, each `package.yml`),
import-linter contracts (`.importlinter`, `setup.cfg`, `pyproject.toml [tool.importlinter]`),
tach (`tach.toml`), `.claude/orthogonality.json` contexts, Nx `project.json` tags (names only),
then INFERRED contexts from the house layouts:
    Rails   app/models/<namespace>/ (a file under another app/<layer>/<namespace>/ joins that context
            only when app/models/<namespace>/ exists; api, admin, concerns and v1-style folders never
            are contexts), packs/*, app/packages/*, components/*
    Django  every app directory holding apps.py
    Python  first-level subpackages under app/ or src/<pkg>/, minus layer names (api, domain, ...)
    TS/JS   src/features/*, src/modules/*, src/domains/*
Everything else belongs to its deployable's default context. Declared context ids are package
directories (tools) or config names; inferred ids are directory-shaped, so siblings share a parent.
`package.yml` and `packwerk.yml` are read by a restricted line parser; unread keys are reported in
`unparsed`, never guessed. Layers contracts are ignored: layers are std-clean-architecture's axis.
"""
import configparser
import json
import os
import posixpath
import re

import _archtoml

RAILS_LAYERS = frozenset(("models", "services", "controllers", "jobs", "serializers", "policies", "views",
                          "components", "forms", "queries", "mailers", "channels", "workers", "interactors"))
PY_LAYERS = frozenset(("api", "routers", "schemas", "models", "services", "core", "db", "tasks", "utils", "common",
                       "lib", "config", "settings", "tests", "migrations", "alembic", "static", "templates",
                       "domain", "infrastructure", "infra", "application", "adapters", "repositories", "repository",
                       "crud", "dependencies", "deps", "middleware", "entities", "use_cases", "interfaces",
                       "presentation", "exceptions", "helpers"))
NEVER_RAILS_CONTEXT = re.compile(r"^(?:api|admin|concerns|v\d+)$")
TS_GROUPS = frozenset(("features", "modules", "domains"))
_PACKAGE_KEYS = frozenset(("enforce_dependencies", "dependencies", "enforce_privacy", "public_path", "metadata",
                           "enforce_architecture", "layer", "enforce_visibility", "visible_to", "owner"))


def read_package_yml(text):
    """(enforce, dependencies, unparsed keys) from a packwerk package.yml."""
    enforce = re.search(r"^enforce_dependencies:\s*['\"]?(\w+)", text, re.M)
    deps, unparsed, in_deps = [], [], False
    inline = re.search(r"^dependencies:\s*\[([^\]]*)\]", text, re.M)
    if inline:
        deps = [d.strip().strip("'\"") for d in inline.group(1).split(",") if d.strip()]
    for line in text.splitlines():
        key = re.match(r"^([\w-]+):", line)
        if key:
            in_deps = key.group(1) == "dependencies" and not inline
            unparsed += [] if key.group(1) in _PACKAGE_KEYS else [key.group(1)]
            continue
        item = re.match(r"^\s+-\s*['\"]?([^'\"#\s]+)", line) if in_deps else None
        if item:
            deps.append(item.group(1))
    return bool(enforce and enforce.group(1) in ("true", "strict")), deps, unparsed


def _item(name, source, decl, **extra):
    item = {"name": name, "source": source, "decl": decl, "declared": True, "enforce": False, "deps": None,
            "relationships": {}, "tables": [], "writes": []}
    item.update(extra)
    return item


def _packwerk(root, rel_paths, decl):
    roots = [posixpath.dirname(p) for p in rel_paths if posixpath.basename(p) == "packwerk.yml"]
    for pack_root in roots:
        for rel in rel_paths:
            if posixpath.basename(rel) != "package.yml" or not (rel + "/").startswith(pack_root + "/" if pack_root else ""):
                continue
            enforce, deps, unparsed = read_package_yml(_read(root, rel))
            package_id = posixpath.dirname(rel)
            dep_ids = [posixpath.normpath(posixpath.join(pack_root, d)) if d != "." else (pack_root or ".") for d in deps]
            decl["items"][package_id or "."] = _item(posixpath.basename(package_id) or ".", "packwerk", rel,
                                                     enforce=enforce, deps=dep_ids)
            decl["unparsed"] += ["%s: %s" % (rel, k) for k in unparsed]
            for dep in dep_ids:
                decl["items"].setdefault(dep, _item(posixpath.basename(dep), "packwerk", rel))
        decl["items"].setdefault(pack_root or ".", _item(".", "packwerk", posixpath.join(pack_root, "packwerk.yml")))


def _read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _module_dir(module, base, dirs):
    for prefix in (base, posixpath.join(base, "src") if base else "src"):
        candidate = posixpath.join(prefix, module.replace(".", "/")) if prefix else module.replace(".", "/")
        if candidate in dirs:
            return candidate
    return None


def _importlinter_contracts(root, rel):
    base = posixpath.basename(rel)
    if base == "pyproject.toml":
        data, _ = _archtoml.parse_toml(_read(root, rel))
        return ((data.get("tool") or {}).get("importlinter") or {}).get("contracts") or []
    parser = configparser.ConfigParser()
    try:
        parser.read_string(_read(root, rel))
    except configparser.Error:
        return []
    return [{k: [v.strip() for v in value.splitlines() if v.strip()] if k.endswith("modules") else value
             for k, value in parser.items(section)} for section in parser.sections() if section.startswith("importlinter:contract")]


def _importlinter(root, rel_paths, decl, dirs):
    for rel in rel_paths:
        if posixpath.basename(rel) not in (".importlinter", "setup.cfg", "pyproject.toml"):
            continue
        for contract in _importlinter_contracts(root, rel):
            kind = contract.get("type")
            groups = {k: [m for m in (contract.get(k) or []) if isinstance(m, str)] for k in ("modules", "source_modules", "forbidden_modules")}
            ids = {k: [d for d in (_module_dir(m, posixpath.dirname(rel), dirs) for m in v) if d] for k, v in groups.items()}
            for context_id in sum(ids.values(), []):
                decl["items"].setdefault(context_id, _item(context_id.replace("/", "."), "importlinter", rel))
            if kind == "independence" and len(ids["modules"]) > 1:
                decl["independence"].append(ids["modules"])
            elif kind == "forbidden":
                decl["forbidden"].append([ids["source_modules"], ids["forbidden_modules"]])


def _tach(root, rel_paths, decl, dirs):
    for rel in (p for p in rel_paths if posixpath.basename(p) == "tach.toml"):
        data, errors = _archtoml.parse_toml(_read(root, rel))
        decl["unparsed"] += ["%s: %s" % (rel, e) for e in errors]
        base = posixpath.dirname(rel)
        for module in data.get("modules") or []:
            path = module.get("path") if isinstance(module, dict) else None
            context_id = _module_dir(path, base, dirs) if isinstance(path, str) else None
            if not context_id:
                continue
            raw = module.get("depends_on")
            deps = None if raw is None else [_module_dir(d.get("path") if isinstance(d, dict) else d, base, dirs) for d in raw]
            decl["items"][context_id] = _item(path, "tach", rel, enforce=raw is not None,
                                              deps=[d for d in deps or [] if d] if deps is not None else None)


def _nx(root, rel_paths, decl):
    for rel in (p for p in rel_paths if posixpath.basename(p) == "project.json"):
        try:
            tags = json.loads(_read(root, rel) or "{}").get("tags") or []
        except (ValueError, AttributeError):
            continue
        scopes = [t.split(":", 1)[1] for t in tags if isinstance(t, str) and t.startswith("scope:")]
        if scopes:
            decl["items"].setdefault(posixpath.dirname(rel), _item(scopes[0], "nx", rel))


def rails_namespaces(rel_paths):
    """Inferred Rails context ids, `<prefix>app/<namespace>`, one per `app/models/<namespace>/` holding a Ruby file
    (design §1.6). A namespace named api, admin, concerns or v<N> is a routing or mixin folder, never a context."""
    found = set()
    for rel in (p.replace("\\", "/") for p in rel_paths if p.endswith(".rb")):
        parts = rel.split("/")
        for i in range(len(parts) - 3):
            if parts[i] == "app" and parts[i + 1] == "models" and not NEVER_RAILS_CONTEXT.match(parts[i + 2]):
                found.add("/".join(parts[:i + 1] + [parts[i + 2]]))
    return sorted(found)


def tool_declarations(root, rel_paths):
    """Contexts declared by tools, plus the Django app directories and Rails model namespaces, as a JSON-serializable dict."""
    rel_paths = sorted(p.replace("\\", "/") for p in rel_paths)
    dirs = {posixpath.dirname(p) for p in rel_paths}
    dirs |= {posixpath.dirname(d) for d in list(dirs)}
    decl = {"items": {}, "independence": [], "forbidden": [], "unparsed": [], "rails_namespaces": rails_namespaces(rel_paths),
            "django_apps": sorted(posixpath.dirname(p) for p in rel_paths if posixpath.basename(p) == "apps.py")}
    _packwerk(root, rel_paths, decl)
    _importlinter(root, rel_paths, decl, dirs)
    _tach(root, rel_paths, decl, dirs)
    _nx(root, rel_paths, decl)
    return decl


def with_config(decl, config):
    """The context map: tool declarations, then `.claude/orthogonality.json` contexts merged by name."""
    empty = {"items": {}, "independence": [], "forbidden": [], "unparsed": [], "django_apps": [], "rails_namespaces": []}
    cmap = json.loads(json.dumps(decl or empty))
    by_name = {item["name"]: key for key, item in cmap["items"].items()}
    cmap.update({"globs": [], "tables": {}, "shared_kernel": list(config.get("shared_kernel") or []), "unmatched": []})
    for name, body in (config.get("contexts") or {}).items():
        key = by_name.get(name, name)
        item = cmap["items"].setdefault(key, _item(name, "config", ".claude/orthogonality.json"))
        if "may_depend_on" in body or body.get("relationships"):
            item.update(enforce=True, deps=[by_name.get(d, d) for d in body.get("may_depend_on") or []])
        item["relationships"] = {by_name.get(k, k): v for k, v in (body.get("relationships") or {}).items()}
        item["writes"] = list(body.get("writes") or [])
        cmap["globs"] += [[pattern, key] for pattern in body.get("paths") or []]
        cmap["tables"].update({str(t).lower(): key for t in body.get("tables") or []})
        if key == name and not body.get("paths") and not body.get("tables"):
            cmap["unmatched"].append(name)
    cmap["prefixes"] = sorted(([k, k] for k, v in cmap["items"].items() if v["source"] != "config"),
                              key=lambda pair: -len(pair[0]))
    return cmap


def _inferred(rel, cmap):
    parts = rel.split("/")
    for i, part in enumerate(parts[:-2]):
        if part == "src" and parts[i + 1] in TS_GROUPS and len(parts) > i + 3:
            return "/".join(parts[:i + 3])
        if part == "app" and parts[i + 1] in RAILS_LAYERS and len(parts) > i + 3 and rel.endswith(".rb"):
            candidate = "/".join(parts[:i + 1] + [parts[i + 2]])
            return candidate if candidate in (cmap.get("rails_namespaces") or ()) else None
        if part in ("packs", "components") and rel.endswith(".rb") or (part == "packages" and i and parts[i - 1] == "app"):
            return "/".join(parts[:i + 2])
    apps = [a for a in cmap.get("django_apps") or [] if (rel + "/").startswith((a + "/") if a else "")]
    if apps:
        return max(apps, key=len) or "."
    return _python_inferred(parts) if rel.endswith(".py") else None


def _python_inferred(parts):
    for i, part in enumerate(parts[:-2]):
        position = i + 1 if part == "app" else i + 2 if part == "src" and len(parts) > i + 3 else None
        if position is not None and parts[position] not in PY_LAYERS and not parts[position].startswith("_"):
            return "/".join(parts[:position + 1])
    return None


def context_for(cmap, rel, deployable=""):
    """(context id, declared) for a project-relative path."""
    norm = rel.replace("\\", "/")
    for prefix, key in cmap.get("prefixes") or []:
        if prefix == "." or (norm + "/").startswith(prefix + "/"):
            return key, True
    import _archconfig
    for pattern, key in cmap.get("globs") or []:
        if _archconfig.matches(norm, [pattern]):
            return key, True
    inferred = _inferred(norm, cmap)
    return (inferred, False) if inferred else (deployable or ".", False)


def is_declared(cmap, context):
    return context in (cmap.get("items") or {})


def display(cmap, context):
    item = (cmap.get("items") or {}).get(context)
    return item["name"] if item else posixpath.basename(context or ".") or "."


def owner_of_table(cmap, table):
    return (cmap.get("tables") or {}).get(str(table or "").lower())


def siblings(cmap, a, b):
    """Two inferred, non-default contexts under one parent directory (owner decision B)."""
    if not a or not b or a == b or is_declared(cmap, a) or is_declared(cmap, b):
        return False
    return "/" in a and "/" in b and posixpath.dirname(a) == posixpath.dirname(b)


def allowed(cmap, a, b):
    """(True | False | None, declaration file) for an edge from context a to b. None: no rule applies."""
    item = (cmap.get("items") or {}).get(a)
    if a == b or not item:
        return (True if a == b else None), ""
    if item["source"] == "importlinter":
        blocked = any(a in g and b in g for g in cmap.get("independence") or []) or \
            any(a in pair[0] and b in pair[1] for pair in cmap.get("forbidden") or [])
        return (False if blocked else None), item["decl"]
    if not item.get("enforce") or item.get("deps") is None:
        return None, item["decl"]
    relationship = item.get("relationships", {}).get(b)
    return (b in item["deps"] or relationship not in (None, "separate-ways")), item["decl"]
