#!/usr/bin/env python3
"""
PostToolUse hook: Atomic Design convention checker.

Validates component hierarchy rules (atom independence, molecule composition,
organism boundaries) and naming conventions across Phlex, ReactJS, Next.js,
and React Native. Outputs warnings only — never blocks.
"""
import os
import re

import _hooklib as hooklib


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

# JS/TS import patterns
JS_RELATIVE_IMPORT_PATTERN = re.compile(
    r"""(?:import|require)\s*(?:\(?\s*)?['"](\.\./(?:atoms|molecules|organisms|templates)/[^'"]*|\.\/[^'"]*)['"]\)?""",
    re.MULTILINE,
)


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
        target_level = match.group(1).lower()
        warnings.append(
            f"WARNING: Atomic Design violation in {display_path} — "
            f"Atoms cannot render other components. Found: {match.group(0).strip()}"
        )
    return warnings


def check_atom_imports_js(content, display_path):
    """Atoms cannot import from any atomic level (JS/TS)."""
    warnings = []
    for match in JS_RELATIVE_IMPORT_PATTERN.finditer(content):
        import_path = match.group(1)
        # Check imports from any atomic level directory
        for level in ATOMIC_LEVELS:
            if f"/{level}/" in import_path or import_path.startswith(f"../{level}/"):
                warnings.append(
                    f"WARNING: Atomic Design violation in {display_path} — "
                    f"Atoms cannot import from {level}/. Found import: {import_path}"
                )
                break
        else:
            # Check same-level imports (./SiblingAtom)
            if import_path.startswith("./"):
                warnings.append(
                    f"WARNING: Atomic Design violation in {display_path} — "
                    f"Atoms cannot import sibling atoms. Found import: {import_path}"
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


def check_molecule_imports_js(content, display_path):
    """Molecules can only import from atoms (JS/TS)."""
    warnings = []
    forbidden = ("molecules", "organisms", "templates")
    for match in JS_RELATIVE_IMPORT_PATTERN.finditer(content):
        import_path = match.group(1)
        for level in forbidden:
            if f"/{level}/" in import_path or import_path.startswith(f"../{level}/"):
                warnings.append(
                    f"WARNING: Atomic Design violation in {display_path} — "
                    f"Molecules can only compose atoms. Found import from {level}/: {import_path}"
                )
                break
        else:
            # Same-level imports (./SiblingMolecule)
            if import_path.startswith("./"):
                warnings.append(
                    f"WARNING: Atomic Design violation in {display_path} — "
                    f"Molecules cannot import sibling molecules. Found import: {import_path}"
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


def check_organism_imports_js(content, display_path):
    """Organisms can import atoms and molecules, not other organisms or templates (JS/TS)."""
    warnings = []
    forbidden = ("organisms", "templates")
    for match in JS_RELATIVE_IMPORT_PATTERN.finditer(content):
        import_path = match.group(1)
        for level in forbidden:
            if f"/{level}/" in import_path or import_path.startswith(f"../{level}/"):
                warnings.append(
                    f"WARNING: Atomic Design violation in {display_path} — "
                    f"Organisms cannot import from {level}/. Found import: {import_path}"
                )
                break
        else:
            # Same-level imports (./SiblingOrganism)
            if import_path.startswith("./"):
                warnings.append(
                    f"WARNING: Atomic Design violation in {display_path} — "
                    f"Organisms cannot import sibling organisms. Found import: {import_path}"
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


def check_hierarchy(level, platform, content, ext, display_path):
    """Dispatch hierarchy checks based on atomic level and platform."""
    warnings = []

    if level == "atoms":
        if platform == "phlex":
            warnings.extend(check_atom_imports_ruby(content, display_path))
        else:
            warnings.extend(check_atom_imports_js(content, display_path))

    elif level == "molecules":
        if platform == "phlex":
            warnings.extend(check_molecule_imports_ruby(content, display_path))
        else:
            warnings.extend(check_molecule_imports_js(content, display_path))

    elif level == "organisms":
        if platform == "phlex":
            warnings.extend(check_organism_imports_ruby(content, display_path))
        else:
            warnings.extend(check_organism_imports_js(content, display_path))

    # Templates have no upward import restrictions to check

    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in ALL_EXTENSIONS:
        return []

    normalized = hooklib.normalize(file_path)

    # Determine atomic level and platform
    level, platform = get_atomic_level(normalized)
    if level is None:
        return []

    # Skip barrel files from import hierarchy checks
    barrel = is_barrel_file(normalized)

    display_path = get_display_path(normalized)

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []

    # Check hierarchy violations (skip barrel files)
    if not barrel:
        warnings.extend(check_hierarchy(level, platform, content, ext, display_path))

    # Check naming conventions
    naming_warning = check_naming_convention(normalized, ext, display_path)
    if naming_warning:
        warnings.append(naming_warning)

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
