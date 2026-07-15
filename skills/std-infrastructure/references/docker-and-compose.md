# Docker & Compose — Local Development and Image Builds

Load-bearing rules restated (they hold even if you read nothing else):
- **Pin every image version.** `latest` is never allowed in a committed file.
- **Never commit real secrets.** `.env.development` holds local-only values; `.env.example` lists every required key with empty values.
- **Production containers run as a non-root user.**

---

## Decision: I need a local dev stack for this project

The core services are Rails, PostgreSQL + PostGIS, Redis, and Centrifugo. `docker-compose.yml` is committed and identical for every developer. `docker-compose.override.yml` is gitignored and holds per-developer settings (port remaps, extra mounts, debug flags) — Compose merges it automatically.

Data lives in **named volumes** (`postgres_data`, `redis_data`), never in bind mounts, so `docker compose down` does not destroy the database.

Every service declares a **health check**, and dependents wait on it with `condition: service_healthy`. Without this, Rails boots before Postgres accepts connections and crash-loops on first run.

### Bad — unpinned images, no health checks, no dependency ordering

```yaml
# docker-compose.yml
services:
  db:
    image: postgis/postgis          # BAD: floating tag, breaks silently on upstream release
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - ./tmp/db:/var/lib/postgresql/data   # BAD: bind mount, permissions + perf problems

  redis:
    image: redis:latest             # BAD

  app:
    build: .
    depends_on:
      - db                          # BAD: only waits for container start, not readiness
      - redis
    environment:
      DATABASE_URL: postgres://postgres:postgres@db:5432/app_development
      AWS_SECRET_ACCESS_KEY: AKIA... # BAD: real credential committed
```

### Good — pinned, health-checked, named volumes, env from file

```yaml
# docker-compose.yml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app_development
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app_development"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7.2-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  centrifugo:
    image: centrifugo/centrifugo:v5.4.0
    command: ["centrifugo", "-c", "/centrifugo/config.json"]
    volumes:
      - ./config/centrifugo.json:/centrifugo/config.json:ro
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "sh", "-c", "wget -qO- http://localhost:8000/health || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 5

  app:
    build:
      context: .
      target: development
    env_file:
      - .env.development
    environment:
      RAILS_ENV: development
      DATABASE_URL: postgres://postgres:postgres@db:5432/app_development
      REDIS_URL: redis://redis:6379/0
    ports:
      - "3000:3000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  sidekiq:
    build:
      context: .
      target: development
    command: ["bundle", "exec", "sidekiq"]
    env_file:
      - .env.development
    depends_on:
      redis:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
```

```yaml
# docker-compose.override.yml   (gitignored — per developer)
services:
  app:
    ports:
      - "3001:3000"   # this dev already has 3000 in use
    environment:
      RUBY_DEBUG_OPEN: "true"
```

---

## Decision: I need a production image for the Rails app

Use a **multi-stage build**: stage 1 installs gems and precompiles assets; stage 2 copies only the built artifacts onto a minimal `ruby:x.y-slim` base. Build toolchains (`build-essential`, node, headers) must not survive into the runtime image — they add hundreds of MB and attack surface.

`Gemfile.lock` is committed and installed with `--deployment`-style settings so the image is reproducible.

### Bad — single stage, root user, build tools shipped to production

```dockerfile
# Dockerfile
FROM ruby:3.3                 # BAD: full image (~1GB), includes compilers and git
WORKDIR /app
COPY . .                      # BAD: copies .git, tmp, log, .env — and busts cache on every source edit
RUN apt-get update && apt-get install -y build-essential nodejs
RUN bundle install            # BAD: re-runs on any file change; dev+test gems included
RUN bundle exec rails assets:precompile
EXPOSE 3000
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]
# BAD: no USER directive — runs as root
```

### Good — multi-stage, layer-cached, slim runtime, non-root

```dockerfile
# syntax=docker/dockerfile:1
ARG RUBY_VERSION=3.3.6

# ---------- base ----------
FROM ruby:${RUBY_VERSION}-slim AS base
WORKDIR /app
ENV BUNDLE_PATH=/usr/local/bundle \
    BUNDLE_JOBS=4 \
    RAILS_LOG_TO_STDOUT=1
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y curl libpq5 libvips && \
    rm -rf /var/lib/apt/lists/*

# ---------- build ----------
FROM base AS build
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y build-essential libpq-dev git pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY Gemfile Gemfile.lock ./
RUN bundle config set --local without 'development test' && \
    bundle install && \
    rm -rf "${BUNDLE_PATH}"/ruby/*/cache "${BUNDLE_PATH}"/ruby/*/bundler/gems/*/.git

COPY . .
RUN SECRET_KEY_BASE_DUMMY=1 bundle exec rails assets:precompile

# ---------- development ----------
FROM base AS development
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y build-essential libpq-dev git && \
    rm -rf /var/lib/apt/lists/*
COPY Gemfile Gemfile.lock ./
RUN bundle install
COPY . .
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]

# ---------- production runtime ----------
FROM base AS production
ENV RAILS_ENV=production
COPY --from=build "${BUNDLE_PATH}" "${BUNDLE_PATH}"
COPY --from=build /app /app

RUN groupadd --system --gid 1000 rails && \
    useradd rails --uid 1000 --gid 1000 --create-home --shell /bin/bash && \
    chown -R rails:rails /app/log /app/tmp
USER 1000:1000

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:3000/up || exit 1
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]
```

`COPY Gemfile Gemfile.lock` **before** `COPY . .` is the whole point: editing a controller must not invalidate the `bundle install` layer.

---

## Decision: what goes in `.dockerignore`

Anything not needed to build. Omitting this leaks `.env` files into the image layers and slows every build.

```
# .dockerignore
.git
.gitignore
.github
node_modules
tmp/*
!tmp/.keep
log/*
!log/.keep
.env*
!.env.example
storage
coverage
spec
test
*.md
.dockerignore
Dockerfile*
docker-compose*.yml
```

---

## Decision: how do I configure the app across environments

Everything is an environment variable — no environment-conditional code paths reading config files. Local development uses `dotenv-rails` (`.env.development`); **`dotenv-rails` must be in the `:development, :test` groups only** and never loaded in production, where values come from the ECS task definition / AWS Secrets Manager.

Canonical names: `RAILS_ENV`, `DATABASE_URL`, `REDIS_URL`, `CENTRIFUGO_API_KEY`.

### Bad

```ruby
# config/initializers/centrifugo.rb
CENTRIFUGO_API_KEY = "8f2a-live-key-9911"   # BAD: hardcoded secret in the repo
CENTRIFUGO_URL = Rails.env.production? ? "https://ws.example.com" : "http://localhost:8000"
```

```
# .env  (committed — BAD)
DATABASE_URL=postgres://admin:hunter2@prod-db.example.com:5432/app
```

### Good

```ruby
# config/initializers/centrifugo.rb
Rails.application.config.centrifugo = ActiveSupport::OrderedOptions.new.tap do |c|
  c.url     = ENV.fetch("CENTRIFUGO_URL")       # fetch: fail fast at boot if unset
  c.api_key = ENV.fetch("CENTRIFUGO_API_KEY")
end
```

```
# .env.example  (committed — keys only, no values)
RAILS_ENV=
DATABASE_URL=
REDIS_URL=
CENTRIFUGO_URL=
CENTRIFUGO_API_KEY=
AWS_REGION=
S3_BUCKET=
```

```ruby
# Gemfile
group :development, :test do
  gem "dotenv-rails"
end
```
