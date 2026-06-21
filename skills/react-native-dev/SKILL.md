---
name: react-native-dev
description: Build React Native mobile features with Zustand state management, TanStack Query data fetching, and Centrifugo real-time subscriptions. Use this skill whenever someone asks to build a mobile screen, create a component, add a Zustand store, write a TanStack Query hook, or says things like "build the mobile UI for X", "create a screen for Y", "add real-time updates", "implement offline support", "set up navigation for X", or "how should I structure this component". Also trigger when someone mentions React Native performance, MMKV storage, map integration, or push notification implementation.
model: sonnet
allowed-tools: Read, Grep, Glob, Write, Edit
---

# React Native Developer

## Purpose
Build mobile features using our React Native stack: Zustand for state, TanStack Query for server data, Centrifugo for real-time, and community libraries over custom code.

## Development Protocol

### 1. Understand the Feature
- Which screens are involved?
- What data comes from the API vs local state?
- Is real-time needed? (Centrifugo subscription)
- Does it need offline support? (Zustand persist + TanStack cache)

### 2. API Layer (TanStack Query)
- Define query keys: `['orders', orderId]`, `['orders', { status, page }]`
- Create custom hooks in `mobile/src/hooks/queries/`:
  ```typescript
  export const useOrders = (filter: OrderFilter) =>
    useQuery({
      queryKey: ['orders', filter],
      queryFn: () => api.orders.list(filter),
      staleTime: 60_000,
    });

  export const useCreateOrder = () =>
    useMutation({
      mutationFn: api.orders.create,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['orders'] });
      },
    });
  ```

### 3. State Management (Zustand)
- Only for CLIENT state — auth, UI preferences, offline queues, navigation state
- Never duplicate server data in Zustand (that's TanStack Query's job)
- Create stores in `mobile/src/stores/`:
  ```typescript
  export const useAuthStore = create<AuthStore>()(
    persist(
      (set) => ({
        token: null,
        user: null,
        login: async (credentials) => { /* ... */ },
        logout: () => set({ token: null, user: null }),
      }),
      { name: 'auth-store', storage: createMMKVStorage() }
    )
  );
  ```

### 4. Component Structure
```
mobile/src/
├── screens/           # Full screen components (connected to navigation)
├── components/
│   ├── common/        # Reusable: Button, Input, Card, Avatar
│   └── features/      # Feature-specific: OrderCard, MapMarker
├── hooks/
│   ├── queries/       # TanStack Query hooks
│   ├── mutations/     # TanStack Mutation hooks
│   └── realtime/      # Centrifugo subscription hooks
├── stores/            # Zustand stores
├── services/          # API client, Centrifugo client
├── navigation/        # React Navigation config
├── theme/             # Colors, spacing, typography
└── utils/             # Helpers, formatters
```

### 5. Real-time (Centrifugo)
- Subscribe in custom hooks:
  ```typescript
  export const useChatMessages = (roomId: string) => {
    const queryClient = useQueryClient();

    useEffect(() => {
      const sub = centrifuge.subscribe(`chat:${roomId}`);
      sub.on('publication', (ctx) => {
        queryClient.setQueryData(
          ['messages', roomId],
          (old: Message[]) => [...(old || []), ctx.data]
        );
      });
      return () => sub.unsubscribe();
    }, [roomId]);

    return useQuery({
      queryKey: ['messages', roomId],
      queryFn: () => api.messages.list(roomId),
    });
  };
  ```

### 6. Maps & Geospatial (PostGIS Backend)
- Use `react-native-maps` with markers from PostGIS spatial queries
- Debounce map region changes before API calls
- Cluster markers for performance: `react-native-map-clustering`
- Send viewport bounds to API for efficient spatial queries

## Key Libraries Reference

| Need | Library | Notes |
|------|---------|-------|
| State | `zustand` + `react-native-mmkv` | Persist with MMKV |
| Server data | `@tanstack/react-query` | Never useEffect for fetching |
| Forms | `react-hook-form` + `zod` | Schema validation |
| Navigation | `@react-navigation/native` | Type-safe params |
| Maps | `react-native-maps` | + clustering |
| Images | `react-native-fast-image` | Cached loading |
| Animations | `react-native-reanimated` | 60fps |
| HTTP | `axios` | Interceptors for auth |
| Storage | `react-native-mmkv` | Fastest local storage |
| Dates | `date-fns` | Tree-shakeable |
| Push | `@react-native-firebase/messaging` | FCM |
| Location | `react-native-geolocation-service` | Background tracking |

See references/react-native-patterns.md for component and hook patterns.
