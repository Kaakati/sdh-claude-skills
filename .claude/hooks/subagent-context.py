#!/usr/bin/env python3
"""
SubagentStart hook: Inject tech stack and team context.

Prints the project tech stack summary so subagents are aware of the
development environment. When spawning within an agent team, also
injects team context (team name, teammates, task list location).

Always exits 0.
"""
import glob
import json
import os
import sys


CONTEXT = (
    "You are working in a Software Development House with this tech stack: "
    "Rails (backend), Panko Serializer, PostgreSQL + PostGIS (geospatial database), "
    "React Native (mobile), ReactJS + Vite (web SPA), Next.js App Router (web SSR/SSG), "
    "Tailwind CSS (web styling), Framer Motion (web animations), ApexCharts (web charts), "
    "Zustand (client state), TanStack Query (server state), Centrifugal/Centrifugo "
    "(real-time WebSocket), Redis (cache + Sidekiq queues), AWS + GCP (cloud), "
    "Vercel (Next.js deployment), Terraform (IaC), Docker Compose (local dev). "
    "Web testing uses Vitest + React Testing Library. "
    "ALWAYS prefer established community libraries (gems, npm packages) over custom "
    "implementations. Frame all recommendations within this stack."
)

TEAM_CONTEXT_TEMPLATE = (
    "\n\nYou are part of an agent team. "
    "Team: {team_name}. "
    "Team config: {config_path}. "
    "Task list: {task_path}. "
    "Teammates: {teammates}. "
    "IMPORTANT: Coordinate via task list and messages. "
    "Each teammate owns a distinct set of files — never edit files owned by another teammate. "
    "Check TaskList after completing each task to find your next assignment."
)


def find_team_context():
    """Discover active team context from ~/.claude/teams/ directory."""
    home = os.path.expanduser("~")
    teams_dir = os.path.join(home, ".claude", "teams")

    if not os.path.isdir(teams_dir):
        return None

    # Find the most recently modified team config
    team_dirs = []
    try:
        for entry in os.listdir(teams_dir):
            config_path = os.path.join(teams_dir, entry, "config.json")
            if os.path.isfile(config_path):
                mtime = os.path.getmtime(config_path)
                team_dirs.append((mtime, entry, config_path))
    except OSError:
        return None

    if not team_dirs:
        return None

    # Use the most recently modified team
    team_dirs.sort(reverse=True)
    _, team_name, config_path = team_dirs[0]

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    members = config.get("members", [])
    teammate_names = [m.get("name", "unknown") for m in members]

    task_path = os.path.join(home, ".claude", "tasks", team_name)

    return {
        "team_name": team_name,
        "config_path": config_path,
        "task_path": task_path,
        "teammates": ", ".join(teammate_names) if teammate_names else "none yet",
    }


def main():
    # Consume stdin (hook protocol)
    try:
        sys.stdin.read()
    except Exception:
        pass

    output = CONTEXT

    # Inject team context if an active team exists
    team_ctx = find_team_context()
    if team_ctx:
        output += TEAM_CONTEXT_TEMPLATE.format(**team_ctx)

    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
