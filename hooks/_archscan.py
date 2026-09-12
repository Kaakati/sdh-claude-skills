#!/usr/bin/env python3
"""On-demand orthogonality scans for the skill scripts and CI.

A scan refreshes the index (unless --no-refresh), runs the requested detectors over the whole index,
applies declarations and inline markers, and decides which findings are NEW:
  * with --changed-since REF: new means absent when the changed files are swapped back to their REF
    versions inside a savepoint that is rolled back afterwards, so CI with a fresh cache still
    reports only what the change introduced;
  * otherwise: new means absent from the stored baseline, which a scan stamps for any detector the
    baseline does not cover yet (and which --update-baseline re-stamps with a reason).
Community tools run only when requested, and a database-connected tool only with --with-db.
Nothing is written into the project except by `_archreport.write_report` (--write-report).
"""
import calendar
import collections
import hashlib
import json
import os
import time

import _archconfig
import _archcontexts
import _archdup
import _archindex
import _archparse
import _archrefresh
import _archrules
import _archstore
import _archtools
import _archview
import _teamgate

SCHEMA = "sdh.orthogonality/v1"
_Stat = collections.namedtuple("_Stat", "st_size st_mtime_ns")


class ScanError(Exception):
    """A usage or configuration problem (code 2) or an internal failure (code 3)."""

    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code


def load_config(root, path=None):
    config, errors, target = _archconfig.load(root, path)
    if errors:
        detail = "; ".join("%s: %s" % (e["path"], e["message"]) for e in errors[:5])
        raise ScanError(2, "invalid %s (%s)" % (os.path.relpath(target, root).replace("\\", "/"), detail))
    return config


def changed_files(root, ref):
    """Files changed since REF: `git diff REF...HEAD`, plus uncommitted and untracked files."""
    code, out = _teamgate.run_git(root, ["diff", "--name-only", "-z", "%s...HEAD" % ref], 30)
    if code != 0:
        raise ScanError(2, "--changed-since %s: git could not diff against that ref (fetch it, or pass another ref)" % ref)
    paths = {p for p in out.split("\0") if p}
    for args in (["diff", "--name-only", "-z"], ["ls-files", "-z", "--others", "--exclude-standard"]):
        code, out = _teamgate.run_git(root, args, 30)
        paths |= {p for p in out.split("\0") if p} if code == 0 else set()
    return sorted(paths)


def open_view(root, options, config):
    stats = {}
    if not options.get("no_refresh"):
        stats = _archrefresh.refresh(root, {"cache_dir": options.get("cache_dir"), "budget": options.get("budget") or 120.0,
                                            "rebuild": bool(options.get("rebuild"))})
    store = _archstore.open_store(root, options.get("cache_dir"), write=True)
    view = _archview.IndexView(store, root, config)
    view.options = {k: options.get(k) for k in ("include_tests", "min_tokens", "min_jaccard", "min_shared")}
    return view, stats


def apply_contexts_source(view, source):
    """--contexts-source: keep only one declaration source ("inferred" drops every declaration)."""
    if source in (None, "auto"):
        return
    decl = json.loads(view.meta("context_decl") or "null") or {"items": {}, "independence": [], "forbidden": [], "unparsed": [], "django_apps": []}
    decl["items"] = {k: v for k, v in decl.get("items", {}).items() if v.get("source") == source}
    view.cmap = _archcontexts.with_config(decl, view.config if source == "config" else {})


def run_all(view, detectors, deadline):
    findings, not_run = _archrules.run_detectors(view, None, detectors, deadline)
    findings += _archrules.declaration_findings(view.config, view.root)
    for row in view.rows("markers"):
        findings += _archrules.marker_findings([row], row["path"])
    _archrules.apply_suppressions(findings, view, None)
    return findings, not_run


def _swap_to_base(view, ref, changed):
    store, root, texts = view.store, view.root, {}
    env = {"root": root, "deployables": _archindex.deployable_dirs([f["path"] for f in view.all_files()] + list(changed)),
           "cmap": view.cmap, "frameworks": {}, "skipped_large": 0}
    for rel in (p for p in changed if _archparse.classify(p)):
        row = view.file_by_path(rel)
        if row:
            _archindex._delete_facts(store, [row["id"]])
            store.delete("files", {"id": row["id"]})
        code, text = _teamgate.run_git(root, ["show", "%s:%s" % (ref, rel)], 30)
        texts[rel] = text if code == 0 else ""
        if code == 0:
            data = text.encode("utf-8", "replace")
            file_row = _archindex._file_row(rel, _Stat(len(data), 0), hashlib.sha1(data).hexdigest(), env)
            file_id = store.insert("files", file_row)
            _archindex.write_facts(store, file_id, _archparse.parse_text(rel, text), file_row)
    _archrefresh.resolve_refs(store, root, None)
    return texts


def base_fingerprints(view, ref, changed, detectors):
    """(fingerprints, detectors stopped by the budget) the same detectors report with the changed files at REF.
    The index is restored afterwards; the pass shares the scan's deadline (`view.deadline`)."""
    store = view.store
    store.begin()
    store.snapshot()
    try:
        texts = _swap_to_base(view, ref, changed)
        base_view = _archview.IndexView(store, view.root, view.config)
        base_view.cmap, base_view.options = view.cmap, dict(view.options, texts=texts, subjects=list(texts))
        findings, not_run = run_all(base_view, detectors, getattr(view, "deadline", None))
        return {f["fingerprint"] for f in findings}, {d: r for d, r in not_run.items() if r == _archrules.BUDGET_REASON}
    finally:
        store.restore()
        store.commit()


def settle_new(view, findings, detectors, options):
    """Mark each finding new or frozen: against REF with --changed-since, else against the baseline. Returns the
    detectors the REF pass could not finish in time. A detector that did not finish is never stamped into a baseline."""
    changed = options.get("_changed")
    if changed is not None:
        base, base_not_run = base_fingerprints(view, options["changed_since"], changed, detectors)
        config_changed = _archconfig.CONFIG_REL in changed
        for finding in findings:
            finding["new"] = finding["fingerprint"] not in base and (config_changed or not finding["id"].startswith("CFG-"))
        return base_not_run
    finished = [d for d in detectors if d not in (options.get("_not_run") or {})]
    if options.get("update_baseline"):
        _archrules.replace_baseline(view.store, findings, finished, options.get("reason") or "")
    elif view.meta("complete") == "1":
        _archrules.ensure_baseline(view.store, findings, finished, "first scan with these detectors")
    view._memo.pop("baseline", None)
    _archrules.mark_new(findings, view)
    return {}


def tool_results(view, options, changed):
    rows = _archtools.detect(view.root, bool(options.get("with_db")))
    wanted = options.get("tools")
    if wanted not in (None, "auto", ["auto"]):
        names = set(wanted)
        unknown = names - {spec[0] for spec in _archtools.SPECS}
        if unknown:
            raise ScanError(2, "unknown tool(s): %s" % ", ".join(sorted(unknown)))
        if not options.get("with_db") and any(spec[5] for spec in _archtools.SPECS if spec[0] in names):
            raise ScanError(2, "a database-connected tool was requested without --with-db")
        rows = [r for r in rows if r["name"] in names]
    results = _archtools.run(view.root, rows, {"changed": changed or [], "budget": options.get("budget")})
    if options.get("update_seen"):
        _archtools.mark_seen(view.store, results)
    return results


def scan_scope(paths, changed):
    """The paths a scan reports on (--paths plus --changed-since files), or None for the whole index."""
    if not paths and changed is None:
        return None
    return set(paths or []) | set(changed or [])


def in_scope(finding, scope):
    if scope is None:
        return True
    paths = [finding["subject"]["path"]] + [r.get("path") for r in finding.get("related") or []]
    return any(p and (p in scope or any(p.startswith(s.rstrip("/") + "/") for s in scope)) for p in paths)


def _age(iso):
    try:
        return max(0, int(time.time() - calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))))
    except (TypeError, ValueError):
        return None


def index_block(view):
    coverage = {r["key"]: json.loads(r["value"]) for r in view.select("coverage")}
    built = view.meta("built_at") or ""
    digest = hashlib.sha1(("%s|%s|%s" % (built, view.meta("files"), view.meta("head"))).encode("utf-8")).hexdigest()
    return {"fingerprint": digest, "complete": view.meta("complete") == "1", "files": int(view.meta("files") or 0),
            "truncated": bool(coverage.get("truncated")), "clones_truncated": False, "age_seconds": _age(view.meta("checked_at") or built),
            "coverage": dict({"config_unparsed": [], "unsupported": []}, **coverage)}


def contexts_block(view):
    items = view.cmap.get("items") or {}
    sources = sorted({i["source"] for i in items.values()})
    listed = [{"name": i["name"], "id": key, "source": i["source"], "decl": i.get("decl"),
               "paths": [p for p, k in view.cmap.get("globs") or [] if k == key] or ([key] if i["source"] != "config" else []),
               "may_depend_on": i.get("deps")} for key, i in sorted(items.items())]
    return {"source": sources[0] if len(sources) == 1 else ("mixed" if sources else "inferred"), "items": listed,
            "unmatched": view.cmap.get("unmatched") or []}


def report(script, view, parts):
    """The sdh.orthogonality/v1 document. parts: findings, tools, not_run, seconds, detectors, extra."""
    findings = parts["findings"]
    by_severity, frozen = _archrules.summary(findings)
    body = {"schema": SCHEMA, "script": script, "plugin_version": _archstore.plugin_version(),
            "project_root": view.root.replace("\\", "/"), "generated_at": _archstore.now_iso(),
            "index": index_block(view), "contexts": contexts_block(view),
            "findings": [_archrules.public(f) for f in findings], "tools": parts.get("tools") or [],
            "baseline": {"taken_at": view.meta("baseline_at"), "frozen": frozen,
                         "detectors": json.loads(view.meta("baseline_detectors", "[]") or "[]")},
            "stats": {"seconds": parts.get("seconds"), "by_severity": by_severity, "not_run": parts.get("not_run") or {},
                      "detectors": list(parts.get("detectors") or []),
                      "suppressed": len([f for f in findings if f.get("suppressed")]),
                      "new": len([f for f in findings if f.get("new")])}}
    body.update(parts.get("extra") or {})
    return body


def scan(root, script, options):
    """Run a scan and return (report, view state closed). Raises ScanError for usage problems. The --budget
    deadline bounds the detectors, inside their loops, and the --changed-since base pass alike; per-site
    detectors take only the in-scope sites as subjects."""
    started = time.monotonic()
    config = load_config(root, options.get("config"))
    detectors = list(options.get("detectors") or _archrules.ALL_DETECTORS)
    view, _ = open_view(root, options, config)
    try:
        apply_contexts_source(view, options.get("contexts_source"))
        changed = changed_files(root, options["changed_since"]) if options.get("changed_since") else None
        scope = scan_scope(options.get("paths"), changed)
        view.options.update(scope=scope, **({"subjects": changed} if changed is not None else {}))
        findings, not_run = run_all(view, detectors, started + float(options.get("budget") or 120.0))
        not_run.update(settle_new(view, findings, detectors, dict(options, _changed=changed, _not_run=dict(not_run))))
        tools = tool_results(view, options, changed) if options.get("tools") else []
        findings += _archtools.new_violations(view.store, tools) if tools else []
        shown = [f for f in findings if in_scope(f, scope) and (f.get("new") or not options.get("new_only"))]
        extra = options["extra"](view) if options.get("extra") else {}
        return report(script, view, {"findings": shown, "tools": tools, "not_run": not_run, "detectors": detectors,
                                     "seconds": round(time.monotonic() - started, 3), "extra": extra})
    finally:
        view.store.close()


def concept_matches(view, name):
    """arch_index --name: exact, near-name and synonym matches among tables and models."""
    wanted = _archdup.normalize_name(name)
    matches = []
    for deployable in view.deployables():
        for table in view.tables(deployable).values():
            kind = _archdup.name_match(wanted, (table["norm"], table["near"]), view.groups)
            if kind:
                matches.append({"kind": "table", "symbol": table["name"], "table": table["name"], "match": kind,
                                "context": table["context"], "declared": table["declared"], "deployable": deployable,
                                "path": table["path"], "line": table["line"], "columns": [c["name"] for c in table["columns"]][:12]})
        for model in view.models(deployable):
            kind = _archdup.name_match(wanted, _archdup.normalize_name(model["symbol"]), view.groups)
            if kind:
                matches.append({"kind": "model", "symbol": model["symbol"], "table": model["tbl"], "match": kind, "context": model["context"],
                                "declared": _archcontexts.is_declared(view.cmap, model["context"]), "deployable": deployable,
                                "path": model["path"], "line": model["line"], "columns": []})
    return sorted(matches, key=lambda m: (["exact", "near-name", "synonym"].index(m["match"]), m["path"]))
