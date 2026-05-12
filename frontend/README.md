# Fivvle — Frontend

Next.js 15 App Router frontend for Fivvle.

## Local development

```bash
npm install
cp .env.example .env.local
# Fill in the Firebase values from:
# Firebase Console → Project Settings → General → Your apps → Web app → SDK setup and configuration
npm run dev
```

The app runs on [http://localhost:3000](http://localhost:3000). The backend must be running on `http://localhost:8000` for the API calls to work — see `backend/README.md` for backend setup.

## Environment variables

All public config goes in `.env.local` (gitignored). Copy from `.env.example` and fill in values:

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase client API key (public identifier) |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase app ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase messaging sender ID |
| `NEXT_PUBLIC_API_BASE_URL` | Backend API base URL (default: `http://localhost:8000`) |

Per `AGENTS.md`: the Firebase client config values are **public identifiers**, not secrets. They are safe in `NEXT_PUBLIC_*`. Nothing else should ever be added under `NEXT_PUBLIC_*`.

## Architecture

The frontend is a **thin client**. It collects user input, displays data fetched from the backend, and manages Firebase Auth session state. It makes no security decisions.

- All business logic lives in `backend/`. See `.cursorrules` and `AGENTS.md` for the frontend/backend boundary.
- Auth: Firebase ID tokens via `Authorization: Bearer` header — the backend verifies every protected request.
- API calls: `frontend/lib/api.ts` — all backend calls go through `apiFetch()`. No direct calls to Anthropic, Groq, Tavily, or any third-party API from the browser.
- Auth context: `frontend/lib/auth-context.tsx` — exposes `user`, `loading`, `signUp`, `signIn`, `logOut`.

## Scripts

```bash
npm run dev      # Start dev server (http://localhost:3000)
npm run build    # Production build
npm run lint     # ESLint via eslint-config-next
```

## Testing

Frontend tests are deferred to step 7 (first vertical slice), where Vitest + React Testing Library will be set up alongside the first real feature. This is intentional — the foundation is verified manually against the running backend.
