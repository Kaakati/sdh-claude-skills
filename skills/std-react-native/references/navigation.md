# React Native navigation — area tabs, a stack per tab, a path per level

Load-bearing rules restated (hold even if you read nothing else):

1. **Three navigators, never more: a root stack → bottom tabs, one per area → one native stack per
   tab.** That caps *navigator nesting*. *Screen depth* is a separate limit set by the drill-down
   levels: inside a tab, overview → list → detail → sub-detail, and nothing below sub-detail is a
   screen.
2. **Tabs are areas, composed from `visibleNav` once `['me']` has data** — 3–5 including Account.
   Never a drawer, and never a "Menu" button: the labelled Menu button is the phone-width *web*
   pattern.
3. **Every screen has a linking path that mirrors the nesting and matches the web URL.** Details are
   flat by ID. A path the role cannot open resolves to the no-access screen.
4. **Back pops the area's stack, and the stack keeps the list mounted beneath the detail.** Params,
   scroll and cache survive with no restoration code. A filter change is `setParams`, never a push.
5. **After a push, the screen reader lands on the new screen.** Verify it with VoiceOver and TalkBack
   per level; send focus yourself only where that pass fails.
6. **Test the rendered shell once per role:** tab names, order and count; a deep link per level; no
   access for a path the role lacks.

**Owned elsewhere — pointed at, never restated:**

| Topic | Owner |
|---|---|
| Levels, location cues, Up vs Back, budgets, list state, focus rules, anti-patterns | `@skills/ui-ux-patterns/references/drill-down-navigation.md` |
| Endpoints per level, flat member URLs, `ancestors`, list parameters, invalidation, search | `@skills/std-api-design/references/drill-down-resources.md` |
| `/me`, CASL, `allows`, `NAV`, `visibleNav`, the `MainTabs` sketch, the `me-by-role` fixture | `@skills/access-control-designer/references/ui-gates.md` |
| Nav order per role, derived landing, locked areas | `@skills/ui-ux-patterns/references/role-based-ux.md` |
| No access vs not found | `@skills/ui-ux-patterns/references/role-based-ux-states.md` |
| The key factory; cursor lists on a `FlatList` | `@skills/std-reactjs/references/data-fetching.md`; `@skills/std-api-design/references/pagination-clients.md` |
| Jest + RNTL, MSW, the shared Jest setup | `@skills/std-testing/references/react-native.md` |
| Native vs JS navigators | the `react-native-best-practices` skill, rule `navigation-native-navigators` |
| Touch-target numbers | the `std-accessibility` skill |

Option names, defaults, `sendAccessibilityEvent` and the experimental
`UNSTABLE_routeNamesChangeBehavior` were checked against the React Navigation 7.x and React Native
0.87 docs on 2026-09-11. Re-check them on the versions the project pins.

---

## Why this file exists

`SKILL.md` used to cap navigation nesting at three levels without saying what it counted. Counted as
navigators, the house shape is already three, and a top-tab navigator inside a stack "passes" if the
root counts as zero. Counted as screens, an overview above list → detail → sub-detail "fails". The
two limits differ, so this file states both. Linking, likewise, is not only "for push
notifications": it addresses every level, and a notification is one caller.

## Decision: which navigator shape?

| Shape | What people get | Verdict |
|---|---|---|
| **A native stack inside each tab** | The tab bar stays visible while drilling; each tab keeps its history | **The house shape** |
| Tabs inside a stack | Every pushed screen covers the tab bar | Only for flows above the tabs: sign-in, a full-screen create flow |
| A drawer switching areas | Areas behind a menu | Never: "The navigation drawer is being deprecated. Use the expanded navigation rail instead" (Material Components for Android — Navigation drawers) |
| Hub-and-spoke between areas | Changing area means going back to a hub | Never for areas (Nielsen Norman Group — Basic Patterns for Mobile Navigation) |
| Top tabs nested in a stack | A fourth navigator | Never; sections use the switcher below |

React Navigation supports both of the first two; the house picks stack-in-tabs so primary navigation
stays visible. "Think of nesting as a way to achieve the UI you want, not a way to organize your
code", and excessive nesting costs performance (React Navigation — Nesting navigators).

```text
RootStack                           navigator 1 · UNSTABLE_routeNamesChangeBehavior="lastUnhandled"
├── SignIn / Loading                signed out / signed in before ['me'] arrives
├── Main → MainTabs                 navigator 2 · one tab per visible area, then Account
│   ├── orders → OrdersStack        navigator 3 · one collection, so OrderList is seeded beneath deep links
│   │   ├── OrderList       L3      orders?status=late
│   │   ├── OrderDetail     L4      orders/:orderId/:tab?   (Lines · Shipments are a param)
│   │   └── ShipmentDetail  L5      shipments/:shipmentId   (flat, like the API)
│   ├── approvals → ApprovalsStack
│   ├── organization → OrganizationStack    MemberList · MemberDetail · Billing (two sections)
│   └── account → AccountStack
├── NewOrder                        a linear flow above the tabs: no tab bar, no nav links
├── NoAccess                        no-access
└── NotFound                        *
```

**Screen depth.** The area is the tab, never a screen. Its stack holds an optional overview (the
section hub, below), the list, the detail — whose sub-collections are a `tab` param switched with
`setParams` — and the sub-detail. Anything deeper is a row, a section or a param.

## Decision: how many tabs, and which?

Count what one role sees after `visibleNav`, never the config.

| Areas the role sees | Tab bar |
|---|---|
| 0 | Account only — a navigator with no screens throws. What the empty product says is `role-based-ux-states.md`'s |
| 1 | The area and Account. Two tabs sits below the floor on purpose: the area's section switcher is that role's primary nav |
| 2–4 | One tab per area in the role's canonical order, then Account |
| 5 or more | Over budget: a design review, not a block. If the areas stay, four take tabs and the fifth slot is **More**, a visible list of the rest and Account |

"Three to five destinations of equal importance" (Android Developers — Navigation bar); a bar
struggles past five (Nielsen Norman Group — Basic Patterns for Mobile Navigation); Apple sets no cap
but says never to hide or disable tabs (Apple Human Interface Guidelines — Tab bars).

- **Compose, never toggle.** A never-permitted area is never registered, and the set changes only
  when `['me']` does (a role change arrives through the realtime `version` bump in `ui-gates.md`). A
  plan-locked area (`locked`) keeps its tab and renders the locked state at its root.
- **Destinations only, labelled.** "New order" is a header action, never a tab (Apple Human Interface
  Guidelines — Tab bars), and a tab's label is also its accessible name. **Search** sits in each area
  root's header (`headerSearchBarOptions`); a Search tab only when search is a role's top task, since
  it spends one of five slots (Apple Human Interface Guidelines — Search fields).
- **More is the reviewed exception.** Its stack registers the overflow areas' screens itself — flat,
  never an area stack nested inside it — so those screens sit under another tab for that role, and
  the linking map must follow. Prove every overflow path in the per-role test before shipping it.

## The shell — filter first, then build

Register tabs as `ui-gates.md`'s `MainTabs` does, mapping each visible area through `AREA_STACKS`,
but call `useMobileNav()` instead of `visibleNav` directly: an area the app has no screens for then
never becomes a tab, and never counts against the budget.

```ts
// src/navigation/areas.ts — which screens each area registers, from the same visibleNav output as the tabs
// Screen → the section key that gates it; null = registered whenever the area is. In an area with
// sections, gate every screen by a section: visibleNav shows the area when ANY section is permitted.
export const SCREEN_GATES = {
  orders: { OrderList: null, OrderDetail: null, ShipmentDetail: null } satisfies Record<keyof OrdersStackParams, string | null>,
  approvals: { ApprovalList: null } satisfies Record<keyof ApprovalsStackParams, string | null>,
  organization: { MemberList: 'members', MemberDetail: 'members', Billing: 'billing' } satisfies Record<keyof OrganizationStackParams, string | null>,
};
export type AreaKey = keyof typeof SCREEN_GATES;
export type MobileArea = VisibleArea & { key: AreaKey };

export const mobileNav = (ability: AppAbility, entitlements: readonly string[]) =>
  visibleNav(NAV, ability, entitlements).filter((area): area is MobileArea => area.key in SCREEN_GATES);

export const hasScreen = (area: VisibleArea, gate: string | null) =>
  gate === null || area.sections.some(({ key }) => key === gate);

export const sectionScreen = (area: AreaKey, section: string) => // a section's root: the first screen it gates
  Object.entries(SCREEN_GATES[area]).find(([, gate]) => gate === section)?.[0];

const SHELL = ['Main', 'Loading', 'NewOrder', 'NoAccess', 'NotFound', 'account', 'AccountHome'];

export const registeredScreens = (areas: readonly MobileArea[]): ReadonlySet<string> =>
  new Set([...SHELL, ...areas.flatMap((area) => [
    area.key,
    ...Object.entries(SCREEN_GATES[area.key]).filter(([, gate]) => hasScreen(area, gate)).map(([name]) => name),
  ])]);

export function useMobileNav() {
  const ability = useAppAbility(); // @casl/react 7: under the AbilityProvider that wraps MainTabs (ui-gates.md)
  const { data: me } = useQuery(meQuery);
  return useMemo(() => (me ? mobileNav(ability, me.entitlements) : []), [ability, me]);
}
```

```tsx
// src/navigation/OrganizationStack.tsx — a gated screen is registered or absent, never hidden
export type OrganizationStackParams = { MemberList: undefined; MemberDetail: { memberId: string }; Billing: undefined };

const Stack = createNativeStackNavigator<OrganizationStackParams>();
const gates = SCREEN_GATES.organization;

export function OrganizationStack() {
  const area = useMobileNav().find(({ key }) => key === 'organization');
  const { t } = useTranslation();
  if (!area) return null; // MainTabs registers this tab only for a visible area

  // The first registered screen is the root, so a billing-only role lands on Billing, as visibleNav derives
  return (
    <Stack.Navigator>
      {hasScreen(area, gates.MemberList) && <Stack.Screen name="MemberList" component={MemberListScreen} options={{ title: t('nav.members') }} />}
      {hasScreen(area, gates.MemberDetail) && <Stack.Screen name="MemberDetail" component={MemberDetailScreen} />}
      {hasScreen(area, gates.Billing) && <Stack.Screen name="Billing" component={BillingScreen} options={{ title: t('nav.billing') }} />}
    </Stack.Navigator>
  );
}
```

- **Tabs keep their stacks:** `popToTopOnBlur` stays at its default, `false` — tab bars let people
  "quickly switch between sections of the view while preserving the current navigation state within
  each section" (Apple Human Interface Guidelines — Tab bars). Re-tapping the focused tab pops to the
  area root by default; `useScrollToTop(listRef)` scrolls the root list on the same tap.
- **Android Back** keeps `backBehavior` at its default, `firstRoute`: it returns to the first tab — the
  role's landing — before leaving the app (Android Developers — Principles of navigation).
- **These are `@react-navigation/bottom-tabs` 7.x options.** The `navigation-native-navigators` rule
  prefers native bottom tabs: the structure is the same, but check that package's option names and
  tab accessible names before copying the test below. A badge that means something (`tabBarBadge`)
  also goes into `tabBarAccessibilityLabel`.

```tsx
// src/navigation/RootNavigator.tsx — one container for the app's life
const Root = createNativeStackNavigator<RootStackParams>();
const NO_RULES: AppRule[] = []; // a module constant, so the provider's memo holds

export function RootNavigator() {
  const queryClient = useQueryClient();
  const linking = useMemo(() => createLinking(queryClient), [queryClient]); // built once, never changed
  const signedIn = useAuthStore((state) => state.token !== null);
  const { data: me } = useQuery({ ...meQuery, enabled: signedIn });

  return (
    <AbilityProvider rules={me?.permissions.rules ?? NO_RULES}>
      <NavigationContainer linking={linking} fallback={<SplashScreen />}>
        <Root.Navigator UNSTABLE_routeNamesChangeBehavior="lastUnhandled" screenOptions={{ headerShown: false }}>
          {!signedIn && <Root.Screen name="SignIn" component={SignInScreen} />}
          {signedIn && !me && <Root.Screen name="Loading" component={SplashScreen} />}
          {signedIn && me && (
            <>
              <Root.Screen name="Main" component={MainTabs} />
              <Root.Screen name="NewOrder" component={NewOrderScreen} options={{ presentation: 'fullScreenModal' }} />
              <Root.Screen name="NoAccess" component={NoAccessScreen} options={{ headerShown: true }} />
            </>
          )}
          <Root.Screen name="NotFound" component={NotFoundScreen} options={{ headerShown: true }} />
        </Root.Navigator>
      </NavigationContainer>
    </AbilityProvider>
  );
}
```

**One container, screens swapped inside it.** Unmounting the container between sign-in and the shell
drops a pending link; inside one navigator, `lastUnhandled` opens it once its screen is registered —
a deep link beats the landing page (`role-based-ux.md`). React Navigation marks the prop
experimental. Never navigate by hand after sign-in: registering `Main` moves the person there.

## Linking — every level has a path, and the path is the web URL

```ts
// src/navigation/linking.ts
type LinkState = { routes: { name: string; state?: LinkState }[] };
export const routeNames = (state?: LinkState): string[] =>
  state?.routes.flatMap((route) => [route.name, ...routeNames(route.state)]) ?? [];

export const config: LinkingOptions<RootStackParams>['config'] = {
  screens: {
    Main: {
      screens: {
        orders: {
          initialRouteName: 'OrderList', // one collection: every role with this tab has the list
          screens: { OrderList: 'orders', OrderDetail: 'orders/:orderId/:tab?', ShipmentDetail: 'shipments/:shipmentId' },
        },
        approvals: { screens: { ApprovalList: 'approvals' } },
        // Sectioned, so no seed: visibleNav derives this root per role, and a fixed one would name a
        // screen some roles never register.
        organization: { screens: { MemberList: 'members', MemberDetail: 'members/:memberId', Billing: 'billing' } },
        account: { screens: { AccountHome: 'account' } },
      },
    },
    NoAccess: 'no-access',
    NotFound: '*',
  },
};

export function createLinking(queryClient: QueryClient): LinkingOptions<RootStackParams> {
  return {
    prefixes: ['acme://', 'https://app.acme.example'],
    config,
    async getInitialURL() {
      const url = await Linking.getInitialURL();
      // Resolve a cold-start link against real rules: `query` on current TanStack Query, `fetchQuery` before it.
      if (url && useAuthStore.getState().token) await queryClient.query(meQuery).catch(() => undefined);
      return url;
    },
    getStateFromPath(path, options) {
      const state = getStateFromPath(path, options); // the default resolver from @react-navigation/native
      const me = queryClient.getQueryData(meQuery.queryKey);
      if (!state || !me) return state; // signed out, or no rules yet: lastUnhandled replays it after sign-in
      const registered = registeredScreens(mobileNav(buildAbility(me.permissions.rules), me.entitlements));
      const inRole = routeNames(state as LinkState).every((name) => registered.has(name));
      return inRole ? state : getStateFromPath('no-access', options);
    },
  };
}
```

- **The config mirrors the nesting,** one path per screen (React Navigation — Configuring links); a
  parent with no path adds no prefix. Query parameters become params by default, and they are the
  API's list parameters (`drill-down-resources.md`), so `orders?status=late` opens the same list on
  every platform.
- **Seed only one-collection areas.** `initialRouteName` must name a screen every role with the tab
  registers; a sectioned area's root varies by role, so its deep-linked detail relies on the up link.
- **The guard is `getStateFromPath`.** React Navigation documents no outcome for a link to a screen
  the role never registers, so the house sends it to `NoAccess`: a feature the role lacks
  (`role-based-ux-states.md`). A record outside scope differs — its screen opens, the API answers
  404, and the screen renders not-found in place without refetching `['me']` (`ui-gates.md`).
- **A cold start waits for the rules:** `getInitialURL` loads `['me']` first, and `fallback` shows
  meanwhile (hide a native splash in `onReady` instead).
- **One accepted gap:** `lastUnhandled` replays a signed-out link without the guard. If the role
  lacks that screen, nothing opens and the person stays on their landing screen; the per-role test
  pins it.
- **Expo Router** builds this tree from folders and takes paths from file names, so name the files
  after the web URLs. `Stack.Protected` and `Tabs.Protected` gate with `guard`, but a denied route
  redirects to the anchor route instead of no access — decide what a denied deep link shows, and test
  it.

## Headers, Back and Up

- **The header is the location cue:** a title and Back, no breadcrumbs. "People know that the
  standard Back button lets them retrace their steps through a hierarchy of information" (Apple Human
  Interface Guidelines — Toolbars). A record screen sets its title once the record loads.
- **Back pops the area's stack.** Inside the app Up and Back behave the same (Android Developers —
  Principles of navigation), so while drilling the header's back *is* Up. Keep
  `headerBackButtonDisplayMode` at `default` so the button names the parent where there is room.
- **After a deep link, at most the seeded list sits beneath.** "The initialRouteName will add the
  screen to React Navigation's state only", so a web build's browser Back never returns to it (React
  Navigation — Configuring links). A record below its list therefore links to its real parent, built
  from `ancestors`.

```tsx
// src/screens/orders/ShipmentDetailScreen.tsx — excerpt: the title from the record, Up to its real parent
export function ShipmentDetailScreen({ route, navigation }: NativeStackScreenProps<OrdersStackParams, 'ShipmentDetail'>) {
  const { t } = useTranslation();
  const { data: shipment } = useShipment(route.params.shipmentId); // a 404 renders not-found in place
  const order = shipment?.ancestors.find((node) => node.type === 'order'); // permission-filtered by the API

  useLayoutEffect(() => {
    if (shipment) navigation.setOptions({ title: shipment.name });
  }, [navigation, shipment]);

  const openOrder = () => {
    if (!order) return;
    const { routes } = navigation.getState();
    const below = routes[routes.length - 2];
    const drilledIn = below?.name === 'OrderDetail' && (below.params as { orderId?: string } | undefined)?.orderId === order.id;
    if (drilledIn) return navigation.goBack(); // the parent is right beneath: keep its state
    navigation.reset({ index: 1, routes: [{ name: 'OrderList' }, { name: 'OrderDetail', params: { orderId: order.id } }] }); // deep-linked: rebuild
  };

  return order ? (
    <Pressable accessibilityRole="link" onPress={openOrder} style={styles.parentLink}>
      <Text>{t('shipments.partOf', { order: order.name })}</Text>
    </Pressable>
  ) : null; // …plus the shipment's own content
}
```

`styles.parentLink` meets the touch-target minimum in `std-accessibility`.

## Sections inside an area

**House choice,** by the sections one role sees:

| Visible sections | Section navigation |
|---|---|
| 1 | None — the area root is that section |
| 2–4 | A segmented switcher at the top of each section's root screen. A switch `replace`s the root: sections are peers, so Back never walks through them |
| 5 or more | The area root is a section hub, a list that pushes each section — the phone's form of the web overview |

```tsx
// src/components/organisms/SectionSwitcher/SectionSwitcher.tsx — rendered by each section's root screen
export function SectionSwitcher({ areaKey, current }: { areaKey: AreaKey; current: string }) {
  const navigation = useNavigation<NativeStackNavigationProp<ParamListBase>>();
  const sections = useMobileNav().find(({ key }) => key === areaKey)?.sections ?? [];
  const { t } = useTranslation();
  if (sections.length < 2 || sections.length > 4) return null; // one section: none; five or more: the hub

  return (
    <View accessibilityRole="tablist" style={styles.row}>
      {sections.map((section) => {
        const selected = section.key === current;
        const screen = sectionScreen(areaKey, section.key);
        const open = () => { if (!selected && screen) navigation.replace(screen); };
        return (
          <Pressable key={section.key} accessibilityRole="tab" accessibilityState={{ selected }} onPress={open}
            style={[styles.segment, selected && styles.segmentSelected]}> {/* an indicator plus weight: never colour alone */}
            <Text style={selected ? styles.labelSelected : styles.label}>{t(section.label)}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}
```

A `replace` opens the section at its default list state. If people bounce between sections
mid-task, keep each section's last params in a session-only Zustand store and pass them to
`replace` — client intent, never persisted.

## List state, params and query keys

- **Params carry IDs and list state, never records;** the screen reads the record from the cache by
  ID. A filter change is `navigation.setParams` — no history entry, focus stays on the control — and
  active filters stay visible with a Clear action, since Back does not undo them.
- **One query key per level,** from the house key factory: a detail by ID alone, so it survives a
  move to another parent; a sub-collection under its parent, so invalidating the parent's prefix
  reaches it (TanStack — Query Invalidation). The params are in the list key, so a filter change
  starts a new infinite query and an old cursor never meets new filters (`pagination-clients.md`).
- **The stack keeps the list mounted beneath the detail,** so Back returns to its params, scroll and
  cache: "In most cases, preserving scroll position is the right choice" (Nielsen Norman Group —
  Designing Scroll Behavior). A live queue whose data changed while the person was away starts at the
  top instead (same source).
- **No hover on a phone:** prefetch a detail on `onPressIn` only where profiling shows a slow open.

## Screen readers and focus

Run a VoiceOver and a TalkBack pass per level: after drill-in, focus is on the new screen; after Back,
on the row that drilled in; after a filter, still on the control (the rules are
`drill-down-navigation.md`'s). Where a pass fails, send focus to the screen's heading once the push
has finished — with `sendAccessibilityEvent`, since `setAccessibilityFocus` is deprecated:

```tsx
// src/hooks/useArrivalFocus.ts — only on screens where the VoiceOver or TalkBack pass found focus elsewhere
export function useArrivalFocus() {
  const heading = useRef<ComponentRef<typeof Text>>(null);
  const navigation = useNavigation<NativeStackNavigationProp<ParamListBase>>();

  useEffect(
    () =>
      navigation.addListener('transitionEnd', (event) => {
        // closing is false once this screen has finished opening; focusing earlier races the animation
        if (!event.data.closing && heading.current) AccessibilityInfo.sendAccessibilityEvent(heading.current, 'focus');
      }),
    [navigation],
  );

  return heading; // <Text ref={heading} accessibilityRole="header">{order.name}</Text>
}
```

A section switch remounts the screen: check that the reader lands on the selected segment, and use
the same call if it does not. In-content headings carry `accessibilityRole="header"`, so a reader can
move between them.

## Testing — the rendered shell, once per role

Assert what each role can see and reach, never which navigation call ran. Use `toBeVisible`, not
`toBeOnTheScreen`: tabs and stacks keep screens mounted, so presence alone passes for a tab nobody is
looking at.

```tsx
// src/navigation/RootNavigator.test.tsx
import meByRole from '@/test/fixtures/me-by-role.json'; // exported by the Rails /me request spec: real rules

jest.useFakeTimers();
afterEach(() => jest.restoreAllMocks());

type Role = keyof typeof meByRole;

async function openApp(role: Role, path?: string) {
  server.use(http.get('*/api/v1/me', () => HttpResponse.json({ data: meByRole[role] })));
  useAuthStore.setState({ token: 'test-token' });
  jest.spyOn(Linking, 'getInitialURL').mockResolvedValue(path ? `acme://${path}` : null);
  render(<RootNavigator />, { wrapper: QueryProviders }); // a fresh QueryClient, no NavigationContainer
  await act(() => jest.runAllTimers());
}

const cases: { role: Role; tabs: string[]; denied: string }[] = [
  { role: 'admin', tabs: ['Orders', 'Approvals', 'Organization', 'Account'], denied: 'billing' },
  { role: 'member', tabs: ['Orders', 'Organization', 'Account'], denied: 'approvals' },
  { role: 'viewer', tabs: ['Orders', 'Account'], denied: 'members' },
];

describe.each(cases)('navigation for $role', ({ role, tabs, denied }) => {
  it(`should render exactly its tabs in order when the caller is ${role}`, async () => {
    // Arrange + Act
    await openApp(role);
    // Assert: a tab is named "<label>, tab, <position> of <count>", so order and count are pinned together
    tabs.forEach((label, index) => {
      expect(screen.getByRole('button', { name: `${label}, tab, ${index + 1} of ${tabs.length}` })).toBeVisible();
    });
  });

  it(`should show no access when a ${role} opens a link outside the role`, async () => {
    await openApp(role, denied);
    expect(screen.getByRole('header', { name: /no access/i })).toBeVisible();
  });
});

it('should rebuild the parent order when Up is pressed on a deep-linked shipment', async () => {
  // Arrange
  const user = userEvent.setup();
  await openApp('member', 'shipments/shp_2');
  // Act
  await user.press(screen.getByRole('link', { name: /part of order #4812/i }));
  await act(() => jest.runAllTimers());
  // Assert
  expect(screen.getByRole('header', { name: 'Order #4812' })).toBeVisible();
});

it('should resolve to a real screen when given any mobile area or section href', () => {
  const hrefs = NAV.filter(({ key }) => key in SCREEN_GATES)
    .flatMap((area) => [area.href, ...(area.sections ?? []).map(({ href }) => href)]);
  hrefs.forEach((href) => expect(routeNames(getStateFromPath(href.slice(1), config))).not.toContain('NotFound'));
});
```

- **The wrapper has no `NavigationContainer`.** `renderWithProviders` in `std-testing` adds one, but
  `RootNavigator` owns its container, and containers do not nest.
- **Extend the table:** a path per level each role has; Organization's switcher showing Members ·
  Billing for the owner and nothing for an admin, who keeps one section; every overflow path when a
  More tab exists. Gesture handler and Reanimated setup stay in the shared Jest setup file.

## Sources

- React Navigation — Nesting navigators — https://reactnavigation.org/docs/nesting-navigators
- React Navigation — Configuring links — https://reactnavigation.org/docs/configuring-links
- Apple Human Interface Guidelines — Tab bars — https://developer.apple.com/design/human-interface-guidelines/tab-bars
- Apple Human Interface Guidelines — Toolbars — https://developer.apple.com/design/human-interface-guidelines/toolbars
- Apple Human Interface Guidelines — Search fields — https://developer.apple.com/design/human-interface-guidelines/search-fields
- Android Developers — Principles of navigation — https://developer.android.com/guide/navigation/principles
- Android Developers — Navigation bar (Jetpack Compose, Material 3) — https://developer.android.com/develop/ui/compose/components/navigation-bar
- Material Components for Android — Navigation drawers — https://raw.githubusercontent.com/material-components/material-components-android/master/docs/components/NavigationDrawer.md
- Nielsen Norman Group — Basic Patterns for Mobile Navigation: A Primer — https://www.nngroup.com/articles/mobile-navigation-patterns/
- Nielsen Norman Group — Designing Scroll Behavior: When to Save a User's Place — https://www.nngroup.com/articles/saving-scroll-position/
- TanStack — Query Invalidation — https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation
