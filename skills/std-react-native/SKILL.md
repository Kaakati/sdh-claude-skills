---
name: std-react-native
description: React Native conventions — Zustand, TanStack Query, Centrifugo, MMKV, navigation. Use when building React Native mobile screens, hooks, or stores.
paths:
  - "**/metro.config.*"
  - "**/app.json"
  - "**/src/screens/**/*.ts"
  - "**/src/screens/**/*.tsx"
  - "**/src/navigation/**/*.ts"
  - "**/src/navigation/**/*.tsx"
---

# React Native Conventions

## Component Architecture
- Functional components with hooks — no class components
- One component per file, file name matches component name (PascalCase)
- Component structure: types/interfaces → component → styles → export
- Keep components under 200 lines — extract sub-components when needed
- Use `React.memo()` for list items and expensive renders

## State Management (Zustand)
- Use Zustand for all shared/global state — no Redux, no Context for state
- One store per domain: `useAuthStore`, `useLocationStore`, `useCartStore`
- Keep stores flat — avoid deeply nested state
- Use selectors to prevent unnecessary re-renders: `const name = useUserStore(s => s.name)`
- Separate actions from state:
  ```typescript
  interface AuthStore {
    user: User | null;
    token: string | null;
    // Actions
    login: (credentials: Credentials) => Promise<void>;
    logout: () => void;
  }
  ```
- Use `persist` middleware with MMKV for offline-capable stores
- Never put server-fetched data in Zustand — that belongs in TanStack Query

## Data Fetching (TanStack Query / React Query)
- Use TanStack Query for ALL server state — never fetch in useEffect
- Define query keys consistently: `['users', userId]`, `['posts', { page, filter }]`
- Extract custom hooks: `useUser(id)`, `usePosts(filter)`
- Configure stale times per query type:
  - User profile: 5 minutes
  - Lists: 1 minute
  - Real-time data: 0 (always refetch)
- Use `useMutation` for all write operations with `onSuccess` invalidation
- Use `useInfiniteQuery` for paginated lists
- Configure `retry: 3` for network resilience on mobile
- Example:
  ```typescript
  const useUser = (id: string) =>
    useQuery({
      queryKey: ['users', id],
      queryFn: () => api.getUser(id),
      staleTime: 5 * 60 * 1000,
    });
  ```

## Real-time (Centrifugal / Centrifugo)
- Use Centrifugo client SDK for real-time subscriptions
- **One `Centrifuge` client for the app**, created once at module scope — not per screen
- **`getSubscription(channel) ?? newSubscription(channel)`** — `newSubscription` *throws* if the
  channel is already in the client's registry, which is exactly what a remounting screen does
- Subscribe in custom hooks: `useChannel('chat:${roomId}')`
- Clean up on unmount by removing **your** handler — `unsubscribe()` does not remove listeners,
  so remounts stack handlers and each message is processed N times
- **An event updates the TanStack Query cache; it never becomes a second copy of the data.**
  Full entity on the wire → `setQueryData`; partial or "something changed" → `invalidateQueries`
- **Invalidate on reconnect** — the socket does not backfill what it missed while down
- Mint the connection token on the Rails side and wire `getToken` (not a static `token`), or the
  socket dies silently when it expires
- Use presence channels for online status — presence is ephemeral client state, not Query state
- Deep guide → `references/realtime-centrifugo.md`

## Navigation
- Use React Navigation (or Expo Router if using Expo)
- Type-safe navigation with typed param lists
- Deep linking configuration for push notifications
- Keep navigation structure flat — max 3 levels of nesting

## Styling
- Use StyleSheet.create for all styles — no inline style objects
- Design tokens: define colors, spacing, typography in a theme file
- Responsive: use `Dimensions` or `useWindowDimensions` for adaptive layouts
- Support dark mode via theme context

## Performance
- Use `FlatList` (never `ScrollView`) for lists > 20 items
- Set `keyExtractor` and `getItemLayout` for FlatList optimization
- Use `react-native-fast-image` for cached image loading
- Avoid anonymous functions in render — use `useCallback`
- Profile with Flipper and React DevTools

## Offline Support
- Persist critical Zustand stores with MMKV
- TanStack Query `persister` for caching API responses offline
- **Feed `onlineManager` from NetInfo** — Query cannot tell a dead radio from a slow server
- Queue mutations when offline, replay on reconnect. **Register `queryClient.setMutationDefaults`
  at app/module scope, not in the screen**: only mutation *state* is persisted (functions are not
  serializable), so after an app kill the resumed mutation has no `mutationFn` and dies with
  `No mutationFn found` — the user saw a success toast an hour ago
- **A retried mutation must be idempotent** — generate the `Idempotency-Key` once at the call
  site so every replay carries the same one; "replayed on reconnect" means the server may see it
  twice
- Show clear offline indicators — a queued write must not look identical to a sent one
- Deep guide → `references/offline-and-mutations.md`

## Libraries — Prefer Community Packages
- Navigation: `@react-navigation/native`
- Storage: `react-native-mmkv` (faster than AsyncStorage)
- Images: `react-native-fast-image`
- Maps: `react-native-maps` (with PostGIS backend)
- Push notifications: `@react-native-firebase/messaging`
- Forms: `react-hook-form` with `zod` validation
- Animations: `react-native-reanimated`
- Gestures: `react-native-gesture-handler`
- Icons: `react-native-vector-icons` or `expo-icons`
- HTTP: `axios` with interceptors for auth tokens
- Date/time: `date-fns` (tree-shakeable) over `moment`
- Geolocation: `react-native-geolocation-service`

## TypeScript
- Strict mode enabled — no `any` types
- Define interfaces for all API responses, props, and store state
- Use discriminated unions for state machines (loading | success | error)

## Deep guides (read on demand, do not preload)

- NetInfo → `onlineManager`, persisting the cache to MMKV, `setMutationDefaults` at app scope,
  idempotency keys that survive a cold start, optimistic updates with rollback
  → `references/offline-and-mutations.md`
- One Centrifuge client, the `getSubscription ?? newSubscription` rule, handler cleanup,
  `setQueryData` vs `invalidateQueries`, reconnect backfill, presence
  → `references/realtime-centrifugo.md`

Related, owned elsewhere — do not duplicate: list/render/animation performance rules live in the
`react-native-best-practices` skill (38 rule files); axios token-refresh interceptors live in
`../react-native-dev/references/react-native-patterns.md`.
- Export types alongside components
