# Landing page subdomain routing

Published landing pages are served on **per-project subdomains**, not `/e/{slug}` paths.

| Environment | Public URL | App dashboard |
|-------------|------------|---------------|
| Local dev | `http://{slug}.localhost:3000` | `http://localhost:3000` |
| Production | `https://{slug}.fivvle.io` | `https://app.fivvle.io` (or apex) |

The internal Next.js route `/e/[slug]` is unchanged. Middleware rewrites subdomain requests to that route so the page implementation is not duplicated.

## Local development

1. Start the frontend as usual: `npm run dev` (port 3000).
2. Open a published page at **`http://{slug}.localhost:3000`** (e.g. `http://mewwly.localhost:3000`).

Modern browsers resolve `*.localhost` to `127.0.0.1` automatically — **no `/etc/hosts` edits** are required for new projects.

3. Optional env vars in `.env.local`:

```env
NEXT_PUBLIC_LANDING_ROOT_DOMAIN=fivvle.io
NEXT_PUBLIC_LANDING_DEV_PORT=3000
```

Backend (for `public_url` in publish API and CORS):

```env
LANDING_PUBLIC_ROOT_DOMAIN=fivvle.io
LANDING_PUBLIC_DEV_PORT=3000
```

## Production DNS (assumptions)

- **Wildcard DNS:** `*.fivvle.io` → frontend hosting (Vercel / Firebase App Hosting).
- **App shell:** `app.fivvle.io` or `fivvle.io` → same Next.js app (middleware skips rewrite on apex / reserved subdomains).
- **Reserved subdomains** (never treated as project slugs): `www`, `app`, `api`, `admin`, `staging`, `mail`.

Configure the wildcard domain in your hosting provider (e.g. Vercel: add `*.fivvle.io` to the project domains).

## CORS (backend)

Public landing pages call the API for page-view beacons and waitlist signups. The backend allows project origins via `CORS_LANDING_ORIGIN_REGEX` (default matches `{slug}.localhost` and `{slug}.fivvle.io`).

## ISR revalidation

On-demand revalidation still targets the internal path `/e/{slug}` — no change required.

## Code map

| File | Role |
|------|------|
| `lib/landing-host.ts` | `resolveProjectSlugFromHost()`, URL builders |
| `middleware.ts` | Subdomain → `/e/[slug]` rewrite |
| `app/e/[slug]/page.tsx` | Landing page renderer (unchanged) |
