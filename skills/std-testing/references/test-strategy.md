# Test Strategy: Choosing the Level and the Doubles

Load-bearing rules restated (this file stands alone):
- **Mock external dependencies** (DB, HTTP, filesystem, email, third-party SDKs). **Never mock internal
  logic** — if you must, the design needs dependency injection.
- Test **behavior**, not implementation. Coverage floors: 80% business logic, 60% overall, 100% on
  auth/authz/payments/validation. Branch coverage, not line coverage.

---

## Decision: which level of test am I writing?

| Signal in the task | Level | Rule |
|---|---|---|
| Pure function, service object, validator, reducer, store | **Unit** | No I/O at all. Milliseconds. Many of these. |
| "Does the controller + serializer + DB actually agree?" | **Integration** | Real DB, real router. Mock only the network edge. Get the real dependency from **test containers or an in-memory database** — never a shared/staging DB. |
| "Can a user complete signup end-to-end?" | **E2E** | Critical paths only. Slow and brittle by nature — keep the count in single digits. |
| "Does our API still match what mobile expects?" | **Contract** | Pact or schema snapshot at the service boundary. |

The pyramid is a budget, not a suggestion: many unit, some integration, few E2E.

### The boundary rule

Draw the mock at the **process boundary**, never inside your own domain.

```ruby
# BAD — mocks an internal collaborator; the test now asserts wiring, not behavior.
# Refactor PricingCalculator instead of stubbing it.
RSpec.describe OrderService do
  it "should apply discount when customer is a member" do
    calculator = instance_double(PricingCalculator, total: 90)
    allow(PricingCalculator).to receive(:new).and_return(calculator)

    result = described_class.new(order).call

    expect(result.total).to eq(90) # tautology: we asserted our own stub
  end
end
```

```ruby
# GOOD — real internal logic, fake only the external payment gateway (injected).
RSpec.describe OrderService do
  let(:gateway) { instance_double(Stripe::Gateway, charge: Stripe::Charge.new(id: "ch_1")) }

  it "should apply member discount when customer is a member" do
    order = create(:order, customer: create(:customer, :member), subtotal_cents: 10_000)

    result = described_class.new(order, gateway: gateway).call

    expect(result.total_cents).to eq(9_000)
    expect(gateway).to have_received(:charge).with(amount_cents: 9_000)
  end
end
```

---

## Decision: how do I build test data?

Never hand-roll a full object in every test — the noise hides the one field that matters.

```typescript
// BAD — 12 lines of irrelevant setup; the reader cannot see that `role` is the point.
it("should deny access when user is not an admin", () => {
  const user = {
    id: "user-123", name: "Test User", email: "test@example.com",
    role: "user", createdAt: new Date(), verified: true, locale: "en",
  };
  expect(canDeleteProject(user)).toBe(false);
});
```

```typescript
// GOOD — builder with overrides; the test states exactly one variable.
function buildUser(overrides?: Partial<User>): User {
  return {
    id: "user-123",
    name: "Test User",
    email: "test@example.com",
    role: "user",
    createdAt: new Date("2024-01-01"),
    verified: true,
    locale: "en",
    ...overrides,
  };
}

it("should deny access when user is not an admin", () => {
  expect(canDeleteProject(buildUser({ role: "user" }))).toBe(false);
});

it("should allow access when user is an admin", () => {
  expect(canDeleteProject(buildUser({ role: "admin" }))).toBe(true);
});
```

Rails equivalent: FactoryBot factories with traits (`create(:customer, :member)`). Build the minimum —
`build` over `create` whenever the record never needs to hit the DB.

**Independence rule**: each test creates its own data. `beforeEach`/`let` for setup, never `beforeAll`
with mutation. Every test must pass in isolation and in any order.

---

## Decision: which edge cases must this suite cover?

Every suite covers all five categories or it is incomplete:

1. **Null/undefined** — missing optional values.
2. **Empty** — empty string, empty array, zero.
3. **Boundary** — min/max of ranges, pagination limits, string length limits.
4. **Error paths** — network failure, invalid data, unauthorized, timeout.
5. **Concurrency** — race conditions where applicable.

```typescript
describe("validateAge", () => {
  it("should accept minimum valid age of 0", ...);
  it("should accept maximum valid age of 150", ...);
  it("should reject negative age", ...);
  it("should reject age above 150", ...);
  it("should reject null input", ...);
  it("should reject non-numeric input", ...);
});
```

Boundaries come in pairs. If you assert `150` is accepted, assert `151` is rejected in the same suite —
an off-by-one is invisible otherwise.

---

## Decision: mocking a chain vs. simplifying the code

```typescript
// BAD — a four-deep mock chain is the code telling you it has too many dependencies.
const mockDb = {
  connection: { pool: { query: vi.fn().mockReturnValue({ rows: { map: vi.fn() } }) } },
};
```

```typescript
// GOOD — inject a narrow port; the fake is trivial because the seam is right.
interface UserRepo {
  findById(id: string): Promise<User | null>;
}

const fakeRepo: UserRepo = {
  findById: async (id) => (id === "user-123" ? buildUser() : null),
};

const service = new UserService(fakeRepo);
```

Prefer stubs and fakes over mock chains. Pain while mocking is a design signal, not a testing problem.

Reset mocks between tests so state never leaks:

```typescript
beforeEach(() => {
  vi.clearAllMocks();
});
```

---

## Sidekiq jobs (Rails)

```ruby
# BAD — tests that Sidekiq works. Sidekiq's authors already did that.
it "enqueues" do
  expect { WelcomeEmailJob.perform_async(1) }
    .to change(WelcomeEmailJob.jobs, :size).by(1)
end
```

```ruby
# GOOD — two separate concerns: the caller enqueues, and the job does its work.
RSpec.describe RegistrationService do
  it "should enqueue a welcome email when registration succeeds" do
    expect { described_class.new(params).call }
      .to change(WelcomeEmailJob.jobs, :size).by(1)
  end
end

RSpec.describe WelcomeEmailJob do
  it "should deliver a welcome email when the user exists" do
    user = create(:user)

    described_class.new.perform(user.id)

    expect(ActionMailer::Base.deliveries.last.to).to eq([user.email])
  end

  it "should not raise when the user was deleted before the job ran" do
    expect { described_class.new.perform(-1) }.not_to raise_error
  end
end
```

Jobs are units: `described_class.new.perform(...)` directly. Use `Sidekiq::Testing.fake!` for enqueue
assertions, `inline!` only in narrow integration tests.

---

## Anti-patterns (all levels)

- **Testing implementation details** — asserting internal method calls or private state.
- **Snapshot overuse** — snapshots hide intent and fail on cosmetic changes. Use sparingly.
- **Flaky tests** — fix or delete immediately. A flaky test is worse than no test.
- **Commented-out tests** — delete them; version control keeps history.
- **Testing framework code** — do not test that ActiveRecord saves or that axios sends requests.
- **Coverage theater** — high coverage with weak assertions is worse than moderate coverage with
  meaningful ones.
