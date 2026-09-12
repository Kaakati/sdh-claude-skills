#!/usr/bin/env python3
"""The command-line front end every `skills/orthogonality/scripts/*.py` delegates to.

    main(script, argv, detectors=()) -> exit code

Exit codes (all scripts):
    0  success, and no finding at or above --fail-on
    1  a finding at or above --fail-on, or --status --require-complete on an incomplete index
    2  usage or configuration error (unknown detector or tool, invalid .claude/orthogonality.json,
       a database-connected tool without --with-db, --update-baseline without --reason)
    3  internal error; with --strict also an incomplete scan (budget reached, tool timeout or error)
Output goes to stdout (or --output) as json | markdown | brief | sarif-lite; markdown on a TTY,
json otherwise.
"""
import argparse
import os
import sys

import _archindex
import _archreport
import _archrules
import _archscan
import _archstate
import _archstore
import _archtools
import _archview
import _hooklib

DESCRIPTIONS = {
    "arch_index": "Build, refresh or inspect the orthogonality index; look up a concept before adding a model or table.",
    "find_duplicates": "Duplicated knowledge: DK1-DK6 and MF3-MF5 over the whole index.",
    "check_boundaries": "Bounded-context coupling: BC1-BC4, MF1 and file-level cycles.",
    "check_mechanisms": "Competing mechanisms: CM1-CM5 and MF2; example ESLint/Ruff config from the registry.",
    "run_community_tools": "Detect and run community architecture tools that are already installed (never installs).",
    "arch_scan": "Everything: refresh, all detectors, optional tools, baseline management and reports.",
}


def _common(parser):
    add = parser.add_argument
    add("--project", help="project or worktree root (default: the root holding the current directory)")
    add("--cache-dir", help="index cache root (default: $CLAUDE_PLUGIN_DATA/orthogonality)")
    add("--config", help="declaration file (default: <project>/.claude/orthogonality.json)")
    add("--format", choices=("json", "markdown", "brief", "sarif-lite"))
    add("--output", help="write the report here instead of stdout")
    add("--paths", nargs="+", help="limit reported findings to these project-relative paths or directories")
    add("--changed-since", help="limit to files changed since this git ref; new means new relative to it")
    add("--new-only", action="store_true", help="hide findings already in the baseline")
    add("--fail-on", choices=("warn", "info", "never"), default="never")
    add("--budget", type=float, default=120.0, help="seconds before the scan stops and reports complete: false")
    add("--no-refresh", action="store_true")
    add("--strict", action="store_true", help="an incomplete scan exits 3")
    add("--write-report", action="store_true", help="also write .claude/orthogonality/last-scan.json (gitignored)")


def _script_args(parser, script, detectors):
    add = parser.add_argument
    if script == "arch_index":
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--refresh", action="store_true", help="incremental refresh (default)")
        mode.add_argument("--rebuild", action="store_true")
        mode.add_argument("--status", action="store_true")
        add("--require-complete", action="store_true")
        add("--show", choices=("models", "tables", "contexts", "mechanisms", "graph", "coverage"))
        add("--name", help="concept lookup: exact, near-name and synonym matches")
        return
    if script == "run_community_tools":
        add("--list", action="store_true")
        add("--tools", default="auto")
        add("--base")
        add("--with-db", action="store_true")
        add("--update-seen", action="store_true")
        return
    add("--detectors", default=",".join(detectors))
    add("--include-tests", action="store_true")
    add("--min-tokens", type=int)
    add("--min-jaccard", type=float)
    add("--min-shared", type=int)
    _family_args(parser, script)


def _family_args(parser, script):
    add = parser.add_argument
    if script == "check_boundaries":
        add("--contexts-source", choices=("auto", "packwerk", "importlinter", "tach", "config", "nx", "inferred"), default="auto")
        add("--cycles", choices=("context", "file"), default="context")
        add("--graph", choices=("dot", "json"))
    if script == "check_mechanisms":
        add("--emit-lint-config", choices=("eslint", "ruff"))
    if script == "arch_scan":
        add("--tools", nargs="?", const="auto")
        add("--with-db", action="store_true")
        add("--update-seen", action="store_true")
        add("--update-baseline", action="store_true")
        add("--reason")
        add("--baseline-report", action="store_true")
        add("--contexts-source", default="auto")


def build_parser(script, detectors=()):
    parser = argparse.ArgumentParser(prog=script + ".py", description=DESCRIPTIONS[script])
    _common(parser)
    _script_args(parser, script, detectors)
    return parser


def _detector_list(args, script):
    wanted = [d.strip().upper() for d in (args.detectors or "").split(",") if d.strip()]
    unknown = [d for d in wanted if d not in _archrules.CATALOG or d.startswith("CFG")]
    if unknown:
        raise _archscan.ScanError(2, "unknown detector(s): %s (known: %s)" % (", ".join(unknown), ", ".join(_archrules.ALL_DETECTORS)))
    if script == "check_boundaries" and args.cycles == "file" and "FC1" not in wanted:
        wanted.append("FC1")
    return wanted


def _extra(script, args):
    def build(view):
        extra = {}
        if script == "check_mechanisms" and args.emit_lint_config:
            extra["lint_config"] = _archreport.lint_config(view, args.emit_lint_config, args.paths)
        if script == "check_boundaries" and args.graph:
            extra["graph"] = _archreport.graph_dot(view) if args.graph == "dot" else _archreport.index_items(view, "graph")
        if script == "arch_scan" and args.baseline_report:
            extra["baseline_history"] = view.select("baseline_history")
        return extra
    return build


def _scan(root, args, script):
    if getattr(args, "update_baseline", False) and not args.reason:
        raise _archscan.ScanError(2, "--update-baseline needs --reason")
    options = {k: getattr(args, k, None) for k in ("cache_dir", "config", "paths", "changed_since", "new_only", "budget", "no_refresh",
                                                   "include_tests", "min_tokens", "min_jaccard", "min_shared", "contexts_source",
                                                   "with_db", "update_seen", "update_baseline", "reason")}
    tools = getattr(args, "tools", None)
    options.update(detectors=_detector_list(args, script), extra=_extra(script, args),
                   tools=None if tools is None else ("auto" if tools == "auto" else [t.strip() for t in tools.split(",") if t.strip()]))
    return _archscan.scan(root, script, options)


def _unfinished(root, args):
    """(body, exit code) for an index no refresh pass has finished: one being built now, or one a killed pass left."""
    building = _archstate.lock_held(_archstore.index_dir(root, args.cache_dir))
    note = ("an index refresh is in progress; retry shortly" if building else
            "no index refresh has finished yet; run arch_index.py again to resume it")
    sys.stderr.write("orthogonality: %s\n" % note)
    body = {"schema": _archscan.SCHEMA, "script": "arch_index", "findings": [], "note": note,
            "index": {"exists": True, "complete": False, "files": 0, "in_progress": building}}
    return body, (1 if args.require_complete else 0)


def _status(root, args):
    try:
        store = _archstore.open_store(root, args.cache_dir)
    except _archstore.IndexIncomplete:
        return _unfinished(root, args)
    if store is None:
        return {"schema": _archscan.SCHEMA, "script": "arch_index", "index": {"exists": False, "complete": False, "files": 0},
                "findings": []}, (1 if args.require_complete else 0)
    view = _archview.IndexView(store, root, _archscan.load_config(root, args.config))
    body = _archscan.report("arch_index", view, {"findings": []})
    store.close()
    return body, (1 if args.require_complete and not body["index"]["complete"] else 0)


def _index(root, args):
    if args.status:
        return _status(root, args)
    locked = False
    if not args.no_refresh:
        from _archrefresh import refresh
        locked = bool(refresh(root, {"cache_dir": args.cache_dir, "budget": args.budget, "rebuild": args.rebuild}).get("locked"))
    try:
        store = _archstore.open_store(root, args.cache_dir)
    except _archstore.StoreError as exc:
        if locked or isinstance(exc, _archstore.IndexIncomplete):
            return _unfinished(root, args)
        raise
    if store is None and locked:
        return _unfinished(root, args)
    view = _archview.IndexView(store, root, _archscan.load_config(root, args.config))
    extra = {"matches": _archscan.concept_matches(view, args.name)} if args.name else {}
    extra.update({"items": _mechanism_items(view) if args.show == "mechanisms" else _archreport.index_items(view, args.show)} if args.show else {})
    body = _archscan.report("arch_index", view, {"findings": [], "extra": dict(extra, query={"name": args.name} if args.name else {})})
    store.close()
    return body, 0


def _mechanism_items(view):
    import _archdetect_mech
    items = []
    for deployable, deps in _archdetect_mech._manifest_rows(view, None).items():
        for concern in sorted(view.registry()["concerns"]):
            slots = _archdetect_mech._mechanisms(view, concern, deployable, deps)
            if slots:
                items.append({"deployable": deployable, "concern": concern,
                              "mechanisms": [{"packages": sorted(s["packages"]), "house": s["house"]} for s in slots.values()]})
    return items


def _tools(root, args):
    rows = _archtools.detect(root, args.with_db)
    if args.list:
        store = _archstore.open_store(root, args.cache_dir)
        view = _archview.IndexView(store, root, {})
        body = _archscan.report("run_community_tools", view, {"findings": [], "tools": rows})
        if store is not None:
            store.close()
        return body, 0
    options = {"cache_dir": args.cache_dir, "config": args.config, "no_refresh": True, "detectors": [], "budget": args.budget,
               "tools": "auto" if args.tools == "auto" else [t.strip() for t in args.tools.split(",") if t.strip()],
               "with_db": args.with_db, "update_seen": args.update_seen, "changed_since": args.changed_since, "paths": args.paths}
    return _archscan.scan(root, "run_community_tools", options), None


def exit_code(body, args):
    failing = {"warn": ("warn",), "info": ("warn", "info"), "never": ()}[args.fail_on]
    hit = any(f["severity"] in failing and not f.get("suppressed") for f in body.get("findings") or [])
    budget = any(v == "time budget reached" for v in (body.get("stats") or {}).get("not_run", {}).values())
    tool_failed = any(t.get("status") in ("timeout", "error") for t in body.get("tools") or [])
    if args.strict and (not (body.get("index") or {}).get("complete", False) or budget or tool_failed):
        return 3
    return 1 if hit else 0


def _emit(body, args, root):
    fmt = args.format or ("markdown" if sys.stdout.isatty() else "json")
    text = _archreport.render(body, fmt)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        sys.stdout.write(text + "\n")
    if args.write_report:
        _archreport.write_report(root, body)


def main(script, argv, detectors=()):
    """Parse, run and emit one script; returns the exit code (argparse itself exits 2 on bad usage)."""
    _hooklib._safe_stdio()
    args = build_parser(script, detectors).parse_args(argv)
    try:
        root = _archindex.resolve_root(args.project or os.getcwd())
        if script == "arch_index":
            body, code = _index(root, args)
        elif script == "run_community_tools":
            body, code = _tools(root, args)
        else:
            body, code = _scan(root, args, script), None
        _emit(body, args, root)
        return exit_code(body, args) if code is None else code
    except _archscan.ScanError as exc:
        sys.stderr.write("orthogonality: %s\n" % exc)
        return exc.code
    except Exception as exc:
        sys.stderr.write("orthogonality: internal error: %s: %s\n" % (type(exc).__name__, exc))
        return 3
