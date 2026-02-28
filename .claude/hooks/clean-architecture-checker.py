#!/usr/bin/env python3
"""
PostToolUse hook: Clean Architecture layer boundary checker.

Checks source files for layer boundary violations per clean-architecture.md.
Exits silently for non-source files.
"""
import json
import os
import re
import sys


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")


def normalize(path):
    return path.replace("\\", "/")


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def check_rails_model_imports(content, normalized):
    """Models should not import from controllers or serializers."""
    if "backend/app/models/" not in normalized:
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


def check_service_http_concepts(content, normalized):
    """Services should not return HTTP status codes or use render."""
    if "backend/app/services/" not in normalized:
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


def check_domain_framework_imports(content, normalized):
    """Domain types should not import framework modules."""
    domain_prefixes = ("mobile/src/domain/", "web/src/domain/", "next/src/domain/")
    if not any(p in normalized for p in domain_prefixes):
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


def check_screen_direct_api_import(content, normalized):
    """Screens/pages should not import API clients directly."""
    screen_prefixes = ("mobile/src/screens/", "web/src/pages/", "next/app/")
    if not any(p in normalized for p in screen_prefixes):
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


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        sys.exit(0)

    content = read_file(file_path)
    if not content:
        sys.exit(0)

    normalized = normalize(file_path)
    warnings = []
    warnings.extend(check_rails_model_imports(content, normalized))
    warnings.extend(check_service_http_concepts(content, normalized))
    warnings.extend(check_domain_framework_imports(content, normalized))
    warnings.extend(check_screen_direct_api_import(content, normalized))

    for w in warnings:
        print(w)

    sys.exit(0)


if __name__ == "__main__":
    main()
