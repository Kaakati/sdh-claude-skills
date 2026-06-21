---
# Wrapper-agnostic: React Native detected by config markers + distinctive dirs.
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
- Subscribe in custom hooks: `useCentrifugoChannel('chat:${roomId}')`
- Unsubscribe on component unmount — always clean up
- Update TanStack Query cache on real-time events (don't duplicate state)
- Use presence channels for online status features
- Handle reconnection gracefully — show connection status to user

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
- Queue mutations when offline, replay on reconnect
- Show clear offline indicators in UI

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
- Export types alongside components
