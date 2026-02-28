# Next.js App Router — Infrastructure Patterns

## Root Layout with Providers

```tsx
// next/app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from '@/components/Providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: { default: 'MyApp', template: '%s | MyApp' },
  description: 'Enterprise application',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

## Loading and Error Boundaries

```tsx
// next/app/orders/loading.tsx
export default function OrdersLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded bg-gray-100" />
        ))}
      </div>
    </div>
  );
}

// next/app/orders/error.tsx
'use client';

export default function OrdersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <h2 className="text-xl font-semibold text-red-600">Something went wrong</h2>
      <p className="mt-2 text-gray-600">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
      >
        Try again
      </button>
    </div>
  );
}
```

## Middleware for Auth and Locale

```typescript
// next/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public paths
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Auth check
  const token = request.cookies.get('auth_token')?.value;
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Locale detection
  const locale = request.headers.get('accept-language')?.split(',')[0]?.split('-')[0] ?? 'en';
  const response = NextResponse.next();
  response.headers.set('x-locale', locale);

  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

## Server Component Test

```tsx
// tests/app/orders/page.test.tsx
import { describe, it, expect, vi } from 'vitest';
import OrdersPage from '@/app/orders/page';

vi.mock('@/api/client', () => ({
  railsApi: {
    get: vi.fn().mockResolvedValue([
      { id: '1', status: 'pending', totalAmount: 100 },
    ]),
  },
}));

describe('OrdersPage', () => {
  it('should render orders from API', async () => {
    const page = await OrdersPage();
    expect(page).toBeTruthy();
  });
});
```

## Server Action Test

```tsx
// tests/actions/orders.test.ts
import { describe, it, expect, vi } from 'vitest';
import { createOrder } from '@/actions/orders';

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }));
vi.mock('next/navigation', () => ({ redirect: vi.fn() }));
vi.mock('@/api/client', () => ({
  railsApi: { post: vi.fn().mockResolvedValue({ id: '1' }) },
}));

describe('createOrder', () => {
  it('should return validation errors for invalid input', async () => {
    const formData = new FormData();
    const result = await createOrder(null, formData);
    expect(result?.errors).toBeDefined();
    expect(result?.errors?.customerName).toBeDefined();
  });

  it('should create order and revalidate on valid input', async () => {
    const formData = new FormData();
    formData.set('customerName', 'Jane Doe');
    formData.set('email', 'jane@example.com');
    formData.set('items', JSON.stringify([{ productId: 'p1', quantity: 2 }]));

    await createOrder(null, formData);
  });
});
```
