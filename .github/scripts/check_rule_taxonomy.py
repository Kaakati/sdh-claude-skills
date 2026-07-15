#!/usr/bin/env python3
"""Verify each rule-per-file skill's body agrees with its canonical taxonomy.

`rules/_sections.md` is the ground truth for a skill's sections: it owns each section's
impact level and the filename prefix that groups its rules. The SKILL.md body restates that
taxonomy, and the body is what the model actually reads — so when the two disagree, the model
is handed the wrong priorities.

This is not hypothetical. `react-native-best-practices` had silently collapsed 14 canonical
sections into 8 invented ones: it dropped "Core Rendering" (CRITICAL — "violations cause
runtime crashes or broken UI") entirely and promoted List Performance into the vacant top
slot. Nothing caught it, because nothing checked.

Run locally exactly as CI does:

    python3 .github/scripts/check_rule_taxonomy.py

What is enforced (semantics, not cosmetics):
  1. every section's prefix claims at least one rule file on disk;
  2. every rule file on disk is claimed by exactly one section;
  3. the body carries a heading for each section with the SAME impact label.

Heading numbering is deliberately NOT enforced: `### 1. Atoms (HIGH)` and `### Atoms (HIGH)`
are both accepted, because both conventions are in use and neither is wrong. Gate the
invariant, not the house style — a gate that fires on a legitimate variation trains people to
ignore it.
"""

import glob
import os
import re
import sys

# Two _sections.md formats are in use, both fine:
#   heading form: "## 1. Core Rendering (rendering)" + "**Impact:** CRITICAL"
#   table form:   "| 1 | Security | `sec-` | CRITICAL | ... |"
HEADING_FORM = re.compile(
    r"^## (\d+)\.\s+(.+?)\s+\((.+?)\)\s*$\n+\*\*Impact:\*\*\s*([A-Z][A-Z-]*)\s*$",
    re.M,
)
TABLE_FORM = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*`([^`|]+?)`\s*\|\s*([A-Z][A-Z-]*)\s*\|",
    re.M,
)


def parse_sections(path):
    """Return [(num, name, prefix, impact)] plus the format name, or ([], None)."""
    text = open(path, encoding="utf-8").read()
    for pattern, label in ((HEADING_FORM, "heading"), (TABLE_FORM, "table")):
        found = pattern.findall(text)
        if found:
            return [
                (int(num), name.strip(), prefix.strip().rstrip("-"), impact.strip())
                for num, name, prefix, impact in found
            ], label
    return [], None


def body_declares(body, num, name, impact):
    """True if the body heads this section with the same impact. Numbering optional."""
    pattern = rf"^#{{2,4}}\s+(?:{num}\.\s+)?{re.escape(name)}\s+\({re.escape(impact)}\)\s*$"
    return re.search(pattern, body, re.M) is not None


def check_skill(sections_path, failures):
    skill_dir = os.path.dirname(os.path.dirname(sections_path))
    body_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(body_path):
        failures.append(f"{skill_dir}: has rules/_sections.md but no SKILL.md")
        return

    body = open(body_path, encoding="utf-8").read()
    sections, form = parse_sections(sections_path)
    if not sections:
        failures.append(
            f"{sections_path}: no sections parsed — the file format changed. Expected either "
            f"'## N. Name (prefix)' + '**Impact:** LEVEL', or a '| N | Name | `prefix-` | LEVEL |' "
            f"table row. Fix the file, or teach {os.path.basename(__file__)} the new format."
        )
        return

    rules = sorted(
        os.path.basename(p)[:-3]
        for p in glob.glob(os.path.join(skill_dir, "rules", "*.md"))
        if not os.path.basename(p).startswith("_")
    )

    claimed = {}
    for num, name, prefix, impact in sections:
        hits = [r for r in rules if r == prefix or r.startswith(prefix + "-")]
        if not hits:
            failures.append(
                f"{sections_path}: section '{name}' claims prefix '{prefix}-', which matches no "
                f"rule file. Rename the rules to that prefix, or drop the section."
            )
        for hit in hits:
            claimed.setdefault(hit, []).append(f"{name} ('{prefix}-')")
        if not body_declares(body, num, name, impact):
            failures.append(
                f"{body_path}: section '{name}' is not declared with impact {impact}. Add or fix "
                f"the heading (e.g. '### {num}. {name} ({impact})' or '### {name} ({impact})') so "
                f"it matches rules/_sections.md, which is the source of truth."
            )

    for rule in rules:
        owners = claimed.get(rule)
        if not owners:
            failures.append(
                f"{skill_dir}: rule '{rule}' is claimed by no section in rules/_sections.md — the "
                f"body cannot group it. Rename it to an existing prefix, or add a section for it."
            )
        elif len(owners) > 1:
            failures.append(
                f"{skill_dir}: rule '{rule}' is claimed by {len(owners)} sections ({', '.join(owners)}). "
                f"Prefixes must be unambiguous — make one prefix more specific."
            )

    return len(sections), len(rules), form


def main():
    sections_files = sorted(glob.glob("skills/*/rules/_sections.md"))
    if not sections_files:
        print("FAIL: no skills/*/rules/_sections.md found — run from the repo root.")
        return 1

    failures = []
    for path in sections_files:
        result = check_skill(path, failures)
        if result:
            count, rules, form = result
            skill = os.path.basename(os.path.dirname(os.path.dirname(path)))
            print(f"  {skill:30} {count:2} sections / {rules:2} rules  [{form}]")

    if failures:
        print()
        print("\n".join("FAIL: " + f for f in failures))
        return 1

    print(f"\nrule taxonomy OK — {len(sections_files)} skills agree with their _sections.md and disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
