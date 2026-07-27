# Loading Flash Survey

**Date:** 2026-07-27  
**Branch:** `feat/universal-chat-tools` @ `92bfdf2`  
**Mode:** Read-only (no edits / commits / server runs).

---

## 1. Routing architecture

- **App Router** (`frontend/app/`). No `pages/` router.
- **Zero `loading.tsx` files** anywhere under `app/`.
- **`Suspense`:** only for `useSearchParams` / public page islands — login, signup, waitlist, `e/[slug]` (fallback=`null` on public landing). Not used for dashboard or experiment routes.

### Route tree (pages only)

```
app/page.tsx                          → home (marketing OR dashboard overview)
app/(auth)/login|signup|forgot-password/page.tsx
app/(dashboard)/dashboard/page.tsx    → redirect("/")
app/(dashboard)/experiments|archived|new|settings/page.tsx
app/(dashboard)/experiment/[id]/page.tsx
app/(dashboard)/experiment/[id]/landing-page/page.tsx
app/(dashboard)/admin/cost|coupons/page.tsx
app/e/[slug]/page.tsx                 → public landing
app/{docs,changelog,privacy,terms,demo,waitlist,preview/device,refinement-demos}/page.tsx
```

### Server vs client

| Route | Pattern |
|-------|---------|
| `app/page.tsx` | Server page → client `HomePageContent` (`"use client"`) |
| `(dashboard)/layout.tsx` | Server wrapper → client `DashboardLayoutClient` |
| `(dashboard)/experiment/[id]/page.tsx` | **Entire page `"use client"`** |
| `(dashboard)/dashboard/page.tsx` | Server `redirect("/")` |
| Auth pages | `"use client"` |

`(dashboard)/layout.tsx` sets `dynamic = "force-dynamic"` / `revalidate = 0`.

---

## 2. Data fetching pattern

- **No React Query / SWR.** No `QueryClientProvider`, no `useQuery` / `useSWR`, no `.prefetchQuery`.
- Pattern: **`useState` + `useEffect` + `lib/api.ts` `fetch` wrappers**.
- No `router.prefetch` usage found in app code surveyed.

### Dashboard / home list

`HomeOverviewContent` (`components/dashboard/HomeOverviewContent.tsx`):

```24:49:frontend/components/dashboard/HomeOverviewContent.tsx
export function HomeOverviewContent() {
  const { user } = useAuth();
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  // ...
  useEffect(() => {
    void fetchExperiments(); // listExperiments()
  }, [fetchExperiments]);

  if (loadState.status === "loading") {
    return ( ... <DashboardHomeSkeleton /> );
  }
```

Initial: `{ status: "loading" }` — no cache / placeholder data.

### Experiment detail

`app/(dashboard)/experiment/[id]/page.tsx` — client page:

```12:51:frontend/app/(dashboard)/experiment/[id]/page.tsx
export default function ExperimentDetailPage() {
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const showLoading = useDelayedLoading(loading, 400);
  // ...
  useEffect(() => {
    setLoading(true);
    setExperiment(null);
    void getExperiment(params.id).then(...).finally(() => setLoading(false));
  }, [params.id]);
```

Fetch starts **only after mount**. Query does not exist between click and mount.

---

## 3. Auth / session hydration (high signal)

**Subscription:** `lib/auth-context.tsx` L79 — `onAuthStateChanged(auth, ...)`.

**Shape:**

```25:34:frontend/lib/auth-context.tsx
type AuthContextValue = {
  user: User | null;
  loading: boolean;      // starts true
  isAdmin: boolean;
  refreshProfile: () => Promise<void>;
  signUp / signIn / signInWithGoogle / logOut
};
```

**Initializing phase:** `loading` starts `true` (L40). Cleared in `onAuthStateChanged`: if user → after `syncUser` `finally`; if no user → immediately `setLoading(false)` (L79–88).

**UI handling:**
- `HomePageContent` / `HomeAuthGate`: `loading` → `DashboardHomeSkeleton`; `!user` → `MarketingLandingPage`; else dashboard shell + overview.
- `DashboardGuard`: `loading` → **different** full-shell `fv-skeleton` layout (rounded cards); `!user` → `null` + `router.replace("/login")`.

**Separate AuthProviders remount on navigation:**
- `/` → `HomePageContent` wraps its own `<AuthProvider>` (L35–37).
- `/(dashboard)/*` → `DashboardLayoutClient` wraps another `<AuthProvider>` (L64–70).

Crossing `/` ↔ `/experiment/[id]` **re-subscribes Firebase** and restarts `loading: true`.

**Login → destination:**

```25:27:frontend/app/(auth)/login/page.tsx
  function handleSuccess(_user: User) {
    router.push(destination); // "/dashboard" or "/new" from intent
  }
```

`destination` typically `/dashboard` → server redirect to `/`. Also `useAuthRedirect` L22–26: when `!loading && user`, `router.replace(destination)`. **No await of a shared hydrated session beyond `signIn`’s `syncAppUser`** before push; destination remounts a new `AuthProvider`.

---

## 4. Dashboard flash

**Primary home UI:** `app/page.tsx` → `HomePageContent` → (authed) `DashboardShell` + `HomeOverviewContent`.  
`/dashboard` only redirects to `/`.

**Before data resolves:** auth gate skeleton, then list `DashboardHomeSkeleton` while `listExperiments` runs.

**No `loading.tsx`** for `/` or dashboard group.

**Two different auth-loading UIs (flash of “old” chrome):**

| Gate | Skeleton language |
|------|-------------------|
| `HomeAuthGate` | `DashboardHomeSkeleton` (BrutalistSkeleton) |
| `DashboardGuard` | Inline `fv-skeleton` + **rounded-xl** card grid (`DashboardLayoutClient` L19–48), including hardcoded `rgba(255,255,255,0.06)` header border |

Navigating into `(dashboard)` routes shows the **fv-rounded** guard skeleton, then brutalist content — matches “old UI flashes before current UI.”

**Storage:** home/overview — no localStorage. `sessionStorage` only for experiment **name peek** (`lib/experiment-name-cache.ts`) on detail page, not full UI snapshot. (Grep still hits deleted `ExperimentDetailPanel` in index — ignore.)

---

## 5. Experiment detail navigation (high signal)

**Renderer:** `ExperimentDetailPage` → `ExperimentCanvas` (L73–78). DeepDive overlays mount inside canvas, not as a separate route.

**Click path:**

```31:34:frontend/components/dashboard/ProjectCard.tsx
  function navigate() {
    cacheExperimentName(experiment.id, getExperimentDisplayTitle(experiment));
    router.push(`/experiment/${experiment.id}`);
  }
```

Sidebar: `<Link href={/experiment/${id}}>` (`ShellSidebar` ~L204). No prefetch API usage.

**Loading UX gap:**

1. Click → soft navigation; **previous route stays painted** (no route `loading.tsx`).
2. Destination JS mounts → `loading=true` → `useDelayedLoading` → `ExperimentLoadingScreen`.
3. `getExperiment` runs in `useEffect` (post-mount).

Between (1) and (2) there is **no skeleton**. Skeleton is gated on destination mount + `isLoading`, not on click.

**`useDelayedLoading(loading, 400)`** (`hooks/useDelayedLoading.ts`): keeps loading UI for **at least** 400ms once shown — reduces flicker of *content* appearing too fast; does **not** make skeleton appear earlier. If fetch finishes before mount paint, user still waited on old page.

When `showLoading` becomes false and `experiment` is still null, page returns **`null`** (L69–71) — possible blank frame.

---

## 6. Existing skeletons

| Asset | Wired? |
|-------|--------|
| `BrutalistSkeleton` | Primitive used by home/list/settings/experiment loading screens |
| `DashboardHomeSkeleton` | Home auth gate + `HomeOverviewContent` loading |
| `ExperimentsListSkeleton` | `ExperimentsContent` loading |
| `SettingsSkeleton` | settings page when `authLoading` |
| `ExperimentLoadingScreen` | experiment `[id]` via `useDelayedLoading` |
| `EditorLoadingSkeleton` | landing-page route; (deleted detail panel was a consumer) |
| `DashboardGuard` inline `fv-skeleton` | auth loading on `(dashboard)` layout |
| `ShellSidebar` `fv-skeleton` | experiment list loading rows |
| `EvidenceStagePanel` / editor `fv-skeleton` | after Evidence mount |
| `SignalWatchingPanel` `WatchingSkeleton` | after Signal analytics pending |
| `LaunchCopyTab` `SectionSkeleton` | copy tab sections |

**Acts:** skeletons exist as **in-panel `isLoading`**, not route-level. Refine chat has no route skeleton. Evidence/Signal/Launch skeletons appear only after DeepDive/act mount.

---

## 7. Instant-navigation candidates (current UX)

| Transition | Current | Missing for instant feedback |
|------------|---------|------------------------------|
| Login success → `/dashboard`→`/` | `router.push` then new `AuthProvider` + home fetch | No pending UI on click; remount re-auth; double skeleton languages |
| Signup → same | Same | Same |
| Project card → `/experiment/[id]` | `router.push`; old page until mount; then delayed loading screen | No click-time pending / no `loading.tsx` |
| Sidebar experiment `Link` | Soft nav, same destination pattern | Same |
| `/` ↔ other dashboard pages | Guard re-auth skeleton (fv) then page fetch | Route-level loading absent; AuthProvider shared within group but still auth gate |

---

## 8. `loading.tsx` / route Suspense

- **None.** App Router without route-level loading UI.
- No Pages Router / `_app` transition layer.

---

## 9. Cache / stale rendering

- No React Query `placeholderData` / `keepPreviousData`.
- List/detail: empty/`loading` until fetch — not “show stale list then refresh.”
- Name-only `sessionStorage` peek for loading screen title.
- Soft-nav **previous route paint** is the main “stale UI” source for navigation flash.

---

## 10. Baseline

```
92bfdf2 Part2 PR-2a: delete Evidence report-side orphans
8d2c56a Part2 PR-1: delete orphaned Insight, extract PanelHeader, audit Signal to brutalist north star
4fa2317 PR-4: cascade cleanup - v2 into cascade, delete phantom statuses, rename edited_doc staleness
```

Recent Part 1/2 commits did **not** target routing, auth hydration, or data-fetch libraries. Flash is consistent with long-standing client `useEffect` fetch + no `loading.tsx` + dual `AuthProvider` + `useDelayedLoading` on experiment page.
