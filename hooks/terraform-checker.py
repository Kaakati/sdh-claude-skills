#!/usr/bin/env python3
"""
PostToolUse hook: Terraform convention checker.

Validates .tf files for: hardcoded secrets, resource naming (snake_case),
required tags, backend config in environment dirs, provider version constraints.
Outputs warnings only — never blocks.

One Terraform module is one DIRECTORY, not one file: the house layout
(terraform/references/repository-layout.md) puts `default_tags` in providers.tf and the backend
in backend.tf, beside the main.tf that holds resources. So the tags and backend checks read the
sibling *.tf files before warning — a check that sees only the edited file flags every resource
file in a correctly configured root module.
"""
import os
import re

import _hooklib as hooklib


# Only check .tf files (not .tfvars — may contain dummy dev values)
TF_EXTENSION = ".tf"
SKILL = "the `std-terraform-conventions` skill"

# AWS access key pattern (AKIA...)
AWS_KEY_PATTERN = re.compile(r"(?:AKIA[0-9A-Z]{16})")

# Common hardcoded secret patterns in HCL. `${` is a reference too: `"${var.db_password}"` is
# the interpolation spelling of `var.db_password`, not a literal.
_NOT_A_REFERENCE = r'(?!\$\{|var\.|local\.|data\.|module\.)'
SECRET_PATTERNS = [
    (re.compile(r'password\s*=\s*"' + _NOT_A_REFERENCE + r'[^"]{4,}"', re.IGNORECASE), "hardcoded password"),
    (re.compile(r'secret\s*=\s*"' + _NOT_A_REFERENCE + r'[^"]{4,}"', re.IGNORECASE), "hardcoded secret"),
    (re.compile(r'api_key\s*=\s*"' + _NOT_A_REFERENCE + r'[^"]{4,}"', re.IGNORECASE), "hardcoded API key"),
    (re.compile(r'token\s*=\s*"' + _NOT_A_REFERENCE + r'[^"]{4,}"', re.IGNORECASE), "hardcoded token"),
    (AWS_KEY_PATTERN, "AWS access key"),
]

# Resource block pattern: resource "type" "name" {
# `\w` is [A-Za-z0-9_] and CANNOT match a hyphen — so a kebab-named resource did not merely
# fail the snake_case test, it never matched this pattern at all. Two consequences, and the
# second is worse: (1) the naming check could never see the one thing it exists to catch —
# line ~81's remedy calls .replace('-', '_'), dead code for input it could not receive; and
# (2) check_required_tags derives its resource list from this same pattern, so a .tf file
# whose resources are all kebab-named yielded an EMPTY list -> has_taggable_resources=False
# -> the entire tags check silently skipped. A file violating naming AND tags emitted
# nothing at all.
RESOURCE_BLOCK_PATTERN = re.compile(r'resource\s+"([\w-]+)"\s+"([\w-]+)"')

# Provider version constraints. `\b` so `required_version = ">= 1.6"` — the TERRAFORM pin — no
# longer counts as a provider pin: a versions.tf with required_version and an unpinned provider
# used to pass.
VERSION_ARG = re.compile(r'\bversion\s*=\s*"[^"]*"')
REQUIRED_PROVIDERS_BLOCK = re.compile(r'\brequired_providers\s*\{')
PROVIDER_ENTRY = re.compile(r'^\s*([\w-]+)\s*=\s*(\{|")', re.MULTILINE)
PROVIDER_BLOCK = re.compile(r'^\s*provider\s+"[\w-]+"\s*\{', re.MULTILINE)

# Tags: a literal map, or the merge()/local/var the std-infrastructure module examples write.
TAGS_PATTERN = re.compile(r'\btags\s*=\s*(?:\{|merge\s*\(|(?:local|var|module|data)\.)')
DEFAULT_TAGS_PATTERN = re.compile(r'default_tags\s*\{', re.MULTILINE)

# Required tags
REQUIRED_TAGS = ["project", "environment", "team", "managed-by"]

# AWS only: `default_tags` is an AWS-provider feature and resource-required-tags.md scopes the
# rule to "every AWS resource". GCP resources take `labels`, and the house GCP examples
# (std-infrastructure/references/gcp-secondary-cloud.md) are IAM resources that take neither.
TAGGABLE_PREFIXES = ("aws_",)

# Backend config pattern
BACKEND_PATTERN = re.compile(r'backend\s+"(s3|gcs|remote)"', re.MULTILINE)

# Environment directory pattern
ENV_DIR_PATTERN = re.compile(r'terraform[/\\]environments[/\\](dev|staging|production)[/\\]')

# Variable block pattern (for checking type constraints)
VARIABLE_BLOCK_PATTERN = re.compile(r'variable\s+"(\w+)"\s*\{')

# snake_case validation
SNAKE_CASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')

# Bounds on the disk reads the directory-level checks make.
MAX_SIBLING_FILES = 200
MAX_CALLER_DIRS = 400
CALLER_SEARCH_DEPTH = 3
SKIP_DIRS = (".terraform", ".git", "modules", "node_modules")


def check_hardcoded_secrets(content, display_path):
    """Check for hardcoded secrets in .tf files."""
    warnings = []
    for pattern, description in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            warnings.append(
                f"WARNING: Terraform — {description} detected in {display_path}:{line_num}. "
                f"Use variables with sensitive = true or AWS Secrets Manager — see {SKILL}."
            )
    return warnings


def check_resource_naming(content, display_path):
    """Check that resource logical names use snake_case."""
    warnings = []
    for match in RESOURCE_BLOCK_PATTERN.finditer(content):
        resource_type = match.group(1)
        resource_name = match.group(2)
        if not SNAKE_CASE_PATTERN.match(resource_name):
            line_num = content[:match.start()].count("\n") + 1
            warnings.append(
                f"WARNING: Terraform — Resource name '{resource_name}' in {display_path}:{line_num} "
                f"is not snake_case. Use: {resource_type}.{resource_name.lower().replace('-', '_')} "
                f"per {SKILL}."
            )
    return warnings


def module_text(file_path, content):
    """This file's content plus every other *.tf beside it — the module the file belongs to."""
    here = os.path.normcase(os.path.abspath(file_path))
    directory = os.path.dirname(here)
    try:
        names = sorted(n for n in os.listdir(directory) if n.endswith(TF_EXTENSION))
    except OSError:
        return content
    others = [hooklib.read_file(os.path.join(directory, n)) for n in names[:MAX_SIBLING_FILES]
              if os.path.normcase(os.path.join(directory, n)) != here]
    return "\n".join([content] + others)


def _module_location(file_path):
    """(caller search root, 'modules/<name>') when the file sits in a child module, else None."""
    current = os.path.dirname(os.path.abspath(file_path))
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            return None
        if os.path.basename(parent) == "modules":
            return os.path.dirname(parent), "modules/" + os.path.basename(current)
        current = parent


def _tf_dirs(base):
    """(directory, *.tf names) under `base`, depth-bounded, skipping modules and caches."""
    base_depth = os.path.abspath(base).rstrip(os.sep).count(os.sep)
    found, visited = [], 0
    for root, dirs, files in os.walk(base):
        visited += 1
        depth = root.rstrip(os.sep).count(os.sep) - base_depth
        dirs[:] = [] if depth >= CALLER_SEARCH_DEPTH else [d for d in dirs if d not in SKIP_DIRS]
        names = [f for f in files if f.endswith(TF_EXTENSION)]
        if names:
            found.append((root, names))
        if visited >= MAX_CALLER_DIRS:
            break
    return found


def _callers_set_default_tags(file_path):
    """True when a root module that sources this child module declares provider `default_tags`.

    A child module has no provider block by design (repository-layout.md: "no backend block and
    no provider block"), and its resources inherit the CALLER's default_tags — the layout that
    doc prescribes, with "no map threaded through module variables". So the evidence lives in the
    root module that calls it, not beside the file."""
    located = _module_location(file_path)
    if not located:
        return False
    base, module_ref = located
    for root, names in _tf_dirs(base):
        text = "\n".join(hooklib.read_file(os.path.join(root, n)) for n in names)
        if module_ref in hooklib.normalize(text) and DEFAULT_TAGS_PATTERN.search(text):
            return True
    return False


def check_required_tags(content, module, display_path, file_path):
    """Taggable resources need tags: explicit `tags`, provider `default_tags` anywhere in this
    module directory, or — for a child module — default_tags in a root module that calls it."""
    resources = RESOURCE_BLOCK_PATTERN.findall(content)
    if not any(rtype.startswith(TAGGABLE_PREFIXES) for rtype, _ in resources):
        return []
    if TAGS_PATTERN.search(content) or DEFAULT_TAGS_PATTERN.search(module):
        return []
    if not PROVIDER_BLOCK.search(module) and _callers_set_default_tags(file_path):
        return []
    return [
        f"WARNING: Terraform — {display_path} has taggable resources without tags. "
        f"Add default_tags in provider or tags on each resource: {', '.join(REQUIRED_TAGS)} "
        f"per {SKILL}."
    ]


def check_backend_config(normalized_path, module, display_path):
    """Environment root modules need a remote backend — in backend.tf or versions.tf.

    The house layout keeps versions.tf to pins only and the backend in backend.tf, so the
    question is whether the DIRECTORY configures one, not whether the edited file does."""
    if not ENV_DIR_PATTERN.search(normalized_path):
        return []
    if os.path.basename(normalized_path) not in ("versions.tf", "backend.tf"):
        return []
    if BACKEND_PATTERN.search(module):
        return []
    return [
        f"WARNING: Terraform — {display_path} in environment directory "
        f"should configure a remote backend (S3 + DynamoDB) per {SKILL}."
    ]


def _block_body(text, open_brace):
    """Text inside the `{` at `open_brace`, through its matching `}`."""
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] in "{}":
            depth += 1 if text[i] == "{" else -1
            if depth == 0:
                return text[open_brace + 1:i]
    return text[open_brace + 1:]


def _unpinned_providers(block):
    """Names in a required_providers body whose entry sets no `version`."""
    unpinned = []
    for m in PROVIDER_ENTRY.finditer(block):
        if m.group(2) == '"':
            continue  # `source = "..."`, `version = "..."`, or legacy `aws = "~> 5.0"`
        if not VERSION_ARG.search(_block_body(block, m.end() - 1)):
            unpinned.append(m.group(1))
    return unpinned


def check_provider_version(content, display_path):
    """Every provider in required_providers carries a version constraint."""
    warnings = []
    for match in REQUIRED_PROVIDERS_BLOCK.finditer(content):
        unpinned = _unpinned_providers(_block_body(content, match.end() - 1))
        if unpinned:
            warnings.append(
                f"WARNING: Terraform — {display_path} has required_providers without "
                f"version constraints ({', '.join(unpinned)}). Pin with: version = \"~> X.0\" "
                f"per {SKILL}."
            )
    return warnings


def get_display_path(normalized_path):
    """Extract a short display path for warning messages."""
    if "terraform/" in normalized_path:
        return normalized_path.split("terraform/", 1)[1]
    return os.path.basename(normalized_path)


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext != TF_EXTENSION:
        return []

    normalized = hooklib.normalize(file_path)
    display_path = get_display_path(normalized)

    content = hooklib.read_file(file_path)
    if not content:
        return []

    module = module_text(file_path, content)
    warnings = []
    warnings.extend(check_hardcoded_secrets(content, display_path))
    warnings.extend(check_resource_naming(content, display_path))
    warnings.extend(check_required_tags(content, module, display_path, file_path))
    warnings.extend(check_backend_config(normalized, module, display_path))
    warnings.extend(check_provider_version(content, display_path))
    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
