#!/usr/bin/env python3
"""
SubagentStart hook: Inject tech stack context.

Prints the project tech stack summary so subagents are aware of the
development environment. Always exits 0.
"""
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


def main():
    # Consume stdin (hook protocol)
    try:
        sys.stdin.read()
    except Exception:
        pass

    print(CONTEXT)
    sys.exit(0)


if __name__ == "__main__":
    main()
