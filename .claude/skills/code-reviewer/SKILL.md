---
name: code-reviewer
description: Review code and pull requests for quality, security, test coverage, and adherence to team conventions. Use this skill whenever someone asks to review a PR, check code quality, audit a diff, evaluate a changeset, or says things like "review my code", "check this PR", "look at my changes", "is this code good", "audit this module", or "what do you think of this diff". Also trigger when someone mentions code quality concerns, technical debt assessment, or asks for feedback on implementation approach.
agent: code-reviewer
model: sonnet
---

# Code Reviewer

Perform systematic code and PR reviews for quality, maintainability, and adherence to team conventions.

## Dynamic Context (auto-loaded when available)

!`git diff HEAD~1 --stat 2>/dev/null || echo "No git diff available"`

!`git log --oneline -5 2>/dev/null || echo "No git log available"`

## Review Protocol

### Step 1: Understand Context

1. Review the diff and commit messages above to understand scope and intent.
2. Identify which layers are affected: API, service, model, migration, mobile, infrastructure.
3. Check if there is a related issue, ticket, or specification to validate against.
4. Map the change to the broader architecture.

### Step 2: Structural Review

1. **File organization** — Are changes in the correct modules? Do new files follow the project's directory structure conventions?
2. **Import hygiene** — No unused imports, no circular dependencies, imports ordered per project convention.
3. **Module boundaries** — Does the change respect architectural layers? No domain logic in controllers, no data access in presentation.
4. **SOLID principles**:
   - **Single Responsibility**: Each class/module/function does one thing.
   - **Open/Closed**: Extended via abstraction, not modification of existing behavior.
   - **Liskov Substitution**: Subtypes are substitutable for their base types.
   - **Interface Segregation**: No forced dependencies on unused interfaces.
   - **Dependency Inversion**: High-level modules depend on abstractions, not concretions.

### Step 3: Code Quality Analysis

#### Readability
- Variable and function names clearly express intent.
- No abbreviations unless they are universally understood domain terms.
- Functions are short and focused (prefer under 30 lines).
- Comments explain *why*, not *what* — self-documenting code is preferred.
- No dead code, commented-out blocks, or TODO items without tracking references.

#### Complexity
- **Cyclomatic complexity must be below 10** per function.
- Nesting depth should not exceed 3 levels — use early returns, guard clauses, or extraction.
- Boolean expressions should be simple — extract complex conditions into named variables or functions.
- Avoid long parameter lists (more than 4 parameters suggests a need for an options object or restructuring).

#### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `camelCase` or `snake_case` per project convention
- Constants: `UPPER_SNAKE_CASE`
- Boolean variables: prefix with `is`, `has`, `should`, `can`
- Event handlers: prefix with `handle` or `on`
- Async functions: name should imply async nature where not obvious

#### Error Handling
- All external calls (API, database, file I/O) have error handling.
- Error messages are descriptive and include context (what failed, what was expected).
- No swallowed exceptions — every catch block logs, re-throws, or handles meaningfully.
- Custom error types used where appropriate for domain-specific failures.
- Error responses follow the project's standard error format.

### Step 4: Security Scan

- No hardcoded secrets, API keys, tokens, or passwords.
- User input is validated and sanitized before use.
- SQL queries use parameterized statements.
- Authentication and authorization checks are present where required.
- No sensitive data logged or exposed in error messages.
- File paths are validated to prevent path traversal.

Refer to the `security-auditor` skill for deeper security analysis.

### Step 5: Performance Check

- No N+1 query patterns — batch data fetching where possible.
- Expensive operations are not inside loops.
- Database queries use appropriate indexes (check query plans for new queries).
- Large data sets use pagination or streaming.
- No unnecessary re-renders in frontend code (check memoization, dependency arrays).
- Caching is used where appropriate and cache invalidation is handled.

### Step 6: Test Coverage Assessment

- New code paths have corresponding tests.
- Edge cases are covered: null/undefined inputs, empty collections, boundary values.
- Error paths are tested — not just the happy path.
- Mocks are used appropriately — external dependencies mocked, internal logic tested directly.
- Test names clearly describe the scenario and expected outcome.
- No test interdependencies — each test is independent and idempotent.

### Step 7: Documentation Check

- Public APIs have documentation (JSDoc, docstrings, or equivalent).
- Complex algorithms have explanatory comments.
- README or relevant docs are updated if behavior changes.
- Breaking changes are documented in changelog or migration guide.
- Configuration changes are documented with defaults and valid ranges.

### Step 8: Accessibility Check (React Native)

#### Review Checklist
- Interactive elements have `accessibilityLabel` and `accessibilityRole` props.
- Images have `accessibilityLabel` describing content (not "image of...").
- Touch targets are at least 44x44 points.
- Color is not the sole means of conveying information (check color-blind safety).
- Screen reader navigation order is logical (`accessibilityOrder` or DOM order).
- Dynamic content updates announced via `AccessibilityInfo.announceForAccessibility`.
- Forms have visible labels (not just placeholders) and error messages associated with fields.

#### Implementation Patterns

**Accessible Touchable Components**:
```tsx
<TouchableOpacity
  accessibilityRole="button"
  accessibilityLabel="Delete order"
  accessibilityHint="Removes this order from your history"
  style={{ minHeight: 44, minWidth: 44 }}
  onPress={handleDelete}
>
  <TrashIcon />
</TouchableOpacity>
```

**Accessible Form Fields**:
```tsx
<View>
  <Text nativeID="emailLabel">Email Address</Text>
  <TextInput
    accessibilityLabelledBy="emailLabel"
    accessibilityRole="none"
    textContentType="emailAddress"
    autoComplete="email"
  />
  {error && <Text accessibilityRole="alert">{error}</Text>}
</View>
```

**Live Region for Dynamic Content**:
```tsx
<Text accessibilityLiveRegion="polite">
  {`${items.length} items in cart`}
</Text>
```

**Grouping Related Elements**:
```tsx
<View accessible={true} accessibilityLabel={`Order ${order.id}, status ${order.status}, total ${order.total}`}>
  <Text>{order.id}</Text>
  <Text>{order.status}</Text>
  <Text>{order.total}</Text>
</View>
```

### Step 9: Stack-Specific Checks (Rails + React Native)

**Rails**: Panko serializers used (not raw models)? Service objects for business logic? Pundit `authorize` on every action? Sidekiq jobs idempotent? Redis cache TTLs set?

**React Native**: Server data in TanStack Query (not Zustand)? Proper `staleTime`? `FlatList` for lists? `useCallback` on render functions? Centrifugo subscriptions cleaned up on unmount?

**Migrations**: Reversible? Foreign keys indexed? PostGIS columns have GiST index? No data + schema changes mixed?

## Output Format

Present findings in this table format:

| Category | Finding | Severity | File:Line | Recommendation |
|---|---|---|---|---|
| Readability | Function `processData` is 85 lines long | Medium | src/service.ts:42 | Extract into smaller focused functions |
| Complexity | Nested if/else 5 levels deep | High | src/handler.ts:112 | Use early returns and guard clauses |
| Security | API key hardcoded in config | Critical | src/config.ts:8 | Move to environment variable |
| Performance | N+1 query in user listing | High | src/users.ts:67 | Use eager loading or batch query |
| Testing | No tests for error handling path | Medium | src/auth.ts:34 | Add test for invalid token scenario |

### Severity Levels

- **Critical**: Security vulnerabilities, data loss risks, production-breaking issues. Must fix before merge.
- **High**: Bugs, significant performance issues, major maintainability concerns. Should fix before merge.
- **Medium**: Code quality issues, minor performance concerns, missing tests. Fix or create follow-up ticket.
- **Low**: Style preferences, minor improvements, suggestions. Optional — discuss with author.

## Summary Template

After the findings table, provide:

1. **Overall Assessment**: Approve / Request Changes / Needs Discussion
2. **Strengths**: What was done well (always include positive feedback).
3. **Key Issues**: Top 3 items that must be addressed.
4. **Suggestions**: Optional improvements for consideration.
