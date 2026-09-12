#!/usr/bin/env python3
"""
SubagentStart hook: give every subagent the house stack, and team context only when the subagent
is a member of THIS session's team.

Contract (https://code.claude.com/docs/en/hooks, "SubagentStart"): "SubagentStart hooks receive
`agent_id` with the unique identifier for the subagent and `agent_type` with the agent name that
the matcher filters on". "SubagentStart hooks can't block subagent creation, but they can inject
context into the subagent" through `hookSpecificOutput.additionalContext`, a "String added to the
subagent's context at the start of its conversation, before its first prompt". Plain stdout is not
a channel for this event: it goes to the debug log, which is where the old `print(output)` sent
everything.

The team block used to come from the most recently modified ~/.claude/teams/*/config.json on the
whole machine, so an Explore subagent in one project was told it belonged to another client's team,
along with that team's absolute paths. It is now read only from this session's team (`session-`
plus the first eight characters of session_id, per the agent-teams docs), and only when agent_id
is one of that team's members. The agent-teams docs describe "a `members` array with each member's
name and agent ID" without naming the JSON keys; the live config spells them `name` and `agentId`.
No paths are injected.

The text states facts rather than orders: the docs warn that out-of-band imperatives can trip the
model's prompt-injection defenses. Always exits 0.
"""
import json
import os
import re
import sys

STACK_CONTEXT = (
    "House stack (sdh plugin). Backend: Rails in API-only mode with Pundit authorization, Panko "
    "serializers, Phlex views and Sidekiq; Python services on FastAPI (the default) or Django + DRF, "
    "with SQLAlchemy 2.0 + Alembic, pydantic v2, Celery and uv/ruff/mypy/pytest. AI/ML: PyTorch, "
    "scikit-learn, MLflow tracking, pgvector embeddings on PostgreSQL, the anthropic SDK. Data: "
    "PostgreSQL + PostGIS, Redis. Mobile: React Native, with Zustand for client state and TanStack "
    "Query for server state. Web: a React + Vite SPA and Next.js App Router, both built on shadcn/ui "
    "(Base UI primitives for new packages; existing Radix packages stay on Radix), Tailwind CSS with "
    "the house design tokens, CASL permission gates, react-hook-form + zod, and vitest + Testing "
    "Library + msw. Charts, one library per stack: Next.js uses Recharts through the shadcn/ui chart "
    "component; the Vite SPA uses Chart.js through react-chartjs-2; Rails Phlex views use Chart.js "
    "through a house Stimulus controller. Navigation is drill-down on every platform, existing "
    "products included: the global sidebar (the bottom tab bar on mobile) lists areas only; each "
    "area's section nav lives in that area's own layout; breadcrumbs come from the API's ancestors; "
    "list filters and sort live in the URL; a command palette, where a product has one, is fed by "
    "the permission-filtered nav and the search endpoint and is never the only way to reach a page. "
    "APIs are drill-down ready: collection routes nest one level under one parent, member routes are "
    "flat by id, detail payloads carry permission-filtered ancestors, counts are computed inside the "
    "caller's scope, and every level is authorized. Real-time: Centrifugo. "
    "Infrastructure: Terraform on AWS (primary) and GCP, Vercel for Next.js, Docker Compose for local "
    "development. Established community libraries (gems, npm packages, PyPI packages) are preferred "
    "over custom code, and recommendations fit the house stack for the layer being worked on."
)
# `agentId` is the key the live team config carries; `agent_id` is kept for a snake_case rename.
MEMBER_ID_KEYS = ("agentId", "agent_id")


def session_team(data):
    """(team name, this member, all members) when agent_id belongs to this session's team, else None."""
    session, agent_id = str(data.get("session_id") or ""), str(data.get("agent_id") or "")
    team = f"session-{session[:8]}"
    if not agent_id or not re.fullmatch(r"session-[A-Za-z0-9_-]{1,8}", team):
        return None
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    try:
        with open(os.path.join(base, "teams", team, "config.json"), encoding="utf-8") as handle:
            members = json.load(handle).get("members", [])
    except (OSError, ValueError, AttributeError):
        return None
    members = [m for m in members if isinstance(m, dict)] if isinstance(members, list) else []
    me = next((m for m in members if agent_id in (str(m.get(key) or "") for key in MEMBER_ID_KEYS)), None)
    return (team, me, members) if me else None


def team_context(found):
    team, me, members = found
    peers = [str(m.get("name"))[:64] for m in members if m is not me and m.get("name")]
    return (
        f"This subagent is teammate {str(me.get('name') or 'unnamed')[:64]} on agent team {team}. "
        f"Other members: {', '.join(peers) or 'none yet'}. Each teammate owns a distinct set of "
        "files, and the shared task list records which teammate holds which task."
    )


def main():
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        data = {}
    data = data if isinstance(data, dict) else {}
    context = STACK_CONTEXT
    found = session_team(data)
    if found:
        context += "\n\n" + team_context(found)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart",
                                             "additionalContext": context}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
