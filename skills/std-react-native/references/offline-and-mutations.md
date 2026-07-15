# Offline & Mutations — the queue that survives a cold start

Load-bearing rules restated (hold even if you read nothing else):

1. **A phone is offline by default and online by luck.** Offline is not an error path; it is a
   normal state the UI must have an answer for.
2. **`setMutationDefaults` must run before hydration, at module/app scope** — not in the screen
   that fires the mutation. Functions are not serializable, so a persisted mutation resumes with
   **no `mutationFn`** unless a default is already registered.
3. **A mutation you retry must be idempotent**, because "retried on reconnect" means the server
   may see it twice.

---

## Why this file exists

`SKILL.md` says *"queue mutations when offline, replay on reconnect"*. That sentence hides the
only part that is hard. Queuing is free — TanStack Query pauses mutations when offline and
retries them, in order, on reconnect, with no code from you. **Surviving the app being killed is
not free**, and that is the case that actually happens on a phone: the user submits, backgrounds
the app, iOS reclaims it, they reopen it an hour later.

The failure is specific and documented:

> *"When persisting to an external storage, only the state of mutations is persisted, as
> functions cannot be serialized."* … after a reload *"the component that triggers the mutation
> might not be mounted, so calling `resumePausedMutations` might yield an error:
> `No mutationFn found`."*

So the queue survives and the **code to execute it does not**. You get a persisted mutation that
can never run, and the user's order silently never happens.

## Decision: what does this mutation need?

| Situation | What you need | Cost |
|---|---|---|
| Fire-and-forget while the app stays open | Nothing — Query pauses and retries | free |
| Must survive app kill / cold start | Persister **+** `setMutationDefaults` at app scope | real |
| Must never double-charge | The above **+** a server-side idempotency key | real |
| Read-only screen | A persisted **query** cache, no mutation work | small |

Do not reach for persisted mutations everywhere. They are for writes the user believes
succeeded — an order, a message, a like. A search filter does not need to survive a cold start.

## Wiring — online status must come from the device

React Query does not know what a phone knows. Give it NetInfo, once, at app scope:

```ts
// src/lib/query-client.ts  ✅
import NetInfo from '@react-native-community/netinfo';
import { onlineManager, QueryClient } from '@tanstack/react-query';
import { MMKV } from 'react-native-mmkv';

// Without this, Query uses a browser-shaped assumption about connectivity and will happily
// fire mutations into a dead radio instead of pausing them.
onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((state) => {
    setOnline(!!state.isConnected);
  }),
);

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 60_000, retry: 3 },
    mutations: { retry: 3 },
  },
});

const storage = new MMKV({ id: 'query-cache' });

export const persister = {
  persistClient: async (client: unknown) =>
    storage.set('react-query', JSON.stringify(client)),
  restoreClient: async () => {
    const raw = storage.getString('react-query');
    return raw ? JSON.parse(raw) : undefined;
  },
  removeClient: async () => storage.delete('react-query'),
};
```

## Bad — the mutation is registered where it is used

```tsx
// src/screens/NewOrder.tsx  ❌
export function NewOrder() {
  const { mutate } = useMutation({
    mutationKey: ['createOrder'],
    // This function lives on this component. Persist the cache, kill the app, reopen on the
    // Home screen: this file never mounts, so the mutationFn does not exist, and the resumed
    // mutation dies with "No mutationFn found". The user saw a success toast an hour ago.
    mutationFn: (body: OrderBody) => api.post('/orders', body).then((r) => r.data),
  });

  return <Button title="Place order" onPress={() => mutate(body)} />;
}
```

It works perfectly in every test where the app stays open. That is why it ships.

## Good — defaults at app scope, screen only fires it

```ts
// src/lib/mutation-defaults.ts  ✅ imported for side effects in App.tsx, before render
import { queryClient } from './query-client';
import { api } from '@/api/client';
import type { OrderBody } from '@/domain/order';

// Registered at MODULE scope, so it exists no matter which screen is mounted when a
// persisted mutation resumes. This is the whole trick.
queryClient.setMutationDefaults(['createOrder'], {
  mutationFn: (body: OrderBody) => api.post('/orders', body).then((r) => r.data),
});
```

```tsx
// src/App.tsx  ✅
import '@/lib/mutation-defaults';   // side-effect import: defaults BEFORE hydration
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { onlineManager } from '@tanstack/react-query';
import { persister, queryClient } from '@/lib/query-client';

export default function App() {
  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister, maxAge: 24 * 60 * 60 * 1000 }}
      // Fires after the cache is rehydrated. Resuming before hydration finishes would
      // replay against an empty cache.
      onSuccess={() => {
        if (onlineManager.isOnline()) queryClient.resumePausedMutations();
      }}
    >
      <RootNavigator />
    </PersistQueryClientProvider>
  );
}
```

```tsx
// src/screens/NewOrder.tsx  ✅ the screen supplies the key, never the function
export function NewOrder() {
  const { mutate, isPending } = useMutation({ mutationKey: ['createOrder'] });
  return <Button title="Place order" disabled={isPending} onPress={() => mutate(body)} />;
}
```

## Idempotency is the server's half, and it is not optional

"Retried in the same order on reconnect" also means *"the server may receive this twice"* — the
first attempt can succeed and the response can be lost. Retry alone turns one order into two.

```ts
// src/lib/mutation-defaults.ts  ✅
import 'react-native-get-random-values';
import { v4 as uuid } from 'uuid';

queryClient.setMutationDefaults(['createOrder'], {
  mutationFn: (body: OrderBody & { requestId: string }) =>
    api.post('/orders', body, {
      // The key is generated ONCE at submit time and persisted with the mutation, so every
      // retry — including one an hour later after a cold start — carries the SAME key.
      // Generating it inside mutationFn would defeat the entire mechanism.
      headers: { 'Idempotency-Key': body.requestId },
    }).then((r) => r.data),
});
```

```tsx
mutate({ ...body, requestId: uuid() });   // ✅ once, at the call site
```

The Rails side must honour it: store the key, return the original response on a repeat. That is
the API's contract, not the client's — see `../std-api-design/references/errors-rails.md` for
the error envelope those retries will parse.

## Optimistic updates that survive a failure

```ts
queryClient.setMutationDefaults(['toggleLike'], {
  mutationFn: ({ postId, liked }: { postId: string; liked: boolean }) =>
    api.post(`/posts/${postId}/like`, { liked }).then((r) => r.data),

  onMutate: async ({ postId, liked }) => {
    // Cancel in-flight refetches, or one can land after this and overwrite the optimism.
    await queryClient.cancelQueries({ queryKey: ['posts', postId] });
    const previous = queryClient.getQueryData(['posts', postId]);
    queryClient.setQueryData(['posts', postId], (old: Post) => ({ ...old, liked }));
    return { previous };     // <- rollback handle
  },
  onError: (_err, { postId }, context) => {
    queryClient.setQueryData(['posts', postId], context?.previous);
  },
  onSettled: (_data, _err, { postId }) => {
    queryClient.invalidateQueries({ queryKey: ['posts', postId] });
  },
});
```

Offline, `onMutate` runs immediately and the mutation pauses — so the UI is optimistic now and
reconciles on reconnect, which is exactly what a user expects from a phone.

## Tell the user the truth

An offline queue that looks identical to a successful write teaches users to distrust the app
the first time something is lost.

```tsx
// ✅ paused !== failed, and it must not read as either "sent" or "error"
const isOffline = !useOnlineManager();
const pending = useIsMutating({ mutationKey: ['createOrder'] });

{isOffline && pending > 0 && <Banner>Saved — will send when you're back online</Banner>}
```

Persist client state (drafts, filters) in a separate MMKV store from the Query cache; server
data has an owner and a TTL, client intent does not. See `SKILL.md` for the Zustand split.
