#!/usr/bin/env python3
"""UserPromptSubmit hook: Detects vague requirements and suggests clarification.
Fires before Claude processes the user's prompt."""

import json
import sys
import re


def main():
    data = json.load(sys.stdin)
    prompt = data.get("prompt", "")

    if not prompt or len(prompt) < 10:
        sys.exit(0)

    # Vague requirement indicators
    vague_patterns = [
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

    vague_matches = []
    for pattern, reason in vague_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            vague_matches.append(reason)

    if vague_matches:
        reasons = "; ".join(vague_matches)
        # Don't block, just add context for Claude
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": (
                            f"[HOOK NOTE] This request may be vague ({reasons}). "
                            "Consider using the requirements-consultant agent to clarify "
                            "before implementation: invoke it with the Task tool using "
                            "subagent_type 'general-purpose' or suggest the user try "
                            "'I need help clarifying requirements for...' to trigger the agent."
                        ),
                    }
                }
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
