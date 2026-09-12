#!/usr/bin/env python3
"""Boundary, misfit and Terraform detectors: BC1 cross-context-dependency, BC2 new-cycle,
BC3 cross-context-write, BC4 multi-context-transaction (info), MF1 wrong-context-file (info),
FC1 file-cycle inside one context (scans, info), TF1 reimplemented-module and TF2
module-version-divergence (scans, info).

Hooks warn on BC1 and BC3 only for DECLARED contexts. BC2 warns for declared contexts, or for
inferred contexts that are siblings under one parent directory (owner decision B); every other
inferred cycle is scan-only info. Tests, type-only imports and declared shared-kernel paths are
quiet; so are migrations, seeds, factories, fixtures, Django admin and declared backfills for BC3.
"""
import re

import _archconfig
import _archcontexts
import _archdup
import _archgraph
import _archrules

TEST_PATH = re.compile(r"(?:^|/)(?:spec|specs|test|tests|__tests__|factories|fixtures)/|_spec\.rb$|\.(?:test|spec)\.[jt]sx?$|(?:^|/)test_[^/]*\.py$|(?:^|/)conftest\.py$")
WRITE_QUIET = re.compile(r"(?:^|/)(?:db/migrate|migrations|alembic/versions)/|(?:^|/)db/seeds|(?:^|/)admin\.py$|(?:^|/)seeds?/")
COMPOSITION_ROOT = re.compile(r"(?:^|/)(?:config/|urls\.py$|main\.py$|routes?\.|index\.[jt]sx?$|application\.rb$|__init__\.py$)")
TF_FAMILIES = {"terraform-aws-modules/vpc/aws": ("aws_vpc",), "terraform-aws-modules/ecs/aws": ("aws_ecs_cluster",),
               "terraform-aws-modules/rds/aws": ("aws_db_instance",), "terraform-aws-modules/eks/aws": ("aws_eks_cluster",),
               "terraform-aws-modules/s3-bucket/aws": ("aws_s3_bucket",), "terraform-aws-modules/alb/aws": ("aws_lb",),
               "terraform-aws-modules/security-group/aws": ("aws_security_group",),
               "terraform-google-modules/network/google": ("google_compute_network",)}


def sites(view, delta):
    """[{path, line, symbol, src, dst, dst_path}] resolved, non-type-only references between contexts."""
    if delta is not None:
        found = []
        for ref in (r for r in delta["facts"]["refs"] if not r.get("type_only")):
            dst_path, dst = view.resolve(ref, delta["path"], delta["deployable"])
            if dst and dst != delta["context"]:
                found.append({"path": delta["path"], "line": ref["line"], "symbol": ref["symbol"], "src": delta["context"], "dst": dst, "dst_path": dst_path})
        return found
    rows = view.rows("refs", {"type_only": 0})
    return [{"path": r["path"], "line": r["line"], "symbol": r["symbol"], "src": r["src_context"], "dst": r["dst_context"],
             "dst_path": r["dst_path"]} for r in rows if r["dst_context"] and r["dst_context"] != r["src_context"]]


def _quiet_site(view, site):
    return TEST_PATH.search(site["path"]) or _archconfig.matches(site["dst_path"] or "", view.cmap.get("shared_kernel") or ())


def detect_bc1(view, delta, config):
    found, inferred = [], {}
    for site in (s for s in sites(view, delta) if not _quiet_site(view, s)):
        verdict, declaration = _archcontexts.allowed(view.cmap, site["src"], site["dst"])
        if verdict is False:
            text = "%s:%d references %s in %s; %s declares no dependency of %s on %s. Use %s's public API, or declare the dependency." % (
                site["path"], site["line"], site["symbol"], site["dst_path"], declaration, _archcontexts.display(view.cmap, site["src"]),
                _archcontexts.display(view.cmap, site["dst"]), _archcontexts.display(view.cmap, site["dst"]))
            found.append(_archrules.make("BC1", {"path": site["path"], "line": site["line"], "symbol": site["symbol"], "context": site["src"]}, text,
                                         related=[{"path": site["dst_path"], "line": 1, "symbol": site["symbol"], "context": site["dst"]}],
                                         confidence="high", suppress_config="contexts.<name>.may_depend_on",
                                         key=("%s|%s" % (site["path"], site["symbol"]), site["dst"]), evidence={"declaration": declaration}))
        elif delta is None and not _archcontexts.is_declared(view.cmap, site["src"]) and "/" in site["src"] and "/" in site["dst"]:
            inferred.setdefault((site["src"], site["dst"]), []).append(site)
    return found + [_inferred_bc1(pair, rows) for pair, rows in sorted(inferred.items())]


def _inferred_bc1(pair, rows):
    first = rows[0]
    text = "%d reference(s) from inferred context %s to %s (first: %s:%d %s). Inferred contexts are guesses; declare the contexts to check this edge." % (
        len(rows), pair[0], pair[1], first["path"], first["line"], first["symbol"])
    return _archrules.make("BC1", {"path": first["path"], "line": first["line"], "symbol": first["symbol"], "context": pair[0]}, text,
                           severity="info", confidence="low", key=pair, evidence={"count": len(rows)})


def _cycle_grade(view, members):
    if all(_archcontexts.is_declared(view.cmap, m) for m in members):
        return "warn"
    parents = {m.rsplit("/", 1)[0] if "/" in m else None for m in members}
    siblings = len(parents) == 1 and all(_archcontexts.siblings(view.cmap, members[0], m) for m in members[1:])
    return "warn" if siblings else "info"


def _cycle_finding(view, members, order, origin):
    path, line, adds = origin
    edges = []
    for src, dst in zip(order, order[1:]):
        example = adds.get((src, dst)) or view.edge_example(src, dst, view.context_edges(adds.get("exclude")).get((src, dst)))
        edges.append("%s->%s at %s:%d" % (_archcontexts.display(view.cmap, src), _archcontexts.display(view.cmap, dst), example[0], example[1]))
    grew = [r for r in view.baseline().values() if r["detector"] == "BC2" and set((r["subject"] or "").split("|")) < set(members)]
    text = "%s:%d closes a dependency cycle between contexts %s (%s)%s. Break it with an interface owned by one side, or declare the direction." % (
        path, line, " -> ".join(_archcontexts.display(view.cmap, m) for m in order), "; ".join(edges[:3]),
        ", growing a frozen cycle" if grew else "")
    return _archrules.make("BC2", {"path": path, "line": line, "symbol": "|".join(members), "context": order[0]}, text,
                           severity=_cycle_grade(view, members), confidence="high", key=("|".join(members), ""),
                           suppress_config="contexts.<name>.may_depend_on", evidence={"members": members, "grew": bool(grew)})


def detect_bc2(view, delta, config):
    if delta is None:
        return _bc2_scan(view)
    added = {}
    for site in (s for s in sites(view, delta) if not _quiet_site(view, s)):
        added.setdefault((delta["context"], site["dst"]), (site["path"], site["line"]))
    if not added:
        return []
    edges = set(view.context_edges(delta.get("file_id"))) | set(added)
    adjacency = _archgraph.context_adjacency(edges)
    found = []
    for component in _archgraph.cycles(adjacency):
        if delta["context"] in component and any(dst in component for _, dst in added):
            order = _archgraph.cycle_order(adjacency, component, delta["context"])
            origin = next(added[(delta["context"], d)] for d in order[1:2])
            found.append(_cycle_finding(view, component, order, (origin[0], origin[1], dict(added, exclude=delta.get("file_id")))))
    return found


def _bc2_scan(view):
    edges = view.context_edges()
    adjacency = _archgraph.context_adjacency(edges)
    found = []
    for component in _archgraph.cycles(adjacency):
        order = _archgraph.cycle_order(adjacency, component, component[0])
        path, line = view.edge_example(order[0], order[1], edges.get((order[0], order[1])))
        found.append(_cycle_finding(view, component, order, (path, line, {"exclude": None})))
    return found


def detect_fc1(view, delta, config):
    if delta is not None:
        return []
    adjacency, contexts = {}, {}
    for row in view.rows("refs", {"type_only": 0}):
        if row["dst_path"] and row["dst_context"] == row["src_context"] and row["dst_path"] != row["path"]:
            adjacency.setdefault(row["path"], set()).add(row["dst_path"])
            contexts[row["path"]] = row["src_context"]
    found = []
    for component in _archgraph.cycles(adjacency):
        text = "Files in context %s import each other in a cycle: %s." % (contexts.get(component[0]), " -> ".join(component[:6]))
        found.append(_archrules.make("FC1", {"path": component[0], "line": 1, "symbol": component[0], "context": contexts.get(component[0])},
                                     text, severity="info", confidence="medium", key=("|".join(component), "")))
    return found


def _model_for(view, deployable, symbol):
    tail = (symbol or "").split("::")[-1]
    norm = _archdup.normalize_name(tail)[0]
    models = view.cached(("models-norm", deployable, norm), lambda: view.rows("models", {"deployable": deployable, "norm": norm}))
    return next((m for m in models if m["symbol"] == symbol), None) or next((m for m in models if m["symbol"].split("::")[-1] == tail), None)


def _writes(view, delta):
    if delta is not None:
        return [dict(w, path=delta["path"], deployable=delta["deployable"], context=delta["context"], tbl=w.get("table")) for w in delta["facts"]["writes"]]
    files = {f["id"]: f for f in view.all_files()}
    return [dict(w, deployable=files[w["file_id"]]["deployable"], context=files[w["file_id"]]["context"]) for w in view.rows("writes")]


def _write_target(view, write):
    model = _model_for(view, write["deployable"], write.get("symbol")) if write.get("symbol") else None
    table = write.get("tbl") or (model["tbl"] if model else None)
    owner = _archcontexts.owner_of_table(view.cmap, table) if table else None
    return table, owner or (model["context"] if model else None), bool(owner)


def detect_bc3(view, delta, config):
    found = []
    for write in _writes(view, delta):
        if TEST_PATH.search(write["path"]) or WRITE_QUIET.search(write["path"]) or _archconfig.matches(write["path"], config.get("backfills")):
            continue
        table, owner, declared = _write_target(view, write)
        if not table or not owner or owner == write["context"] or _archconfig.write_exception(config, owner, table):
            continue
        warn = declared and _archcontexts.is_declared(view.cmap, write["context"])
        text = "%s:%d %s %s, owned by context %s (%s); this file is in context %s. Call the owner's entry point, or declare the write in contexts.%s.writes with an ADR." % (
            write["path"], write["line"], write.get("op") or "writes", table, _archcontexts.display(view.cmap, owner),
            "declared in .claude/orthogonality.json" if declared else "inferred", _archcontexts.display(view.cmap, write["context"]),
            _archcontexts.display(view.cmap, write["context"]))
        found.append(_archrules.make("BC3", {"path": write["path"], "line": write["line"], "symbol": table, "context": write["context"]}, text,
                                     severity="warn" if warn else "info", confidence="high" if warn else "low",
                                     suppress_config="contexts.<name>.writes", key=("%s|%s" % (write["path"], table), owner)))
    return found


def detect_bc4(view, delta, config):
    if delta is not None:
        return []
    writes, found = _writes(view, None), []
    for txn in view.rows("txns"):
        inside = [w for w in writes if w["path"] == txn["path"] and txn["line"] <= w["line"] <= txn["end_line"]]
        owners = sorted({o for o in (_write_target(view, w)[1] for w in inside) if o})
        if len(owners) >= 2:
            text = "%s:%d-%d: one transaction persists models from contexts %s. Transactions should not cross aggregate boundaries." % (
                txn["path"], txn["line"], txn["end_line"], ", ".join(owners))
            found.append(_archrules.make("BC4", {"path": txn["path"], "line": txn["line"], "symbol": "transaction"}, text,
                                         severity="info", confidence="low", key=("%s:%d" % (txn["path"], txn["line"]), "|".join(owners))))
    return found


def detect_mf1(view, delta, config):
    if delta is not None:
        return []
    per_file = {}
    for site in (s for s in sites(view, None) if not TEST_PATH.search(s["path"]) and not COMPOSITION_ROOT.search(s["path"])):
        per_file.setdefault((site["path"], site["src"]), {}).setdefault(site["dst"], []).append(site)
    found = []
    for (path, own), targets in sorted(per_file.items()):
        total = sum(len(v) for v in targets.values())
        top = max(targets, key=lambda k: len(targets[k]))
        if total >= 6 and len(targets[top]) >= 0.7 * total:
            text = "%s (context %s) makes %d of its %d cross-context references into %s; it may belong there." % (path, own, len(targets[top]), total, top)
            found.append(_archrules.make("MF1", {"path": path, "line": 1, "symbol": path, "context": own}, text,
                                         severity="info", confidence="low", key=(path, top)))
    return found


def detect_tf1(view, delta, config):
    if delta is not None:
        return []
    blocks = view.rows("tf")
    families = {}
    for module in (b for b in blocks if b["block"] == "module" and b["source"] and not b["source"].startswith(".")):
        for kind in TF_FAMILIES.get(module["source"].split("?")[0].split("//")[0], ()):
            families.setdefault(kind, module)
    found = []
    for resource in (b for b in blocks if b["block"] == "resource" and "/modules/" in "/" + b["path"] and b["type"] in families):
        module = families[resource["type"]]
        text = "%s:%d declares %s in a local module; %s:%d already uses the registry module %s, which provides it." % (
            resource["path"], resource["line"], resource["type"], module["path"], module["line"], module["source"])
        found.append(_archrules.make("TF1", {"path": resource["path"], "line": resource["line"], "symbol": resource["type"]}, text,
                                     related=[{"path": module["path"], "line": module["line"], "symbol": module["source"]}],
                                     severity="info", confidence="medium", key=(resource["path"], resource["type"])))
    return found


def detect_tf2(view, delta, config):
    if delta is not None:
        return []
    by_source = {}
    for module in (b for b in view.rows("tf") if b["block"] == "module" and b["source"] and b["version"]):
        by_source.setdefault(module["source"], []).append(module)
    found = []
    for source, modules in sorted(by_source.items()):
        versions = sorted({m["version"] for m in modules})
        if len(versions) > 1:
            first = modules[0]
            text = "Registry module %s is pinned to %d versions (%s) across root modules, first at %s:%d." % (source, len(versions), ", ".join(versions), first["path"], first["line"])
            found.append(_archrules.make("TF2", {"path": first["path"], "line": first["line"], "symbol": source}, text,
                                         severity="info", confidence="high", key=(source, "|".join(versions))))
    return found
