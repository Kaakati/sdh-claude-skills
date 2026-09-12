#!/usr/bin/env python3
"""
PostToolUse hook: Atomic Design convention checker.

Validates component hierarchy rules (atom independence, molecule composition,
organism boundaries) and naming conventions across Phlex, ReactJS, Next.js,
and React Native, per the `atomic-design` skill. Outputs warnings only — never blocks.

JS/TS imports are read the way they are written: named, default, namespace and side-effect
imports, `import()` and `require()`. Relative specifiers resolve against the file; alias
specifiers (`@/components/organisms/Header`) classify by their `components/<level>/` segment.
The old pattern needed the quote straight after `import`, so every named import - including the
skill's own violation examples - went unflagged. A `./Button.styles` or `./Card.css` inside the
component's own folder is co-location, not a sibling import, and `import type` composes nothing.
Checks follow the file's language: a .tsx under app/components is checked as JS, not as Phlex.

Vendored shadcn/ui primitives (components.json `aliases.ui`) are CLI-owned, so they are skipped
even when that alias points into an atomic directory.
"""
import os
import posixpath
import re

import _hooklib as hooklib
import _vendored as vendored


# Extensions to check per platform
RUBY_EXTENSIONS = (".rb",)
JS_EXTENSIONS = (".tsx", ".jsx", ".ts", ".js")
ALL_EXTENSIONS = RUBY_EXTENSIONS + JS_EXTENSIONS

# Atomic levels in hierarchy order
ATOMIC_LEVELS = ("atoms", "molecules", "organisms", "templates")

# Canonical (wrapper-agnostic) directories that contain atomic design components
PHLEX_COMPONENT_DIR = "app/components"
PHLEX_VIEW_DIR = "app/views"
FRONTEND_COMPONENT_DIR = "src/components"

# Barrel file names (exempt from same-level import checks)
BARREL_FILES = ("index.ts", "index.tsx", "index.js", "index.jsx")

# Ruby render pattern: render Components::Level::ComponentName
RUBY_RENDER_PATTERN = re.compile(
    r"render\s+Components::(Atoms|Molecules|Organisms|Templates)::", re.IGNORECASE
)

# `import X from`, `import { X } from`, `import * as X from`, `import "x"` - group 1 marks
# `import type` - plus `import("x")` and `require("x")`.
JS_IMPORT_PATTERN = re.compile(
    r"""^[ \t]*import\s+(type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?["']([^"']+)["']"""
    r"""|\b(?:import|require)\s*\(\s*["']([^"']+)["']\s*\)""",
    re.MULTILINE,
)
# `components/<level>/<Component>` inside a resolved relative path or an alias specifier.
LEVEL_SEGMENT = re.compile(r"(?:^|/)components/(atoms|molecules|organisms|templates)(?:/([^/]+))?")

# Levels each level may NOT import. Its own level is allowed only inside its own component folder.
FORBIDDEN_IMPORTS = {
    "atoms": ("atoms", "molecules", "organisms", "templates"),
    "molecules": ("molecules", "organisms", "templates"),
    "organisms": ("organisms", "templates"),
}


def get_atomic_level(normalized_path):
    """Determine the atomic level of a file from its path.

    Returns a tuple (level, platform) where level is one of
    'atoms', 'molecules', 'organisms', 'templates', or None,
    and platform is 'phlex' or 'frontend' or None.
    """
    # Check Phlex (Ruby) component directories
    if hooklib.under(normalized_path, PHLEX_COMPONENT_DIR):
        after = normalized_path.split(PHLEX_COMPONENT_DIR + "/", 1)[1]
        for level in ATOMIC_LEVELS:
            if after.startswith(level + "/"):
                return level, "phlex"
        return None, None

    # Check frontend component directories (web, next, mobile)
    if hooklib.under(normalized_path, FRONTEND_COMPONENT_DIR):
        after = normalized_path.split(FRONTEND_COMPONENT_DIR + "/", 1)[1]
        for level in ATOMIC_LEVELS:
            if after.startswith(level + "/"):
                return level, "frontend"
        return None, None

    return None, None


def is_barrel_file(normalized_path):
    """Check if the file is a barrel (index) file."""
    basename = os.path.basename(normalized_path)
    return basename in BARREL_FILES


def get_display_path(normalized_path):
    """Extract a short display path for warning messages."""
    for component_dir in (PHLEX_COMPONENT_DIR, FRONTEND_COMPONENT_DIR):
        if hooklib.under(normalized_path, component_dir):
            return normalized_path.split(component_dir + "/", 1)[1]
    return os.path.basename(normalized_path)


def check_atom_imports_ruby(content, display_path):
    """Atoms cannot render any other components (Phlex/Ruby)."""
    warnings = []
    for match in RUBY_RENDER_PATTERN.finditer(content):
        warnings.append(
            f"WARNING: Atomic Design violation (see the `atomic-design` skill) in {display_path} — "
            f"Atoms cannot render other components. Found: {match.group(0).strip()}"
        )
    return warnings


def check_molecule_imports_ruby(content, display_path):
    """Molecules can only compose atoms (Phlex/Ruby)."""
    warnings = []
    for match in RUBY_RENDER_PATTERN.finditer(content):
        target_level = match.group(1).lower()
        if target_level in ("molecules", "organisms", "templates"):
            warnings.append(
                f"WARNING: Atomic Design violation in {display_path} — "
                f"Molecules can only compose atoms. Found: {match.group(0).strip()}"
            )
    return warnings


def check_organism_imports_ruby(content, display_path):
    """Organisms can compose atoms and molecules, not other organisms or templates (Phlex/Ruby)."""
    warnings = []
    for match in RUBY_RENDER_PATTERN.finditer(content):
        target_level = match.group(1).lower()
        if target_level in ("organisms", "templates"):
            warnings.append(
                f"WARNING: Atomic Design violation in {display_path} — "
                f"Organisms cannot render other organisms or templates. "
                f"Found: {match.group(0).strip()}"
            )
    return warnings


def resolve_import(spec, file_dir):
    """(level, component) an import specifier targets; (None, None) outside the atomic tree."""
    if spec.startswith("."):
        spec = posixpath.normpath(posixpath.join(file_dir, spec))
    match = LEVEL_SEGMENT.search(spec)
    if not match:
        return None, None
    return match.group(1), (match.group(2) or "").split(".")[0]


def own_component(normalized_path, level):
    """The component a file belongs to: its folder under the level, or its own base name."""
    match = re.search(rf"(?:^|/)components/{level}/([^/]+)", normalized_path)
    return match.group(1).split(".")[0] if match else ""


def import_problem(level, target, own, spec):
    """Why one import breaks the level rules, or None when it is allowed."""
    target_level, target_component = target
    if target_level not in FORBIDDEN_IMPORTS.get(level, ()):
        return None
    if target_level == level and target_component == own:
        return None  # co-located: ./Button.styles, ./Card.css, the component folder's own index
    if target_level == level:
        return f"{level.capitalize()} cannot import sibling {level}. Found import: {spec}"
    if level == "molecules":
        return f"Molecules can only compose atoms. Found import from {target_level}/: {spec}"
    return f"{level.capitalize()} cannot import from {target_level}/. Found import: {spec}"


def check_imports_js(content, level, normalized_path):
    """Hierarchy violations among a JS/TS component's imports (templates have no restrictions)."""
    warnings = []
    display_path = get_display_path(normalized_path)
    file_dir = posixpath.dirname(normalized_path)
    own = own_component(normalized_path, level)
    for match in JS_IMPORT_PATTERN.finditer(content):
        spec = match.group(2) or match.group(3)
        target = (None, None) if match.group(1) else resolve_import(spec, file_dir)
        problem = import_problem(level, target, own, spec)
        if problem:
            warnings.append(
                f"WARNING: Atomic Design violation (see the `atomic-design` skill) in "
                f"{display_path} — {problem}"
            )
    return warnings


def check_naming_convention(normalized_path, ext, display_path):
    """Validate naming conventions for component files."""
    basename = os.path.basename(normalized_path)
    name_without_ext = os.path.splitext(basename)[0]

    # Skip barrel files
    if basename in BARREL_FILES:
        return None

    if ext in RUBY_EXTENSIONS:
        # Ruby files should be snake_case
        if re.search(r"[A-Z]", name_without_ext):
            return (
                f"WARNING: Naming convention — Ruby component files should use "
                f"snake_case. Found: {basename}"
            )
    elif ext in (".tsx", ".jsx"):
        # TSX/JSX component files should be PascalCase
        if "_" in name_without_ext:
            return (
                f"WARNING: Naming convention — React/Next.js/RN component files "
                f"(.tsx/.jsx) should use PascalCase. Found: {basename}"
            )

    return None


def check_hierarchy(level, ext, content, normalized_path):
    """Dispatch hierarchy checks by atomic level and the file's own language."""
    if ext not in RUBY_EXTENSIONS:
        return check_imports_js(content, level, normalized_path)
    ruby_check = {
        "atoms": check_atom_imports_ruby,
        "molecules": check_molecule_imports_ruby,
        "organisms": check_organism_imports_ruby,
    }.get(level)
    return ruby_check(content, get_display_path(normalized_path)) if ruby_check else []


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in ALL_EXTENSIONS:
        return []

    normalized = hooklib.normalize(file_path)

    # Atomic level from the path; a vendored shadcn primitive is CLI-owned wherever it sits.
    level, _platform = get_atomic_level(normalized)
    if level is None or vendored.is_vendored_ui(file_path):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    # Barrel files re-export their level by design, so they skip the hierarchy checks
    warnings = [] if is_barrel_file(normalized) else check_hierarchy(level, ext, content, normalized)
    naming_warning = check_naming_convention(normalized, ext, get_display_path(normalized))
    if naming_warning:
        warnings.append(naming_warning)
    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
