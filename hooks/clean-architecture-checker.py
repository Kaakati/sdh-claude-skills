#!/usr/bin/env python3
"""
PostToolUse hook: Clean Architecture layer boundary checker.

Checks source files for layer boundary violations per clean-architecture.md.
Exits silently for non-source files.
"""
import os
import re

import _hooklib as hooklib


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")


def check_rails_model_imports(content, file_path):
    """Models should not import from controllers or serializers."""
    if not hooklib.under(file_path, "app/models"):
        return []
    warnings = []
    if re.search(r"require.*controllers/", content) or re.search(
        r"require.*serializers/", content
    ):
        warnings.append(
            "WARNING: Model imports controller/serializer — entity depends on "
            "adapter. Move logic to a service per clean-architecture.md."
        )
    return warnings


def check_service_http_concepts(content, file_path):
    """Services should not return HTTP status codes or use render."""
    if not hooklib.under(file_path, "app/services"):
        return []
    warnings = []
    if re.search(r"\bstatus:\s*:\w+", content) or re.search(
        r"\brender\b", content
    ) or re.search(r"\b(status|http_status)\s*=\s*\d{3}\b", content):
        warnings.append(
            "WARNING: Service returns HTTP concepts — use case knows about HTTP. "
            "Return Result objects per clean-architecture.md."
        )
    return warnings


def check_domain_framework_imports(content, file_path):
    """Domain types should not import framework modules."""
    if not hooklib.under(file_path, "src/domain"):
        return []
    warnings = []
    framework_imports = re.compile(
        r"""(?:import|require)\s*(?:\{[^}]*\}\s*from\s*)?['"](react|react-native|next|@next/|vue|angular)"""
    )
    if framework_imports.search(content):
        warnings.append(
            "WARNING: Domain type imports framework module — entity depends on "
            "framework per clean-architecture.md."
        )
    return warnings


def check_screen_direct_api_import(content, file_path, ext):
    """Screens/pages should not import API clients directly."""
    is_screen = hooklib.under_any(file_path, ("src/screens", "src/pages")) or (
        ext in (".tsx", ".jsx") and hooklib.under(file_path, "app")
    )
    if not is_screen:
        return []
    warnings = []
    # Check for direct axios/fetch/api client imports (not hooks)
    api_import = re.compile(
        r"""(?:import|require)\s*(?:\{[^}]*\}\s*from\s*)?['"](?:axios|\.\.?/api/|\.\.?/services/|@/api/)"""
    )
    if api_import.search(content):
        warnings.append(
            "WARNING: Screen/page imports API client directly — use a hook as "
            "intermediary per clean-architecture.md."
        )
    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []
    warnings.extend(check_rails_model_imports(content, file_path))
    warnings.extend(check_service_http_concepts(content, file_path))
    warnings.extend(check_domain_framework_imports(content, file_path))
    warnings.extend(check_screen_direct_api_import(content, file_path, ext))

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
