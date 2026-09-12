#!/usr/bin/env python3
"""Renderers for orthogonality reports: json, markdown, brief (at most 15 lines, for `!` injection)
and sarif-lite (a minimal SARIF 2.1.0 run for CI annotations); `--write-report`; the index listings
(`arch_index.py --show`); and the example ESLint / Ruff lint configuration built from the registry.

`write_report` is the only place the engine writes into a project: `.claude/orthogonality/
last-scan.json`, next to a `.gitignore` holding `*`, and only when the user passed --write-report.
"""
import json
import os

import _archcontexts
import _archindex
import _archstate

BRIEF_LINES = 15
_LEVELS = {"warn": "warning", "info": "note", "note": "note"}
_IMPORT_NAMES = {"pyjwt": "jwt", "python-jose": "jose", "argon2-cffi": "argon2", "djangorestframework-simplejwt": "rest_framework_simplejwt",
                 "djangorestframework-jwt": "rest_framework_jwt", "tortoise-orm": "tortoise", "django-rest-knox": "knox"}


def render(report, fmt):
    if fmt == "json":
        return json.dumps(report, indent=2)
    if fmt == "sarif-lite":
        return json.dumps(sarif(report), indent=2)
    return brief(report) if fmt == "brief" else markdown(report)


def _counts(report):
    by = report.get("stats", {}).get("by_severity") or {}
    return ", ".join("%d %s" % (by[k], k) for k in sorted(by)) or "none"


def brief(report):
    findings = report.get("findings") or []
    lines = [f["message"] for f in findings[:BRIEF_LINES - 1]]
    incomplete = "" if report.get("index", {}).get("complete", True) else "; index incomplete"
    more = " (%d not shown)" % (len(findings) - len(lines)) if len(findings) > len(lines) else ""
    lines.append("orthogonality %s: %d finding(s): %s%s%s" % (report.get("script"), len(findings), _counts(report), more, incomplete))
    return "\n".join(lines)


def _finding_lines(findings):
    lines = []
    for klass in sorted({f["class"] for f in findings}):
        lines += ["", "## %s" % klass]
        for severity in ("warn", "info", "note"):
            chosen = [f for f in findings if f["class"] == klass and f["severity"] == severity]
            lines += (["", "### %s" % severity] if chosen else []) + ["- %s%s%s" % (
                f["message"], "" if f.get("new", True) else " _(frozen)_", " _(suppressed: %s)_" % f["suppressed"] if f.get("suppressed") else "")
                for f in chosen]
    return lines


def markdown(report):
    index = report.get("index") or {}
    lines = ["# Orthogonality: %s" % report.get("script"), "",
             "Index: %s files, complete: %s, truncated: %s. Findings: %s." % (index.get("files"), index.get("complete"),
                                                                             index.get("truncated"), _counts(report))]
    lines += _finding_lines(report.get("findings") or [])
    tools = report.get("tools") or []
    if tools:
        lines += ["", "## Community tools", "", "| Tool | Status | Why | Violations | New |", "|---|---|---|---|---|"]
        lines += ["| %s | %s | %s | %s | %s |" % (t["name"], t.get("status"), t.get("why", ""), len(t.get("violations") or []),
                                                t.get("new_violations", 0)) for t in tools]
    for key in ("lint_config", "graph", "items", "matches"):
        if report.get(key) is not None:
            lines += ["", "## %s" % key, "", "```", report[key] if isinstance(report[key], str) else json.dumps(report[key], indent=2), "```"]
    frozen = (report.get("baseline") or {}).get("frozen") or {}
    lines += ["", "## Frozen baseline", "", "| Detector | Frozen findings |", "|---|---|"] + ["| %s | %d |" % (k, v) for k, v in sorted(frozen.items())]
    return "\n".join(lines)


def sarif(report):
    findings = report.get("findings") or []
    rules = {f["id"]: {"id": f["id"], "name": f["slug"]} for f in findings}
    results = [{"ruleId": f["id"], "level": _LEVELS.get(f["severity"], "note"), "message": {"text": f["message"]},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": f["subject"]["path"]},
                                                    "region": {"startLine": max(1, int(f["subject"]["line"] or 1))}}}],
                "partialFingerprints": {"sdhOrthogonality/v1": f["fingerprint"]},
                "properties": {"new": f.get("new"), "confidence": f["confidence"], "suppressed": f.get("suppressed")}} for f in findings]
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{"tool": {"driver": {"name": "sdh-orthogonality", "rules": sorted(rules.values(), key=lambda r: r["id"])}},
                      "results": results}]}


def write_report(root, report):
    """Write .claude/orthogonality/last-scan.json (and a `*` .gitignore beside it). Returns the path."""
    directory = os.path.join(root, ".claude", "orthogonality")
    os.makedirs(directory, exist_ok=True)
    ignore = os.path.join(directory, ".gitignore")
    if not os.path.isfile(ignore):
        with open(ignore, "w", encoding="utf-8") as handle:
            handle.write("*\n")
    target = os.path.join(directory, "last-scan.json")
    _archstate.atomic_write(target, json.dumps(report, indent=2))
    return target


def _competitor_messages(row, concern, framework):
    house = "+".join(row["house"] or row.get("js_house") or []) or "the house choice"
    messages = {}
    for entry in row.get("competitors") or []:
        for package in ([entry] if isinstance(entry, str) else entry):
            messages[package] = "%s: the house choice for %s is %s (see the orthogonality skill)." % (concern, framework, house)
    return messages


def lint_config(view, kind, paths=None):
    """Example no-restricted-imports (eslint) or banned-api (ruff) configuration per deployable; printed, never
    written. `paths` limits it to the deployables holding those project-relative paths."""
    ecosystem = "npm" if kind == "eslint" else "pypi"
    deployables = sorted({r["deployable"] for r in view.select("deps", {"ecosystem": ecosystem}, ["deployable"], distinct=True)})
    if paths:
        dirs = _archindex.deployable_dirs([f["path"] for f in view.all_files()])
        wanted = {_archindex.deployable_of(p.rstrip("/") + ("/x" if not os.path.splitext(p)[1] else ""), dirs) for p in paths}
        deployables = [d for d in deployables if d in wanted]
    per_deployable = {}
    for deployable in deployables:
        framework = _archindex.framework_for(view.root, deployable, ecosystem, view.cached("fw", dict))
        messages = {}
        for concern, spec in sorted(view.registry()["concerns"].items()):
            if kind == "ruff" and spec.get("tooling"):
                continue
            for row in (r for r in spec["rows"] if r["ecosystem"] == ecosystem and framework in r["frameworks"]):
                messages.update(_competitor_messages(row, concern, framework))
        per_deployable[deployable] = messages
    return _eslint(per_deployable) if kind == "eslint" else _ruff(per_deployable)


def _eslint(per_deployable):
    return {deployable: {"rules": {"no-restricted-imports": ["error", {"paths": [{"name": name, "message": message}
                                                                                   for name, message in sorted(messages.items())]}]}}
            for deployable, messages in per_deployable.items()}


def _ruff(per_deployable):
    blocks = []
    for deployable, messages in sorted(per_deployable.items()):
        blocks += ["# %s/pyproject.toml" % deployable, "[tool.ruff.lint.flake8-tidy-imports.banned-api]"]
        blocks += ['"%s".msg = "%s"' % (_IMPORT_NAMES.get(name, name.replace("-", "_")), message.replace('"', "'"))
                   for name, message in sorted(messages.items())] + [""]
    return "\n".join(blocks)


def index_items(view, what):
    """arch_index --show listings."""
    if what == "models":
        return [{"symbol": m["symbol"], "table": m["tbl"], "path": m["path"], "line": m["line"], "context": m["context"],
                 "framework": m["framework"]} for d in view.deployables() for m in view.models(d)]
    if what == "tables":
        return [{"name": t["name"], "deployable": d, "context": t["context"], "declared": t["declared"], "origin": t["origin"],
                 "path": t["path"], "line": t["line"], "columns": [c["name"] for c in t["columns"]]}
                for d in view.deployables() for t in view.tables(d).values()]
    if what == "graph":
        return [{"from": a, "to": b, "example": view.edge_example(a, b, f)[0]} for (a, b), f in sorted(view.context_edges().items())]
    if what == "coverage":
        return {r["key"]: json.loads(r["value"]) for r in view.select("coverage")}
    if what == "contexts":
        inferred = sorted({f["context"] for f in view.all_files() if not _archcontexts.is_declared(view.cmap, f["context"])})
        return {"declared": view.cmap.get("items"), "inferred": inferred, "unmatched": view.cmap.get("unmatched")}
    return None


def graph_dot(view):
    lines = ["digraph contexts {"] + ['  "%s" -> "%s";' % (a, b) for a, b in sorted(view.context_edges())] + ["}"]
    return "\n".join(lines)
