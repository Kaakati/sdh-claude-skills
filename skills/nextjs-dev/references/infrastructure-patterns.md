# Next.js App Router — Infrastructure Patterns

## Root Layout with Providers

The root layout owns three things every page depends on: the locale on `<html>`, the next-themes
provider, and the base's `<Toaster />`, mounted once.

```tsx
// next/app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { getLocale } from 'next-intl/server';
import { Providers } from '@/components/Providers';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/sonner'; // Radix package. Base UI: import { Toaster } from '@/components/ui/toast'
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: { default: 'MyApp', template: '%s | MyApp' },
  description: 'Enterprise application',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();

  return (
    // next-themes sets the `dark` class before hydration; the suppression covers this element only
    <html lang={locale} className={inter.className} suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <Providers>{children}</Providers>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
```

```tsx
// next/src/components/theme-provider.tsx
'use client';

import { ThemeProvider as NextThemesProvider } from 'next-themes';
import type { ComponentProps } from 'react';

export function ThemeProvider(props: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props} />;
}
```

- **`attribute="class"` puts `.dark` on `<html>`, and nothing follows it without the variant.**
  Tailwind v4's `dark:` defaults to the `prefers-color-scheme` media query; the token CSS's
  `@custom-variant dark (&:is(.dark *))` is what makes it follow the class. The token file →
  `@skills/theming/references/platform-integration.md`.
- **One `<Toaster />`, inside the provider.** sonner's reads `useTheme()` from next-themes, so
  outside the provider it renders in the wrong theme. Which toast: Radix → `add sonner`, Base UI →
  `add toast` — both export `Toaster`, and call sites never import either toast directly; they call
  `notify()` → `@skills/std-shadcn-ui/references/forms-and-feedback.md`.
- **`disableTransitionOnChange`** stops every `transition-*` class from animating at once when the
  theme flips.

## Loading and Error Boundaries

```tsx
// next/app/orders/loading.tsx
import { Skeleton } from '@/components/ui/skeleton';

export default function OrdersLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    </div>
  );
}

// next/app/orders/error.tsx
'use client';

import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';

export default function OrdersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('orders');

  useEffect(() => {
    console.error('orders segment failed', { digest: error.digest }); // log the digest; never show error.message
  }, [error]);

  return (
    <div role="alert" className="flex flex-col items-center justify-center py-12">
      <h2 className="text-xl font-semibold text-foreground">{t('loadFailed')}</h2>
      <Button variant="outline" onClick={reset} className="mt-4">
        {t('retry')}
      </Button>
    </div>
  );
}
```

## Middleware for Auth and Locale

On Next.js 16 this file is `proxy.ts` and the function `proxy`
(`npx @next/codemod@canary middleware-to-proxy .`); 15 has no proxy convention →
`@skills/std-nextjs/references/middleware-seo-deploy.md`.

```typescript
// next/middleware.ts — Next.js 16: next/proxy.ts with `export function proxy`
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
import { revalidatePath } from 'next/cache';
import { createOrder } from '@/actions/orders';

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }));
vi.mock('next/navigation', () => ({ redirect: vi.fn() }));
vi.mock('@/lib/auth', () => ({ requireSession: vi.fn().mockResolvedValue({ id: 'u_42' }) }));
vi.mock('@/api/client', () => ({
  railsApi: { post: vi.fn().mockResolvedValue({ id: '1' }) },
}));

describe('createOrder', () => {
  it('should return the schema error keys when the input is invalid', async () => {
    // Arrange
    const formData = new FormData();
    formData.set('customerName', '');
    formData.set('email', 'not-an-email');

    // Act
    const result = await createOrder(null, formData);

    // Assert — the same keys the form's FieldError translates
    expect(result).toMatchObject({
      ok: false,
      fieldErrors: {
        customerName: ['orders.errors.customerNameRequired'],
        email: ['orders.errors.emailInvalid'],
      },
    });
  });

  it('should revalidate the orders list when the input is valid', async () => {
    // Arrange
    const formData = new FormData();
    formData.set('customerName', 'Jane Doe');
    formData.set('email', 'jane@example.com');

    // Act
    await createOrder(null, formData);

    // Assert
    expect(revalidatePath).toHaveBeenCalledWith('/orders');
  });
});
```
