# Developer Handbook

## Tech Stack Deep Dive

### Ruby on Rails
- **Version**: See Gemfile for exact version
- **Mode**: API-only (`config.api_only = true`)
- **Authentication**: Devise + devise-jwt for token-based auth
- **Authorization**: Pundit policies — one policy per model
- **Serialization**: Panko::Serializer — always define explicit attributes
- **Background Jobs**: Sidekiq with Redis — jobs in `backend/app/jobs/`
- **Pagination**: Pagy gem — fastest pagination in Ruby

### PostgreSQL + PostGIS
- **Version**: See docker-compose.yml
- **PostGIS**: Enabled for geospatial queries
- **Adapter**: `activerecord-postgis-adapter`
- **Spatial types**: `st_point` (locations), `st_polygon` (geofences)
- **Spatial index**: GiST index on all geometry/geography columns
- **RGeo**: Ruby interface for geometry operations

### React Native
- **State**: Zustand (client state only — auth, UI preferences, offline queue)
- **Server data**: TanStack Query (all API data lives here)
- **Navigation**: React Navigation with typed params
- **Forms**: react-hook-form + zod validation
- **Storage**: react-native-mmkv (fast key-value, replaces AsyncStorage)

### Centrifugo (Real-time)
- **Protocol**: WebSocket with fallback
- **Channels**: Namespaced — `chat:room_123`, `user:456`, `location:fleet`
- **Auth**: JWT-based channel authorization
- **Publishing**: Rails publishes via Centrifugo HTTP API
- **Client**: centrifuge-js SDK in React Native

### Redis
- **Caching**: Rails.cache backend with explicit TTLs
- **Queues**: Sidekiq job processing
- **Sessions**: Optional session store
- **Pub/Sub**: Internal event distribution

### Infrastructure
- **AWS**: ECS Fargate (compute), RDS (database), ElastiCache (Redis), S3 (storage)
- **Terraform**: All infrastructure defined as code in `terraform/`
- **Docker Compose**: Local development environment
- **CI/CD**: GitHub Actions — lint, test, build, deploy

## Code Review Process

1. **Self-review**: Use `/code-reviewer` skill before opening PR
2. **PR template**: Fill out description, test plan, screenshots (if UI)
3. **Reviewer assignment**: Auto-assigned based on CODEOWNERS
4. **Review SLA**: Reviews within 4 business hours
5. **Merge**: Squash merge after approval, delete source branch

## Testing Strategy

### Rails (RSpec)
```bash
bundle exec rspec                    # Full suite
bundle exec rspec spec/models/       # Models only
bundle exec rspec spec/requests/     # API integration tests
bundle exec rspec --tag focus        # Run focused tests
```
- Use `factory_bot` for test data
- Use `shoulda-matchers` for model specs
- Use `webmock` for external HTTP stubbing
- Use `database_cleaner` for test isolation

### React Native (Jest)
```bash
cd mobile
npm test                             # Full suite
npm test -- --watch                  # Watch mode
npm test -- OrderScreen.test.tsx     # Single file
```
- Use `@testing-library/react-native` for component tests
- Use `msw` (Mock Service Worker) for API mocking
- Use `jest.mock` for native modules

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgis://user:pass@localhost/app_dev` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `CENTRIFUGO_API_URL` | Centrifugo HTTP API | `http://localhost:8000/api` |
| `CENTRIFUGO_API_KEY` | Centrifugo API key | `my-api-key` |
| `CENTRIFUGO_SECRET` | Centrifugo JWT secret | `my-secret` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET` | S3 bucket for uploads | `myapp-uploads-dev` |
| `RAILS_MASTER_KEY` | Rails credentials key | (from team lead) |

## Incident Response

1. **Detect**: CloudWatch alarm or user report
2. **Acknowledge**: Claim the incident in PagerDuty/Opsgenie
3. **Diagnose**: Check logs (CloudWatch), errors (Sentry), metrics (Grafana)
4. **Fix**: Apply fix or rollback deployment
5. **Communicate**: Update status page and Slack `#incidents`
6. **Post-mortem**: Write ADR within 48 hours, no blame

## Getting Help
- **Stuck on code?** Use Claude Code with our custom agents and skills
- **Vague requirements?** Use the `/requirements-consultant` agent
- **Architecture question?** Use the `architecture-advisor` agent
- **Team Slack**: `#engineering`, `#code-review`, `#incidents`
