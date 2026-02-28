#!/usr/bin/env python3
"""
PostToolUse hook: API design checker for controller and API route files.

Replaces the agent-based API design hook with a deterministic command hook.
Checks files under backend/app/controllers/, mobile/src/api/, web/src/api/, next/src/actions/
for common API design violations per api-design.md.
Exits silently (exit 0, no output) for non-matching files.
"""
import json
import os
import re
import sys


# Only check files under these directory prefixes (forward-slash normalized)
ALLOWED_PREFIXES = (
    "backend/app/controllers/",
    "mobile/src/api/",
    "web/src/api/",
    "next/src/actions/",
)

# Common verbs that should not appear in URL route paths
ROUTE_VERBS = (
    "get", "create", "update", "delete", "remove", "fetch",
    "add", "edit", "list", "find", "search", "post", "put",
)


def normalize_path(path):
    """Normalize path separators to forward slashes for consistent matching."""
    return path.replace("\\", "/")


def read_file(path):
    """Read file content, return empty string on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return ""


def check_verbs_in_routes(content):
    """Check for verbs in URL route path definitions."""
    warnings = []
    # Match common route definition patterns:
    # Rails: get '/getUser', resources :createOrders
    # JS/TS: '/api/getUser', '/api/createOrder', router.get('/deleteItem')
    route_pattern = re.compile(
        r"""['"](/[a-zA-Z_/]*\b("""
        + "|".join(ROUTE_VERBS)
        + r""")[A-Z]\w*)\b""",
        re.IGNORECASE,
    )
    for match in route_pattern.finditer(content):
        path_segment = match.group(1)
        verb = match.group(2)
        warnings.append(
            f"WARNING: Verb '{verb}' in URL path '{path_segment}'. "
            f"Use plural nouns for resources per api-design.md."
        )
    return warnings


def check_unwrapped_array_response(content):
    """Check for JSON responses returning arrays not wrapped in a data key."""
    warnings = []
    # Rails: render json: [...] or render json: SomeModel.all
    # Look for render json: followed by array literal
    pattern_rails = re.compile(r"render\s+json:\s*\[")
    if pattern_rails.search(content):
        warnings.append(
            "WARNING: Collection response not wrapped in data key "
            "per api-design.md. Use { data: [...] } format."
        )

    # JS/TS: res.json([...]) or return Response.json([...])
    pattern_js = re.compile(r"\.(json|send)\s*\(\s*\[")
    if pattern_js.search(content):
        warnings.append(
            "WARNING: Collection response not wrapped in data key "
            "per api-design.md. Use { data: [...] } format."
        )

    return warnings


def check_error_response_format(content):
    """Check error responses for missing code or request_id fields."""
    warnings = []
    # Rails: render json: { error: ... } without code or request_id
    error_render = re.compile(
        r"render\s+json:\s*\{[^}]*\berror\b[^}]*\}", re.DOTALL
    )
    for match in error_render.finditer(content):
        block = match.group(0)
        if "code" not in block or "request_id" not in block:
            missing = []
            if "code" not in block:
                missing.append("code")
            if "request_id" not in block:
                missing.append("request_id")
            warnings.append(
                f"WARNING: Error response missing {'/'.join(missing)} "
                f"per api-design.md."
            )

    return warnings


def check_post_returns_200(content):
    """Check for POST actions returning 200 instead of 201."""
    warnings = []
    # Rails: in a create action, render ... status: :ok or status: 200
    # Heuristic: look for def create ... render ... status: :ok
    create_pattern = re.compile(
        r"def\s+create\b.*?(?=\bdef\s|\Z)", re.DOTALL
    )
    for match in create_pattern.finditer(content):
        block = match.group(0)
        if re.search(r"status:\s*(:ok|200)\b", block):
            warnings.append(
                "WARNING: POST create action returns 200 instead of 201 "
                "Created per api-design.md."
            )

    # JS/TS: router.post with res.status(200) or without explicit status
    post_pattern = re.compile(
        r"\.(post)\s*\([^)]*\)\s*.*?res\.status\(200\)", re.DOTALL
    )
    if post_pattern.search(content):
        warnings.append(
            "WARNING: POST handler returns 200 instead of 201 "
            "Created per api-design.md."
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

    # Check directory prefix
    normalized = normalize_path(file_path)
    if not any(prefix in normalized for prefix in ALLOWED_PREFIXES):
        sys.exit(0)

    # Read and analyze file
    content = read_file(file_path)
    if not content:
        sys.exit(0)

    warnings = []
    warnings.extend(check_verbs_in_routes(content))
    warnings.extend(check_unwrapped_array_response(content))
    warnings.extend(check_error_response_format(content))
    warnings.extend(check_post_returns_200(content))

    if warnings:
        seen = set()
        for w in warnings:
            if w not in seen:
                seen.add(w)
                print(w)

    sys.exit(0)


if __name__ == "__main__":
    main()
