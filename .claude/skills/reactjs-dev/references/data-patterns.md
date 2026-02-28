# ReactJS (Vite SPA) — Data Patterns

## Zustand Store with localStorage Persistence

```typescript
// web/src/stores/ui-preferences.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIPreferencesState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIPreferences = create<UIPreferencesState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'system',
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'ui-preferences' },
  ),
);
```

## React Router Configuration

```tsx
// web/src/router/index.tsx
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AppLayout } from '../components/AppLayout';
import { AuthGuard } from '../components/AuthGuard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

const Dashboard = lazy(() => import('../pages/Dashboard'));
const Orders = lazy(() => import('../pages/Orders'));
const OrderDetail = lazy(() => import('../pages/OrderDetail'));
const Login = lazy(() => import('../pages/Login'));
const NotFound = lazy(() => import('../pages/NotFound'));

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingSpinner />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <SuspenseWrapper><Login /></SuspenseWrapper>,
  },
  {
    path: '/',
    element: <AuthGuard><AppLayout /></AuthGuard>,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <SuspenseWrapper><Dashboard /></SuspenseWrapper> },
      { path: 'orders', element: <SuspenseWrapper><Orders /></SuspenseWrapper> },
      { path: 'orders/:id', element: <SuspenseWrapper><OrderDetail /></SuspenseWrapper> },
    ],
  },
  { path: '*', element: <SuspenseWrapper><NotFound /></SuspenseWrapper> },
]);
```

## API Client with Interceptors

```typescript
// web/src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);
```

## Vitest Component Test

```tsx
// web/src/components/OrderTable.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { OrderTable } from './OrderTable';
import { createTestOrder } from '../../tests/factories';

describe('OrderTable', () => {
  it('should render order rows when orders are provided', () => {
    const orders = [createTestOrder({ id: '1', status: 'pending' })];

    render(<OrderTable orders={orders} isLoading={false} error={null} />);

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('should show loading skeleton when isLoading is true', () => {
    render(<OrderTable orders={[]} isLoading={true} error={null} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should show empty state when no orders exist', () => {
    render(<OrderTable orders={[]} isLoading={false} error={null} />);

    expect(screen.getByText(/no orders/i)).toBeInTheDocument();
  });
});
```

## TanStack Query Hook Test with MSW

```typescript
// web/src/api/__tests__/orders.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../tests/msw-server';
import { useOrders } from '../orders';
import { createQueryWrapper } from '../../tests/utils';

describe('useOrders', () => {
  it('should fetch orders from the API', async () => {
    server.use(
      http.get('*/api/v1/orders', () => {
        return HttpResponse.json([
          { id: '1', status: 'pending', totalAmount: 100 },
        ]);
      }),
    );

    const { result } = renderHook(() => useOrders(), { wrapper: createQueryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].status).toBe('pending');
  });
});
```
