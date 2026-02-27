# React Native Patterns Library

## Screen Component Pattern
```typescript
// src/screens/OrdersScreen.tsx
import React, { useCallback } from 'react';
import { FlatList, RefreshControl, View } from 'react-native';
import { useOrders } from '@/hooks/queries/useOrders';
import { OrderCard } from '@/components/features/OrderCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ErrorView } from '@/components/common/ErrorView';
import { EmptyState } from '@/components/common/EmptyState';
import { styles } from './OrdersScreen.styles';

export const OrdersScreen = () => {
  const { data, isLoading, isError, error, refetch, isRefetching } = useOrders({
    status: 'active',
  });

  const renderItem = useCallback(
    ({ item }: { item: Order }) => <OrderCard order={item} />,
    []
  );

  const keyExtractor = useCallback((item: Order) => item.id, []);

  if (isLoading) return <LoadingSpinner />;
  if (isError) return <ErrorView error={error} onRetry={refetch} />;
  if (!data?.length) return <EmptyState message="No orders yet" />;

  return (
    <View style={styles.container}>
      <FlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} />
        }
        contentContainerStyle={styles.list}
      />
    </View>
  );
};
```

## Zustand Store with MMKV Persistence
```typescript
// src/stores/useAuthStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

const mmkvStorage = createJSONStorage(() => ({
  getItem: (name: string) => storage.getString(name) ?? null,
  setItem: (name: string, value: string) => storage.set(name, value),
  removeItem: (name: string) => storage.delete(name),
}));

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}

interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: async (credentials) => {
        const response = await api.auth.login(credentials);
        set({
          token: response.token,
          user: response.user,
          isAuthenticated: true,
        });
      },

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false });
        queryClient.clear();
      },

      setToken: (token) => set({ token }),
    }),
    {
      name: 'auth-storage',
      storage: mmkvStorage,
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

## TanStack Query Hook with Pagination
```typescript
// src/hooks/queries/useOrders.ts
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filter: OrderFilter) => [...orderKeys.lists(), filter] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
};

export const useOrders = (filter: OrderFilter) =>
  useInfiniteQuery({
    queryKey: orderKeys.list(filter),
    queryFn: ({ pageParam }) =>
      api.orders.list({ ...filter, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.meta.nextCursor,
    staleTime: 60_000,
    select: (data) => data.pages.flatMap((page) => page.data),
  });

export const useOrder = (id: string) =>
  useQuery({
    queryKey: orderKeys.detail(id),
    queryFn: () => api.orders.get(id),
    staleTime: 5 * 60_000,
  });

export const useCreateOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.orders.create,
    onSuccess: (newOrder) => {
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      queryClient.setQueryData(orderKeys.detail(newOrder.id), newOrder);
    },
  });
};
```

## Centrifugo Real-time Hook
```typescript
// src/hooks/realtime/useLiveLocation.ts
import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { centrifuge } from '@/services/centrifugo';
import type { Subscription } from 'centrifuge';

export const useLiveLocation = (vehicleId: string) => {
  const queryClient = useQueryClient();
  const subRef = useRef<Subscription | null>(null);

  useEffect(() => {
    const sub = centrifuge.newSubscription(`location:vehicle:${vehicleId}`);

    sub.on('publication', (ctx) => {
      const locationUpdate = ctx.data as LocationUpdate;

      // Update the TanStack Query cache directly
      queryClient.setQueryData(
        ['vehicles', vehicleId, 'location'],
        locationUpdate
      );
    });

    sub.on('error', (err) => {
      console.warn(`Location subscription error for ${vehicleId}:`, err);
    });

    sub.subscribe();
    subRef.current = sub;

    return () => {
      sub.unsubscribe();
      subRef.current = null;
    };
  }, [vehicleId, queryClient]);
};
```

## API Client with Auth Interceptor
```typescript
// src/services/api.ts
import axios from 'axios';
import { useAuthStore } from '@/stores/useAuthStore';
import Config from 'react-native-config';

const client = axios.create({
  baseURL: Config.API_URL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — attach auth token
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

export const api = {
  orders: {
    list: (params: OrderFilter) =>
      client.get('/api/v1/orders', { params }).then((r) => r.data),
    get: (id: string) =>
      client.get(`/api/v1/orders/${id}`).then((r) => r.data),
    create: (data: CreateOrderInput) =>
      client.post('/api/v1/orders', { order: data }).then((r) => r.data),
  },
  // ... other endpoints
};
```

## Map with PostGIS Spatial Query
```typescript
// src/screens/MapScreen.tsx
import React, { useCallback, useRef, useState } from 'react';
import MapView, { Marker, Region } from 'react-native-maps';
import { useNearbyLocations } from '@/hooks/queries/useNearbyLocations';
import { debounce } from '@/utils/debounce';

export const MapScreen = () => {
  const mapRef = useRef<MapView>(null);
  const [region, setRegion] = useState<Region>(DEFAULT_REGION);

  const { data: locations } = useNearbyLocations({
    lat: region.latitude,
    lng: region.longitude,
    radiusKm: calculateRadiusFromDelta(region.latitudeDelta),
  });

  const handleRegionChange = useCallback(
    debounce((newRegion: Region) => {
      setRegion(newRegion);
    }, 500),
    []
  );

  return (
    <MapView
      ref={mapRef}
      style={{ flex: 1 }}
      initialRegion={DEFAULT_REGION}
      onRegionChangeComplete={handleRegionChange}
    >
      {locations?.map((loc) => (
        <Marker
          key={loc.id}
          coordinate={{ latitude: loc.lat, longitude: loc.lng }}
          title={loc.name}
        />
      ))}
    </MapView>
  );
};
```

## Form with react-hook-form + Zod
```typescript
// src/screens/CreateOrderScreen.tsx
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const orderSchema = z.object({
  customerName: z.string().min(2, 'Name must be at least 2 characters'),
  address: z.string().min(5, 'Please enter a valid address'),
  items: z.array(z.object({
    productId: z.string(),
    quantity: z.number().min(1).max(99),
  })).min(1, 'At least one item required'),
});

type OrderFormData = z.infer<typeof orderSchema>;

export const CreateOrderScreen = () => {
  const { control, handleSubmit, formState: { errors } } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
  });
  const createOrder = useCreateOrder();

  const onSubmit = (data: OrderFormData) => {
    createOrder.mutate(data, {
      onSuccess: () => navigation.goBack(),
    });
  };

  return (
    <ScrollView>
      <Controller
        control={control}
        name="customerName"
        render={({ field: { onChange, value } }) => (
          <TextInput
            label="Customer Name"
            value={value}
            onChangeText={onChange}
            error={errors.customerName?.message}
          />
        )}
      />
      {/* ... more fields */}
      <Button onPress={handleSubmit(onSubmit)} loading={createOrder.isPending}>
        Create Order
      </Button>
    </ScrollView>
  );
};
```
