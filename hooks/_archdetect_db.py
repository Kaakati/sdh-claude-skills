#!/usr/bin/env python3
"""Duplicated-knowledge and schema-misfit detectors: DK1 duplicate-concept, DK2 overlapping-columns,
DK3 fact-reachable-through-fk, DK4 repeating-group, MF3 eav-table, MF5 jsonb-key-as-column.

Subjects and candidate pools come from `_archsubjects` (edit mode: the edited file's tables and
the few tables that can pair with them; scan mode: every merged table, blocked into pairs).
Different DECLARED contexts are legitimate polysemy and stay quiet; different inferred contexts are
info. A synonym raises a name match to warn only together with column overlap (owner decision C).
The fix for every finding here belongs to the `std-database` skill.
"""
import re

import _archdup
import _archrules
import _archsubjects as subj

SNAPSHOT_TABLE = re.compile(r"(?:_items|_lines)$|^(?:invoices|orders|receipts)$")
SNAPSHOT_COLUMN = re.compile(r"(?:price|amount|total|tax|cost|name|title|sku)")
TENANT_KEYS = ("organization_id", "tenant_id")
GENERIC_COLUMNS = frozenset(("name", "title", "description", "status", "state", "position", "notes", "type", "kind",
                             "slug", "label", "active", "enabled", "metadata", "data", "settings"))


def _place(table):
    return {"path": table["path"], "line": table["line"], "symbol": table["name"], "context": table["context"]}


def _context_grade(a, b):
    """'same', 'declared-apart' (quiet) or 'apart' (info)."""
    if a["context"] == b["context"]:
        return "same"
    return "declared-apart" if a["declared"] and b["declared"] else "apart"


def _excluded(a, b):
    return _archdup.exclusion(a) or _archdup.exclusion(b) or ("per-type" if _archdup.per_type_pair(a, b) else None)


def _dk1_grade(kind, overlap, apart, excluded):
    j, _, facts = overlap
    strong = (facts >= 3 and j >= 0.4) if kind != "synonym" else (facts >= 4 and j >= 0.6)
    if apart or excluded or not strong:
        return "info", "low" if facts == 0 else "medium"
    return "warn", "high" if kind == "exact" else "medium"


def _dk1_pair(view, a, b):
    if a["name"].lower() == b["name"].lower():
        return None
    kind = _archdup.name_match((a["norm"], a["near"]), (b["norm"], b["near"]), view.groups)
    grade = _context_grade(a, b) if kind else "declared-apart"
    if grade == "declared-apart":
        return None
    overlap = _archdup.jaccard(subj.keys(a), subj.keys(b))
    excluded = _excluded(a, b)
    severity, confidence = _dk1_grade(kind, overlap, grade == "apart", excluded)
    shared = [subj.keys(a).get(k) or subj.keys(b).get(k) for k in overlap[1]][:5]
    text = "%s:%d declares %s; %s (%s:%d) is the same concept in context %s: %s %s~%s, %d shared columns (J=%.2f)%s. Extend %s, or declare %s with an ADR." % (
        a["path"], a["line"], a["name"], b["name"], b["path"], b["line"], a["context"], kind, a["norm"], b["norm"],
        overlap[2], overlap[0], " [excluded: %s]" % excluded if excluded else "", b["name"], a["name"])
    return _archrules.make("DK1", _place(a), text, related=[_place(b)], severity=severity, confidence=confidence,
                           key=tuple(sorted((a["name"].lower(), b["name"].lower()))),
                           evidence={"name_match": kind, "jaccard": overlap[0], "shared": shared, "excluded": excluded},
                           remedy="Extend %s, or declare %s in intentional_duplicates with an ADR." % (b["name"], a["name"]))


def _each_pair(view, delta, mode, judge):
    """judge(view, a, b) over the candidate pairs until the run's deadline (`_archrules.out_of_time`)."""
    found = []
    for a, b in subj.pairs(view, delta, mode):
        if _archrules.out_of_time(view):
            break
        finding = judge(view, a, b)
        if finding:
            found.append(finding)
    return found


def detect_dk1(view, delta, config):
    return _each_pair(view, delta, "name", _dk1_pair)


def _dk2_pair(view, a, b):
    if a["name"].lower() == b["name"].lower() or _archdup.name_match((a["norm"], a["near"]), (b["norm"], b["near"]), view.groups):
        return None
    j, keys, facts = _archdup.jaccard(subj.keys(a), subj.keys(b))
    grade = _context_grade(a, b)
    if grade == "declared-apart" or facts < 3 or j < 0.4:
        return None
    options = getattr(view, "options", None) or {}
    warn = facts >= (options.get("min_shared") or 4) and j >= (options.get("min_jaccard") or 0.6) and grade == "same" and not _excluded(a, b)
    values = [k for k in keys if k.startswith("value:")]
    text = "%s:%d %s shares %d columns with %s (%s:%d) in context %s (J=%.2f: %s)%s. One fact belongs in one table: extend %s, or declare %s as intentional." % (
        a["path"], a["line"], a["name"], facts, b["name"], b["path"], b["line"], a["context"], j,
        ", ".join(subj.keys(a).get(k) or k for k in keys[:5]),
        "; the %s columns suggest a value object" % "/".join(v[6:] for v in values) if values else "", b["name"], a["name"])
    return _archrules.make("DK2", _place(a), text, related=[_place(b)], severity="warn" if warn else "info",
                           confidence="medium" if warn else "low", key=tuple(sorted((a["name"].lower(), b["name"].lower()))),
                           evidence={"jaccard": j, "shared": keys[:5], "excluded": _excluded(a, b)})


def detect_dk2(view, delta, config):
    return _each_pair(view, delta, "columns", _dk2_pair)


def _fk_parents(table, tables):
    parents = {}
    for column in table["columns"]:
        name = column["name"].lower()
        if column.get("fk_table"):
            parents[name] = column["fk_table"]
        elif name.endswith("_id") and _archdup.pluralize(name[:-3]) in tables:
            parents[name] = _archdup.pluralize(name[:-3])
    return parents


def _dk3_column(table, column, fk, parent):
    prefix = fk[:-3] + "_"
    name, family = column["name"].lower(), column.get("family")
    parent_cols = {c["name"].lower(): c.get("family") for c in parent["columns"]}
    if name.startswith(prefix) and name[len(prefix):] not in ("id", "") and parent_cols.get(name[len(prefix):]) == family:
        rest = name[len(prefix):]
        snapshot = SNAPSHOT_TABLE.search(table["name"].lower()) and (family == "decimal" or SNAPSHOT_COLUMN.search(rest))
        return rest, "info" if snapshot else "warn"
    composite = any(fk in c["columns"] and name in c["columns"] for c in table.get("composite_fks") or [])
    copyable = name in TENANT_KEYS or (name not in _archdup.INFRA_COLUMNS and name not in GENERIC_COLUMNS and not name.endswith("_id"))
    if name in parent_cols and parent_cols[name] == family and copyable and not composite:
        return name, "info"
    return None


def _dk3_finding(table, column, link, hit):
    fk, parent = link
    rest, severity = hit
    text = "%s.%s copies %s.%s through %s.%s. A copy needs a declared source and sync path (a view, a trigger, or a snapshot taken on create); otherwise read it through the association." % (
        table["name"], column["name"], parent["name"], rest, table["name"], fk)
    subject = {"path": table["path"], "line": column.get("line") or table["line"], "symbol": "%s.%s" % (table["name"], column["name"]),
               "context": table["context"]}
    return _archrules.make("DK3", subject, text, related=[{"path": parent["path"], "line": parent["line"],
                                                         "symbol": "%s.%s" % (parent["name"], rest), "context": parent["context"]}],
                           severity=severity, confidence="high" if severity == "warn" else "medium",
                           evidence={"fk": "%s.%s" % (table["name"], fk), "same_name": rest == column["name"]})


def _dk3_table(table, tables):
    found = []
    subject_columns = table.get("delta_columns")
    parents = _fk_parents(table, tables)
    for column in (c for c in table["columns"] if subject_columns is None or c["name"] in subject_columns):
        for fk, parent_name in parents.items():
            hit = _dk3_column(table, column, fk, tables[parent_name]) if parent_name in tables and column["name"] != fk else None
            if hit:
                found.append(_dk3_finding(table, column, (fk, tables[parent_name]), hit))
    return found


def _tables_by_name(view, deployable):
    """{name: merged table} for one deployable, built once per run (it used to be rebuilt per subject table)."""
    return view.cached(("tables-by-name", deployable), lambda: {t["name"]: t for t in view.tables(deployable).values()})


def detect_dk3(view, delta, config):
    subjects, pool = subj.subjects(view, delta)
    shared = {t["name"]: t for t in pool} if pool is not None else None
    found = []
    for table in subjects:
        if _archrules.out_of_time(view):
            break
        found.extend(_dk3_table(table, shared if shared is not None else _tables_by_name(view, table["deployable"])))
    return found


def detect_dk4(view, delta, config):
    found = []
    for table in subj.subjects(view, delta)[0]:
        for stem, numbers in _archdup.repeating_groups(table["columns"]).items():
            text = "%s has %d numbered %s columns (%s%d..%s%d), a repeating group: the first-normal-form smell. Move them to a child table, or one array column if they are never queried apart." % (
                table["name"], len(numbers), stem, stem, numbers[0], stem, numbers[-1])
            found.append(_archrules.make("DK4", _place(table), text, severity="warn" if len(numbers) >= 5 else "info",
                                         confidence="high", key=("%s.%s" % (table["name"], stem), ""), evidence={"stem": stem, "numbers": numbers}))
    return found


def detect_mf3(view, delta, config):
    found = []
    for table in subj.subjects(view, delta)[0]:
        shape = _archdup.eav_shape(table)
        if shape:
            text = "%s stores entity-attribute-value rows (%s, %s, %s). Attributes the product filters on belong in columns, and rare ones in one jsonb column, not a key/value table." % (
                table["name"], shape["entity"], shape["key"], shape["value"])
            found.append(_archrules.make("MF3", _place(table), text, confidence="high", key=(table["name"], ""), evidence=shape))
    return found


def detect_mf5(view, delta, config):
    sites = ([dict(s, path=delta["path"]) for s in delta["facts"]["jsonb"]] if delta is not None else view.rows("jsonb"))
    found = []
    for site in sites:
        text = "%s:%d filters or sorts on the JSON key %s->%s, so that key is used as a column. A key the database filters, sorts, joins or constrains on is a column." % (
            site["path"], site["line"], site["field"], site["key"])
        found.append(_archrules.make("MF5", {"path": site["path"], "line": site["line"], "symbol": "%s.%s" % (site["field"], site["key"])},
                                     text, confidence=site.get("confidence") or "medium",
                                     key=("%s:%s.%s" % (site["path"], site["field"], site["key"]), ""),
                                     evidence={"field": site["field"], "key": site["key"]}))
    return found
