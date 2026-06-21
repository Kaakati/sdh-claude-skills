# Documentation Templates

## Model Documentation Template
```markdown
# [ModelName]

## Description
[What this model represents in the domain]

## Table: [table_name]

| Column | Type | Null | Default | Description |
|--------|------|------|---------|-------------|
| id | bigint | no | auto | Primary key |
| ... | ... | ... | ... | ... |

## Associations
- `belongs_to :parent`
- `has_many :children`
- `has_many :related, through: :join_table`

## Validations
- `name`: presence, length(max: 255)
- `email`: presence, uniqueness, format

## Scopes
- `active`: `where(active: true)`
- `recent`: `order(created_at: :desc)`

## Key Methods
- `#full_name`: Returns first + last name
- `#within_radius?(lat, lng, km)`: PostGIS spatial check

## Serializers
- `ModelListSerializer`: id, name, status (for lists)
- `ModelDetailSerializer`: all fields + associations (for detail views)
```

## Service Object Documentation Template
```markdown
# [ServiceName]

## Purpose
[What this service does]

## Usage
```ruby
result = ServiceName.new(param1: value, param2: value).call
if result.success?
  # handle success
else
  # handle failure: result.error
end
```

## Parameters
| Name | Type | Required | Description |
|------|------|----------|-------------|
| param1 | String | yes | ... |
| param2 | Integer | no | Default: 10 |

## Returns
- **Success**: `Result.success(model_instance)`
- **Failure**: `Result.failure("error message")`

## Side Effects
- Creates [records]
- Sends [notifications]
- Publishes to Centrifugo channel: [channel]
- Enqueues Sidekiq job: [JobName]

## Error Handling
- `ActiveRecord::RecordInvalid`: Returns failure with validation errors
- `ExternalApiError`: Retries 3x, then returns failure
```

## React Native Screen Documentation Template
```markdown
# [ScreenName]

## Purpose
[What this screen displays/does]

## Navigation
- **Route**: `screens/ScreenName`
- **Params**: `{ id: string, mode?: 'edit' | 'view' }`
- **Back**: Returns to [PreviousScreen]

## Data Sources
- **Server data**: `useQuery(['resource', id])` — from TanStack Query
- **Client state**: `useAuthStore(s => s.user)` — from Zustand
- **Real-time**: `useCentrifugoChannel('resource:${id}')` — live updates

## User Actions
| Action | Handler | Effect |
|--------|---------|--------|
| Pull to refresh | `refetch()` | Reloads data from API |
| Tap item | `navigation.navigate` | Opens detail screen |
| Submit form | `mutation.mutate()` | Creates/updates resource |

## Components Used
- `Header` — Screen header with back button
- `ResourceCard` — Displays resource summary
- `LoadingSpinner` — During initial load

## Accessibility
- Screen reader labels on all interactive elements
- Keyboard navigation support
- Minimum touch target: 44x44pt
```

## Sidekiq Job Documentation Template
```markdown
# [JobName]

## Purpose
[What this background job does]

## Queue
`default` | `critical` | `low_priority` | `mailers`

## Parameters
| Name | Type | Description |
|------|------|-------------|
| record_id | Integer | ID of the record to process |

## Idempotency
[How this job handles being run multiple times with the same arguments]

## Retry Behavior
- Max retries: 5
- Retry on: `NetworkError`, `TimeoutError`
- Discard on: `RecordNotFound`

## Dependencies
- External API: [name, endpoint]
- Redis cache: [keys read/written]
- Centrifugo: [channels published to]

## Monitoring
- Expected duration: < [X] seconds
- Alert if queue latency > [Y] seconds
- Dashboard: [URL]
```

## Terraform Module Documentation Template
```markdown
# Module: [module_name]

## Purpose
[What infrastructure this module creates]

## Resources Created
- `aws_ecs_service` — [Description]
- `aws_rds_instance` — [Description]

## Input Variables
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|

## Outputs
| Name | Description |
|------|-------------|

## Usage
```hcl
module "api" {
  source = "../../modules/ecs"

  cluster_name = "production"
  service_name = "rails-api"
  # ...
}
```

## Dependencies
- Requires VPC module output
- Requires RDS module output for DATABASE_URL
```
