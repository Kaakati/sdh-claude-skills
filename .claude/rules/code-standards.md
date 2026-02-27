# Code Standards

Universal coding standards for all source code in this project.

## Naming Conventions

- **JavaScript/TypeScript**: `camelCase` for variables and functions, `PascalCase` for classes and interfaces, `UPPER_SNAKE_CASE` for constants
- **Python**: `snake_case` for variables and functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- **Files**: `kebab-case` for general files, `PascalCase` for component files (React)
- **Booleans**: Prefix with `is`, `has`, `can`, `should` — e.g., `isActive`, `hasPermission`
- **Functions**: Use verb-noun pairs — e.g., `getUser`, `validateInput`, `calculateTotal`
- **Avoid**: Single-letter names (except loop indices), abbreviations, generic names like `data`, `info`, `temp`

## SOLID Principles

- **Single Responsibility (SRP)**: A class or module should have one reason to change. If you describe it with "and", split it.
- **Open/Closed (OCP)**: Open for extension, closed for modification. Use interfaces and composition over modifying existing code.
- **Liskov Substitution (LSP)**: Subtypes must be substitutable for their base types without altering correctness.
- **Interface Segregation (ISP)**: Prefer many small, specific interfaces over one large general-purpose interface.
- **Dependency Inversion (DIP)**: High-level modules must not depend on low-level modules. Both should depend on abstractions.

## Function and File Limits

- **Function length**: Maximum 30 lines. If a function exceeds this, decompose it into smaller, well-named helper functions.
- **File length**: Target maximum 300 lines. When a file exceeds this, consider whether it has multiple responsibilities that can be separated.
- **Parameters**: Maximum 4 parameters per function. Use an options/config object for more.
- **Nesting depth**: Maximum 3 levels of nesting. Extract early returns or helper functions to reduce depth.

## Error Handling

- **Never swallow errors silently**. Every `catch` block must log, rethrow, or handle the error meaningfully.
- **Use custom error classes** for domain-specific errors:
  ```typescript
  class NotFoundError extends AppError {
    constructor(resource: string, id: string) {
      super(`${resource} with id ${id} not found`, 404);
    }
  }
  ```
- **Fail fast**: Validate inputs at the boundary and return early on invalid state.
- **Error propagation**: Let errors bubble up to a centralized handler. Do not catch and re-throw without adding context.
- **Never use exceptions for flow control**. Exceptions are for exceptional circumstances.

## Logging Standards

- **Structured logs**: Use JSON format for machine-parseable logs.
- **Log levels**:
  - `error` — Unrecoverable failures requiring attention
  - `warn` — Degraded behavior, potential issues
  - `info` — Significant business events (user created, order placed)
  - `debug` — Diagnostic information for development
- **Include context**: Request ID, user ID, operation name, duration.
- **Never log**: Passwords, tokens, PII, credit card numbers, or secrets.
- **Correlation IDs**: Include a request/trace ID in all logs for distributed tracing.

## Constants and Magic Numbers

- **No magic numbers or strings**. Extract all literals into named constants:
  ```typescript
  // Bad
  if (retries > 3) { ... }

  // Good
  const MAX_RETRY_ATTEMPTS = 3;
  if (retries > MAX_RETRY_ATTEMPTS) { ... }
  ```
- **Group related constants** in enums or constant objects.
- **Configuration values** belong in environment variables or config files, not in code.

## General Principles

- Prefer composition over inheritance.
- Prefer immutability — use `const`, `readonly`, `Object.freeze` where appropriate.
- Avoid premature optimization. Write clear code first, optimize with measurements.
- Delete dead code. Do not comment it out "for later."
- Every public API should have a clear contract — typed parameters and return values.
