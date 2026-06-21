#!/usr/bin/env python3
"""
PostToolUse hook: Terraform convention checker.

Validates .tf files for: hardcoded secrets, resource naming (snake_case),
required tags, backend config in environment dirs, provider version constraints.
Outputs warnings only — never blocks.
"""
import os
import re

import _hooklib as hooklib


# Only check .tf files (not .tfvars — may contain dummy dev values)
TF_EXTENSION = ".tf"

# AWS access key pattern (AKIA...)
AWS_KEY_PATTERN = re.compile(r"(?:AKIA[0-9A-Z]{16})")

# Common hardcoded secret patterns in HCL
SECRET_PATTERNS = [
    (re.compile(r'password\s*=\s*"(?!var\.|local\.|data\.|module\.)[^"]{4,}"', re.IGNORECASE), "hardcoded password"),
    (re.compile(r'secret\s*=\s*"(?!var\.|local\.|data\.|module\.)[^"]{4,}"', re.IGNORECASE), "hardcoded secret"),
    (re.compile(r'api_key\s*=\s*"(?!var\.|local\.|data\.|module\.)[^"]{4,}"', re.IGNORECASE), "hardcoded API key"),
    (re.compile(r'token\s*=\s*"(?!var\.|local\.|data\.|module\.)[^"]{4,}"', re.IGNORECASE), "hardcoded token"),
    (AWS_KEY_PATTERN, "AWS access key"),
]

# Resource block pattern: resource "type" "name" {
RESOURCE_BLOCK_PATTERN = re.compile(r'resource\s+"(\w+)"\s+"(\w+)"')

# Provider version constraint pattern
PROVIDER_VERSION_PATTERN = re.compile(r'version\s*=\s*"([^"]*)"')
REQUIRED_PROVIDERS_BLOCK = re.compile(r'required_providers\s*\{', re.MULTILINE)

# Tags block pattern
TAGS_PATTERN = re.compile(r'tags\s*=\s*\{', re.MULTILINE)
DEFAULT_TAGS_PATTERN = re.compile(r'default_tags\s*\{', re.MULTILINE)

# Required tags
REQUIRED_TAGS = ["project", "environment", "team", "managed-by"]

# Backend config pattern
BACKEND_PATTERN = re.compile(r'backend\s+"(s3|gcs|remote)"', re.MULTILINE)

# Environment directory pattern
ENV_DIR_PATTERN = re.compile(r'terraform[/\\]environments[/\\](dev|staging|production)[/\\]')

# Variable block pattern (for checking type constraints)
VARIABLE_BLOCK_PATTERN = re.compile(r'variable\s+"(\w+)"\s*\{')

# snake_case validation
SNAKE_CASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')


def check_hardcoded_secrets(content, display_path):
    """Check for hardcoded secrets in .tf files."""
    warnings = []
    for pattern, description in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            warnings.append(
                f"WARNING: Terraform — {description} detected in {display_path}:{line_num}. "
                f"Use variables with sensitive = true or AWS Secrets Manager."
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
                f"is not snake_case. Use: {resource_type}.{resource_name.lower().replace('-', '_')}"
            )
    return warnings


def check_required_tags(content, display_path):
    """Check that resource blocks include required tags or default_tags is set."""
    warnings = []

    # If default_tags is present in provider block, tags are covered
    if DEFAULT_TAGS_PATTERN.search(content):
        return warnings

    # Check if any resource blocks exist that should have tags
    resources = RESOURCE_BLOCK_PATTERN.findall(content)
    taggable_prefixes = ("aws_", "google_", "azurerm_")

    has_taggable_resources = any(
        rtype.startswith(taggable_prefixes) for rtype, _ in resources
    )

    if has_taggable_resources and not TAGS_PATTERN.search(content):
        warnings.append(
            f"WARNING: Terraform — {display_path} has taggable resources without tags. "
            f"Add default_tags in provider or tags on each resource: {', '.join(REQUIRED_TAGS)}"
        )

    return warnings


def check_backend_config(normalized_path, content, display_path):
    """Check that environment root modules have backend configuration."""
    warnings = []
    env_match = ENV_DIR_PATTERN.search(normalized_path)

    if env_match:
        # This is an environment root module — check for backend config
        basename = os.path.basename(normalized_path)
        if basename in ("main.tf", "versions.tf", "backend.tf"):
            # Only warn on these files where backend should be defined
            pass
        # Check across the directory — but we only see this file
        # So check if this file is versions.tf or backend.tf and has no backend
        if basename in ("versions.tf", "backend.tf"):
            if not BACKEND_PATTERN.search(content):
                warnings.append(
                    f"WARNING: Terraform — {display_path} in environment directory "
                    f"should configure a remote backend (S3 + DynamoDB)."
                )

    return warnings


def check_provider_version(content, display_path):
    """Check that providers have version constraints."""
    warnings = []

    if REQUIRED_PROVIDERS_BLOCK.search(content):
        # Check if version constraints exist
        if not PROVIDER_VERSION_PATTERN.search(content):
            warnings.append(
                f"WARNING: Terraform — {display_path} has required_providers without "
                f"version constraints. Pin with: version = \"~> X.0\""
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

    warnings = []

    warnings.extend(check_hardcoded_secrets(content, display_path))
    warnings.extend(check_resource_naming(content, display_path))
    warnings.extend(check_required_tags(content, display_path))
    warnings.extend(check_backend_config(normalized, content, display_path))
    warnings.extend(check_provider_version(content, display_path))

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
