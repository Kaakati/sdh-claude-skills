#!/usr/bin/env python3
"""The orthogonality finding contract, shared by the hooks and the skill scripts.

A finding (JSON schema sdh.orthogonality/v1, design §1.2 and §3.4):
    id, slug, class, severity (warn | info | note), confidence (high | medium | low), new,
    fingerprint = sha1(detector | normalized subject | normalized counterpart),
    subject {path, line, symbol, context}, related [...], evidence {...}, owner_skill,
    policy_skill "orthogonality", remedy, suppress {config, inline}, source "sdh", message
plus `suppressed` ("config" | "marker") and `expired` (an until date in the past) when they apply.

Hooks show a finding only when it is warn, high or medium confidence, new against the baseline, not
suppressed, and not already shown this session; scans list everything. Suppression is an
`intentional_duplicates` entry in `.claude/orthogonality.json` or an inline `sdh:orthogonal-ok <ID> <reason>`
comment on the subject line or the line above; every rendered line states that route. A marker with no
reason is itself a CFG-MARKER warning. Nothing here asks or denies. A detector loop past the run's deadline
(`out_of_time`) stops and is reported as not run, never as complete.
"""
import hashlib
import importlib
import json
import time

import _archconfig
import _archstore

POLICY_SKILL = "orthogonality"
MAX_LINE = 320
BUDGET_REASON = "time budget reached"
CATALOG = {
    "DK1": ("duplicate-concept", "duplicated-knowledge", "std-database"),
    "DK2": ("overlapping-columns", "duplicated-knowledge", "std-database"),
    "DK3": ("fact-reachable-through-fk", "duplicated-knowledge", "std-database"),
    "DK4": ("repeating-group", "duplicated-knowledge", "std-database"),
    "DK5": ("rule-in-two-places", "duplicated-knowledge", "std-database"),
    "DK6": ("copy-paste-block", "duplicated-knowledge", "std-code-standards"),
    "CM1": ("second-library", "competing-mechanisms", POLICY_SKILL),
    "CM2": ("second-client-wrapper", "competing-mechanisms", "std-code-standards"),
    "CM3": ("second-error-envelope", "competing-mechanisms", "std-api-design"),
    "CM4": ("second-pagination-style", "competing-mechanisms", "std-api-design"),
    "CM5": ("second-auth-mechanism", "competing-mechanisms", "std-security"),
    "BC1": ("cross-context-dependency", "boundary-coupling", POLICY_SKILL),
    "BC2": ("new-cycle", "boundary-coupling", POLICY_SKILL),
    "BC3": ("cross-context-write", "boundary-coupling", POLICY_SKILL),
    "BC4": ("multi-context-transaction", "boundary-coupling", POLICY_SKILL),
    "FC1": ("file-cycle", "boundary-coupling", "std-clean-architecture"),
    "MF1": ("wrong-context-file", "misfit", POLICY_SKILL),
    "MF2": ("first-of-kind-pattern", "misfit", POLICY_SKILL),
    "MF3": ("eav-table", "misfit", "std-database"),
    "MF4": ("sti-bloat", "misfit", "std-database"),
    "MF5": ("jsonb-key-as-column", "misfit", "std-database"),
    "TF1": ("reimplemented-module", "terraform", "std-terraform-conventions"),
    "TF2": ("module-version-divergence", "terraform", "monorepo-architect"),
    "TF3": ("duplicate-singleton", "terraform", "std-infrastructure"),
    "CFG-INVALID": ("invalid-config", "declaration", POLICY_SKILL),
    "CFG-ADR": ("missing-adr", "declaration", POLICY_SKILL),
    "CFG-READMODEL": ("incomplete-read-model", "declaration", POLICY_SKILL),
    "CFG-MARKER": ("marker-without-reason", "declaration", POLICY_SKILL),
    "TOOL": ("tool-violation", "community-tool", POLICY_SKILL),
}
EDIT_TIME = ("DK1", "DK2", "DK3", "DK4", "MF3", "MF5", "CM1", "CM2", "CM3", "CM4", "BC1", "BC2", "BC3")
FAMILIES = {
    "duplicates": ("DK1", "DK2", "DK3", "DK4", "DK5", "DK6", "MF3", "MF4", "MF5"),
    "boundaries": ("BC1", "BC2", "BC3", "BC4", "MF1", "FC1"),
    "mechanisms": ("CM1", "CM2", "CM3", "CM4", "CM5", "MF2"),
    "terraform": ("TF1", "TF2", "TF3"),
}
ALL_DETECTORS = FAMILIES["duplicates"] + FAMILIES["boundaries"] + FAMILIES["mechanisms"] + FAMILIES["terraform"]
NOT_IMPLEMENTED = {
    "DK5": "belongs to database-design-checker.py as its check 5 (design phase 2)",
    "MF4": "needs whole-codebase column usage per STI subclass (design phase 2)",
    "TF3": "account-singleton detection is low confidence (design phase 2)",
}
_MODULES = (("DK6", "_archdetect_clone"), ("DK", "_archdetect_db"), ("MF3", "_archdetect_db"), ("MF5", "_archdetect_db"),
            ("CM", "_archdetect_mech"), ("MF2", "_archdetect_mech"), ("BC", "_archdetect_bound"),
            ("MF1", "_archdetect_bound"), ("FC1", "_archdetect_bound"), ("TF", "_archdetect_bound"))


def _norm(value):
    return " ".join(str(value or "").lower().split())


def fingerprint(detector, subject, counterpart=""):
    return hashlib.sha1(("%s|%s|%s" % (detector, _norm(subject), _norm(counterpart))).encode("utf-8")).hexdigest()


def skill_tail(owner):
    if owner in (None, POLICY_SKILL):
        return "Per the `orthogonality` skill."
    return "Fix: the `%s` skill; policy: the `orthogonality` skill." % owner


def make(detector, subject, text, **fields):
    """A finding. subject: {path, line, symbol, context}. fields: related, evidence, severity, confidence, owner_skill,
    remedy, key (subject key, counterpart key), suppress_config. Every related entry leaves with the subject's four
    keys (`context: None` when a detector has none), so the v1 JSON has one shape for every detector."""
    slug, klass, owner = CATALOG[detector]
    related = [dict({"context": None}, **entry) for entry in fields.get("related") or []]
    key = fields.get("key") or (subject.get("symbol"), related[0].get("symbol") if related else "")
    return {
        "id": detector, "slug": slug, "class": klass, "severity": fields.get("severity", "warn"),
        "confidence": fields.get("confidence", "medium"), "new": True, "fingerprint": fingerprint(detector, key[0], key[1]),
        "subject": {"path": subject.get("path") or "", "line": int(subject.get("line") or 0),
                    "symbol": subject.get("symbol") or "", "context": subject.get("context")},
        "related": related, "evidence": fields.get("evidence") or {}, "owner_skill": fields.get("owner_skill") or owner,
        "policy_skill": POLICY_SKILL, "remedy": fields.get("remedy", ""),
        "suppress": {"config": fields.get("suppress_config", "intentional_duplicates"),
                     "inline": "sdh:orthogonal-ok %s <reason>" % detector},
        "source": "sdh", "text": text,
    }


def suppression_route(finding, short=False):
    """How to keep a finding: the inline marker (not on a .json subject), then the config key with an ADR (`short`: marker only)."""
    suppress = finding.get("suppress") or {}
    config = suppress.get("config") or "-"
    if config == "-":
        return ""
    marker = "" if finding["subject"]["path"].endswith(".json") else suppress.get("inline") or ""
    if marker and short:
        return " Keep: %s." % marker
    return " Keep: %s%s with an ADR." % (marker + ", or " if marker else "", config)


def _fit(body, room):
    """`body` within `room` characters: whole trailing sentences go first, then a hard cut."""
    while len(body) > room and ". " in body:
        body = body.rsplit(". ", 1)[0] + "."
    return body if len(body) <= room else body[:max(0, room - 3)].rstrip() + "..."


def render(finding):
    """The one-line message within MAX_LINE characters, always ending with the route, then the skill pointers."""
    head = "ORTHOGONALITY [%s %s] " % (finding["id"], finding["slug"])
    expired = " The declaration covering this expired on %s." % finding["expired"] if finding.get("expired") else ""
    tail = " " + skill_tail(finding.get("owner_skill"))
    body = (finding.get("text") or "").strip()
    route = suppression_route(finding)
    if len(head) + len(body) + len(expired) + len(route) + len(tail) > MAX_LINE:
        route = suppression_route(finding, short=True)
    return head + _fit(body, MAX_LINE - len(head) - len(expired) - len(route) - len(tail)) + expired + route + tail


def public(finding):
    return dict({k: v for k, v in finding.items() if k != "text"}, message=render(finding))


def detector_function(detector):
    for prefix, module_name in _MODULES:
        if detector.startswith(prefix):
            return getattr(importlib.import_module(module_name), "detect_" + detector.lower())
    raise KeyError(detector)


def out_of_time(view):
    """True past the running detectors' deadline; a loop that sees it stops, and the detector is reported as not run."""
    deadline = getattr(view, "deadline", None)
    if deadline is not None and time.monotonic() > deadline:
        view.cut_short = True
        return True
    return False


def run_detectors(view, delta, detectors, deadline=None):
    """(findings, not_run {detector: reason}) for `detectors` in order until `deadline` (monotonic; loops check `out_of_time`)."""
    findings, not_run, seen = [], {}, set()
    view.deadline = deadline
    for detector in detectors:
        view.cut_short = False
        if detector in NOT_IMPLEMENTED or out_of_time(view):
            not_run[detector] = NOT_IMPLEMENTED.get(detector, BUDGET_REASON)
            continue
        for finding in detector_function(detector)(view, delta, view.config) or []:
            if finding["fingerprint"] not in seen:
                seen.add(finding["fingerprint"])
                findings.append(finding)
        if view.cut_short:
            not_run[detector] = BUDGET_REASON
    return findings, not_run


def marker_findings(markers, path):
    """CFG-MARKER for every sdh:orthogonal-ok marker with no detector id or no reason."""
    found = []
    for marker in markers:
        if marker.get("detector") and (marker.get("reason") or "").strip():
            continue
        text = "%s:%d has an `sdh:orthogonal-ok %s` marker with no reason, so it suppresses nothing. Add the reason (and an ADR for anything cross-cutting)." % (
            path, marker["line"], marker.get("detector") or "<ID>")
        found.append(make("CFG-MARKER", {"path": path, "line": marker["line"], "symbol": marker.get("detector") or ""}, text,
                          confidence="high", key=(path, marker["line"]), suppress_config="-"))
    return found


def declaration_findings(config, root):
    found = []
    for item in _archconfig.declaration_findings(config, root):
        if item["id"] == "CFG-ADR":
            text = "%s %s names %s, which does not exist; a declaration must point to a real ADR." % (
                _archconfig.CONFIG_REL, item["json_path"], item["adr"])
        else:
            text = "%s %s declares a read model without %s, so its source, refresh path and writers are unstated." % (
                _archconfig.CONFIG_REL, item["json_path"], ", ".join(item["missing"]))
        found.append(make(item["id"], {"path": _archconfig.CONFIG_REL, "line": 1, "symbol": item["json_path"]}, text,
                          confidence="high", key=(item["json_path"], item.get("adr", "")), suppress_config="-"))
    return found


def _marker_covers(finding, markers):
    line = finding["subject"]["line"]
    return any(m.get("detector") == finding["id"] and (m.get("reason") or "").strip() and m["line"] in (line, line - 1)
               for m in markers)


def apply_suppressions(findings, view, delta):
    """Mark findings suppressed by an unexpired declaration or a reasoned inline marker."""
    markers_by_path = {}
    for finding in findings:
        counterpart = (finding["related"] or [{}])[0].get("symbol", "")
        entry = _archconfig.intentional(view.config, finding["id"], finding["subject"]["symbol"], counterpart)
        if entry and _archconfig.expired(entry.get("until")):
            finding["expired"] = entry["until"]
        elif entry:
            finding["suppressed"] = "config"
        path = finding["subject"]["path"]
        if path not in markers_by_path:
            markers_by_path[path] = view.markers(path, delta)
        if _marker_covers(finding, markers_by_path[path]):
            finding["suppressed"] = "marker"
    return findings


def covered_detectors(view):
    return set(json.loads(view.meta("baseline_detectors", "[]") or "[]"))


def mark_new(findings, view):
    """new = the fingerprint is absent from the baseline (every finding is new for an uncovered detector)."""
    baseline, covered = view.baseline(), covered_detectors(view)
    for finding in findings:
        finding["new"] = not (finding["id"] in covered and finding["fingerprint"] in baseline)
    return findings


def hook_visible(finding):
    return (finding["severity"] == "warn" and finding["confidence"] in ("high", "medium")
            and finding.get("new", True) and not finding.get("suppressed"))


def _priority(finding):
    order = list(EDIT_TIME)
    return (0 if finding["confidence"] == "high" else 1, order.index(finding["id"]) if finding["id"] in order else len(order))


def hook_lines(findings, event, limit=3):
    """At most `limit` rendered lines of hook-visible findings not yet shown this session."""
    import _hooklib
    lines = []
    for finding in sorted((f for f in findings if hook_visible(f)), key=_priority):
        if len(lines) < limit and _hooklib.first_in_session(event, "orth-" + finding["fingerprint"][:16]):
            lines.append(render(finding))
    return lines


def ensure_baseline(store, findings, detectors, reason="first complete index"):
    """Stamp the baseline for detectors it does not cover yet; returns the detectors newly covered."""
    covered = set(json.loads(store.get_meta("baseline_detectors", "[]") or "[]"))
    fresh = [d for d in detectors if d not in covered and d not in NOT_IMPLEMENTED]
    if not fresh:
        return []
    now = _archstore.now_iso()
    rows = [{"fingerprint": f["fingerprint"], "detector": f["id"], "subject": f["subject"]["symbol"], "first_seen": now}
            for f in findings if f["id"] in fresh]
    store.begin()
    store.insert_many("findings_baseline", rows)
    store.insert_many("baseline_history", [{"taken_at": now, "detector": d, "count": len([r for r in rows if r["detector"] == d]),
                                            "reason": reason} for d in fresh])
    store.set_meta("baseline_detectors", json.dumps(sorted(covered | set(fresh))))
    store.set_meta("baseline_at", store.get_meta("baseline_at") or now)
    store.commit()
    return fresh


def replace_baseline(store, findings, detectors, reason):
    """--update-baseline: re-stamp the baseline for `detectors` from the current findings."""
    store.begin()
    store.delete("findings_baseline", {"detector": list(detectors)})
    store.set_meta("baseline_detectors", json.dumps(sorted(set(json.loads(store.get_meta("baseline_detectors", "[]") or "[]")) - set(detectors))))
    store.commit()
    ensure_baseline(store, findings, detectors, reason)
    store.set_meta("baseline_at", _archstore.now_iso())
    store.commit()


def summary(findings):
    by_severity, frozen = {}, {}
    for finding in findings:
        by_severity[finding["severity"]] = by_severity.get(finding["severity"], 0) + 1
        if not finding.get("new", True):
            frozen[finding["id"]] = frozen.get(finding["id"], 0) + 1
    return by_severity, frozen
