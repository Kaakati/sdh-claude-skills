#!/usr/bin/env python3
"""UserPromptSubmit hook: flag an underspecified request and offer requirements clarification.

Contract (https://code.claude.com/docs/en/hooks, "UserPromptSubmit"): `additionalContext` is
"added to Claude's context alongside the submitted prompt" and produces no visible transcript
entry. The text states facts and a conditional next step, because "text framed as out-of-band
system commands can trigger Claude's prompt-injection defenses".

Two corrections:
  1. PRECISION. The generic-request pattern has an unbounded `.*`, so "Create a Terraform module
     for the RDS instance with multi-AZ, 7-day backups" fired and demanded clarification of a fully
     specified request. A prompt carrying a concrete signal (a path or file name, backticks, a digit,
     a code identifier, a comparison operator, a JSX tag, a house stack name, or 12+ words) is not
     the vague request the generic, quality-attribute and one-word patterns exist to catch.
  2. DEGRADATION. AskUserQuestion is absent in headless -p runs and denied in dontAsk mode, yet the
     old text said "you MUST call AskUserQuestion. Do NOT skip this step". The suggestion is now
     conditional with a fallback, and the skill carries its plugin namespace.
"""

import json
import re
import sys

# (pattern, reason, exempt when the prompt carries a specificity signal)
VAGUE_PATTERNS = [
    (
        r"\b(we need|we want|we should|can you make|build me|create a)\b.*"
        r"(?:thing|stuff|something|feature(?!\s+flags?\b)|system|module)\b",
        "Generic feature request without specifics",
        True,
    ),
    (
        r"\b(make it|should be)\s+(better|faster|nicer|cleaner|good|modern|scalable)\b",
        "Quality attribute without measurable criteria",
        True,
    ),
    (
        r"\b(like|similar to|something like)\s+\w+\s*(app|website|platform)\b",
        "Reference to another product without specific requirements",
        False,
    ),
    (
        r"^(add|implement|create|build)\s+\w{1,20}\s*$",
        "One-word feature request",
        True,
    ),
]

# Case-sensitive on purpose: `[a-z]+[A-Z]` is how camelCase is told from prose.
SPECIFICITY_SIGNALS = [
    r"`",
    r"\w/\w",
    r"\b\w+\.(?:rb|py|tsx?|jsx?|tf|ya?ml|json|md|sql|css|erb|html)\b",
    r"\d",
    r"\b[a-z]+_[a-z0-9_]+\b",
    r"\b[a-z]+[A-Z][A-Za-z0-9]*\b",
    r"\b[A-Z][a-z0-9]+[A-Z][A-Za-z0-9]*\b",
    r"\b[a-z_]{2,}\.[a-z_]{2,}\b",
    r"==|!=|>=|<=|=>",
    r"<[A-Z]\w*",
    r"(?i)\b(?:rails|django|drf|fastapi|next\.js|nextjs|vite|react native|expo|terraform|casl|"
    r"shadcn|phlex|pundit|panko|sidekiq|celery|alembic|sqlalchemy|pydantic|postgis|pgvector|"
    r"recharts|zustand|tanstack|centrifugo|tailwind|mlflow|zod|rds|ecs|s3|vercel)\b",
]
SPECIFIC_WORD_COUNT = 12

# Skip detection when the user is clearly asking for help or using a skill
SKIP_PATTERNS = [
    r"^/",                           # Slash commands
    r"\brequirements?\b.*\bclarif",  # Already asking for requirements help
    r"\bhelp me (clarify|scope|define|understand)\b",
    r"\buser stor(y|ies)\b",
    r"\bacceptance criteria\b",
]


def is_specific(prompt):
    if len(prompt.split()) >= SPECIFIC_WORD_COUNT:
        return True
    return any(re.search(signal, prompt) for signal in SPECIFICITY_SIGNALS)


def vague_reasons(prompt):
    specific = is_specific(prompt)
    return [
        reason for pattern, reason, exemptible in VAGUE_PATTERNS
        if re.search(pattern, prompt, re.IGNORECASE) and not (exemptible and specific)
    ]


def advice(reasons):
    return (
        f"The submitted request may be underspecified ({reasons}). This repository's workflow "
        "offers the user a choice before implementation starts: clarify the requirements first "
        "with the sdh:requirements-consultant skill (the Skill tool, with the original request as "
        "args), or proceed on stated assumptions. When the AskUserQuestion tool is available, the "
        "choice fits it as two options: \"Clarify requirements first (Recommended)\" and \"Proceed "
        "as-is\". When AskUserQuestion is unavailable or denied (headless -p runs, dontAsk mode, "
        "subagents), the assumptions are stated explicitly and the work proceeds."
    )


def main():
    data = json.load(sys.stdin)
    prompt = data.get("prompt", "") if isinstance(data, dict) else ""
    if not isinstance(prompt, str) or len(prompt) < 10:
        sys.exit(0)
    if any(re.search(skip, prompt, re.IGNORECASE) for skip in SKIP_PATTERNS):
        sys.exit(0)
    reasons = vague_reasons(prompt)
    if reasons:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": advice("; ".join(reasons)),
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    # Fail OPEN: an advisory hook's crash must never cost the user their prompt. Not silently,
    # and never as a raw traceback: one actionable line (plain stdout is context on this event).
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"HOOK ERROR: vague-request-detector failed to run - "
            f"{type(exc).__name__}: {exc}. Your prompt was not affected."
        )
        sys.exit(0)
