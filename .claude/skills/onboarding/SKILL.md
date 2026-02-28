---
name: onboarding
description: Create developer onboarding guides, setup documentation, and knowledge base articles for software teams. Use this skill whenever someone asks to create onboarding docs, setup instructions, a getting started guide, team documentation, runbooks, or says things like "help new devs get started", "document our setup process", "write the onboarding guide", "create a runbook for X", or "how should we document this for the team". Also trigger when someone asks about reducing onboarding time, knowledge transfer, or team documentation strategy.
model: haiku
---

# Onboarding Guide Builder

Create onboarding documentation that gets a new developer productive in days, not weeks. Good onboarding docs are the highest-leverage documentation a team can write — they pay dividends on every hire for years.

## Onboarding Workflow

### Step 1: Prerequisites

Verify the new developer has the following installed and configured:

#### Required Tools
- **Git**: Version 2.30+ with SSH key configured for the repository host.
- **Runtime**: The project's language runtime at the version specified in `.tool-versions`, `.nvmrc`, `runtime.txt`, or equivalent.
- **Package manager**: npm/yarn/pnpm (Node.js), pip/poetry (Python), bundler (Ruby), etc.
- **Docker**: Docker Desktop or Docker Engine with Compose for local service dependencies.
- **IDE/Editor**: Recommended IDE with project-specific extensions/plugins installed.
- **Database client**: CLI or GUI tool for the project's database.

#### Accounts and Access
- [ ] Repository access (GitHub/GitLab/Bitbucket).
- [ ] CI/CD pipeline access (read at minimum).
- [ ] Cloud provider console access (staging environment).
- [ ] Monitoring and logging platform access.
- [ ] Project management tool (Jira, Linear, etc.).
- [ ] Communication channels (Slack, Teams, etc.).
- [ ] Secrets/credentials for local development (via team lead).

### Step 2: Repository Setup

```bash
# Clone the repository
git clone {repository-url}
cd {project-name}

# Install dependencies
{install-command}

# Copy environment configuration
cp .env.example .env
# Edit .env with local values (database URL, API keys for dev, etc.)

# Start local services (database, cache, message queue)
docker-compose up -d

# Run database migrations
{migration-command}

# Seed development data (if available)
{seed-command}

# Verify setup — run the test suite
{test-command}

# Start the development server
{dev-command}
```

After setup, verify:
- [ ] Application starts without errors.
- [ ] Tests pass.
- [ ] Can access the application in browser or via API client.
- [ ] Database is populated with seed data.

### Step 3: Architecture Walkthrough

Present the high-level architecture to the new developer:

#### System Overview
1. Draw or show the system architecture diagram.
2. Explain each service/component and its responsibility.
3. Identify the boundaries: what this service owns vs. what it depends on.
4. Explain the data flow for a typical user request.

#### Project Structure
Walk through the directory structure:

```
src/
  api/          # HTTP handlers, routes, middleware
  services/     # Business logic layer
  models/       # Data models and database entities
  repositories/ # Data access layer
  utils/        # Shared utilities
  config/       # Application configuration
tests/
  unit/         # Unit tests
  integration/  # Integration tests
  e2e/          # End-to-end tests
  fixtures/     # Test data factories
docs/           # Project documentation
scripts/        # Development and deployment scripts
```

Explain the conventions:
- Where new features should be added.
- How layers communicate (controllers call services, services call repositories).
- How configuration is loaded and used.
- Where tests go and how they are organized.

#### Key Design Patterns
Walk through the 3-5 most important patterns used in the project:
- Authentication and authorization flow.
- Error handling pattern.
- Data validation approach.
- Async job processing (if applicable).
- Event-driven communication (if applicable).

### Step 4: Development Workflow

#### Daily Workflow
1. Pull latest changes from the main branch.
2. Create a feature branch from main: `git checkout -b feature/{ticket-id}-{description}`.
3. Make changes, write tests, verify locally.
4. Commit with descriptive messages (see commit conventions below).
5. Push the branch and create a pull request.
6. Address review feedback.
7. Merge after approval.

#### Commit Message Convention
```
{type}({scope}): {description}

{optional body}

{optional footer}
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

Examples:
- `feat(auth): add password reset flow`
- `fix(orders): correct tax calculation for international orders`
- `refactor(users): extract validation into middleware`

#### Branch Naming
- Feature: `feature/{ticket-id}-{short-description}`
- Bug fix: `fix/{ticket-id}-{short-description}`
- Hotfix: `hotfix/{ticket-id}-{short-description}`

#### Pull Request Process
1. Fill out the PR template completely.
2. Link the related ticket/issue.
3. Add screenshots or recordings for UI changes.
4. Request review from at least one team member.
5. Address all review comments or discuss disagreements.
6. Squash and merge after approval (or per team convention).

### Step 5: Code Review Process

#### As a Reviewer
- Review within 24 hours of being requested.
- Check for correctness, readability, test coverage, and adherence to conventions.
- Use the code-reviewer skill for systematic reviews.
- Be constructive — suggest alternatives, not just criticize.
- Approve when the code is good enough, not when it is perfect.

#### As an Author
- Keep PRs small and focused (under 400 lines of changes).
- Write a clear PR description explaining what and why.
- Self-review your PR before requesting review.
- Respond to all comments, even if just acknowledging.

### Step 6: Testing Expectations

- Write tests for all new code.
- Run the full test suite before pushing.
- Tests must pass in CI before merge.
- Use the test-generator skill for guidance on test structure.
- Coverage target: 80% line coverage for new code.

### Step 7: Deployment Process

- Staging deploys happen automatically on merge to main (or manually triggered).
- Production deploys are scheduled and coordinated with the team.
- Use the deploy skill for deployment procedures.
- Never deploy directly to production without the deployment checklist.

### Step 8: Getting Help

- **Code questions**: Search the codebase, read tests for examples, ask on the team channel.
- **Architecture questions**: Check documentation in `docs/`, ask the tech lead.
- **Process questions**: Refer to this onboarding guide and the dev-handbook.
- **Blocked on access/tools**: Contact the team lead immediately.

### Step 9: Web Frontend Setup

#### Vite SPA Setup
```bash
# Navigate to web directory
cd web/

# Install dependencies
npm install

# Start development server (default port 5173)
npm run dev
# App available at http://localhost:5173

# Run tests
npm run test

# Build for production
npm run build
```

#### Next.js Setup
```bash
# Navigate to next directory
cd next/

# Install dependencies
npm install

# Start development server (port 3001 to avoid conflict with Vite)
npm run dev -- -p 3001
# App available at http://localhost:3001

# Run tests
npm run test

# Build for production
npm run build
```

#### Web Project Structure Walkthrough
```
web/                          # Vite SPA (React + React Router)
├── src/
│   ├── pages/               # One page per route (lazy-loaded)
│   ├── components/          # Shared UI components
│   ├── hooks/               # Custom hooks (business logic)
│   ├── api/                 # TanStack Query hooks + axios client
│   ├── stores/              # Zustand stores (client-only state)
│   ├── domain/              # TypeScript domain types
│   ├── router/              # React Router configuration
│   └── i18n/                # Internationalization

next/                         # Next.js App Router (SSR/SSG)
├── app/                     # App Router pages and layouts
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page (Server Component)
│   └── (dashboard)/         # Route group
├── src/
│   ├── actions/             # Server actions (mutations)
│   ├── components/          # Shared components
│   ├── hooks/               # Client-side hooks
│   └── api/                 # Rails API client
├── middleware.ts             # Auth, locale detection
```

#### Key Conventions for Web
- **All frontends share the same Rails API** — React Native, Vite SPA, and Next.js.
- **TanStack Query** for server data, **Zustand** for client-only state (same pattern across all frontends).
- **Tailwind CSS** for web styling (not used in React Native).
- **Vitest** for web testing (not Jest).

## First Week Plan

| Day | Focus | Goal |
|---|---|---|
| Day 1 | Setup | Environment running, tests passing, architecture overview |
| Day 2 | Exploration | Read key modules, trace a request end-to-end, review recent PRs |
| Day 3 | First task | Pick a small bug fix or documentation improvement |
| Day 4 | First PR | Submit PR, go through the review process |
| Day 5 | Review | Review a teammate's PR, deeper dive into a module |
