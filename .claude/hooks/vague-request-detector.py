#!/usr/bin/env python3
"""UserPromptSubmit hook: Detects vague requirements and suggests clarification.

When a vague request is detected, instructs Claude to ask the user whether they
want to clarify requirements via the /requirements-consultant skill before
proceeding with implementation."""

import json
import sys
import re


# Patterns that indicate vague or underspecified requirements
VAGUE_PATTERNS = [
    (
        r"\b(we need|we want|we should|can you make|build me|create a)\b.*(?:thing|stuff|something|feature|system|module)\b",
        "Generic feature request without specifics",
    ),
    (
        r"\b(make it|should be)\s+(better|faster|nicer|cleaner|good|modern|scalable)\b",
        "Quality attribute without measurable criteria",
    ),
    (
        r"\b(like|similar to|something like)\s+\w+\s*(app|website|platform)\b",
        "Reference to another product without specific requirements",
    ),
    (
        r"^(add|implement|create|build)\s+\w{1,20}\s*$",
        "One-word feature request",
    ),
]

# Skip detection when the user is clearly asking for help or using a skill
SKIP_PATTERNS = [
    r"^/",                           # Slash commands
    r"\brequirements?\b.*\bclarif",  # Already asking for requirements help
    r"\bhelp me (clarify|scope|define|understand)\b",
    r"\buser stor(y|ies)\b",
    r"\bacceptance criteria\b",
]


def main():
    data = json.load(sys.stdin)
    prompt = data.get("prompt", "")

    if not prompt or len(prompt) < 10:
        sys.exit(0)

    # Don't trigger on slash commands or explicit requirements work
    for skip in SKIP_PATTERNS:
        if re.search(skip, prompt, re.IGNORECASE):
            sys.exit(0)

    vague_matches = []
    for pattern, reason in VAGUE_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            vague_matches.append(reason)

    if vague_matches:
        reasons = "; ".join(vague_matches)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": (
                            "<user-prompt-submit-hook>\n"
                            "VAGUE REQUEST DETECTED — INTERACTIVE CLARIFICATION REQUIRED\n\n"
                            f"Issues found: {reasons}\n\n"
                            "You MUST take the following action BEFORE doing any implementation work:\n\n"
                            "1. Use the AskUserQuestion tool to ask the user:\n"
                            '   Question: "Your request may benefit from requirements clarification. '
                            'Would you like to refine the requirements before I start building?"\n'
                            "   Options:\n"
                            '   - "Clarify requirements first (Recommended)" — description: '
                            '"Route to the requirements-consultant agent to scope the work, '
                            'define user stories, and identify hidden requirements before coding."\n'
                            '   - "Proceed as-is" — description: '
                            '"Skip clarification and start implementation with the current description. '
                            'I will make reasonable assumptions."\n\n'
                            "2. If the user chooses to clarify requirements, invoke the Skill tool "
                            'with skill: "requirements-consultant" and pass the user\'s original '
                            "request as the args parameter.\n\n"
                            "3. If the user chooses to proceed as-is, continue normally but "
                            "explicitly state any assumptions you are making.\n\n"
                            "Do NOT skip this step. Do NOT just add a note — you must actually "
                            "call AskUserQuestion.\n"
                            "</user-prompt-submit-hook>"
                        ),
                    }
                }
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
