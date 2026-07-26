# DataDumpAI Enterprise Web

Authenticated React frontend for DataDumpAI Enterprise (Project Horizon). This app will replace the Streamlit UI over time. It does **not** replace the marketing site.

## Stack

- Vite + React 19 + TypeScript
- React Router 7
- Tailwind CSS 3 (tokens aligned with `core/theme.py`)

## Quick start

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). By default the SPA uses the live product API (`VITE_USE_MOCK_API=false`). Start the FastAPI API (and set Supabase env vars) so Home, Library, Studio, and Reports load real workspace data.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Local development server |
| `npm run build` | Typecheck + production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Oxlint |

## Architecture

```
src/
  pages/
    Auth/              # Login, register, forgot password
    Account/           # Profile + organisation membership
    Home/              # Horizon Home composition
  components/
    auth/              # ProtectedRoute / PublicOnlyRoute
    cards, drawers, layout, ui
  api/
    services/          # Auth, Profile, Home, Workspace, Knowledge, Report, Publish, AI
    mock/data.ts       # Domain fixtures for Mock*Service
    client.ts          # Shared fetch + Bearer helper (+ 401 → /auth/login)
  context/             # Auth + Workspace selection
  constants/           # Routes + chrome copy
```

UI imports `services` from `@/api/services` (never mock data or URLs).

Auth (Phase 1): with `VITE_USE_MOCK_API=true`, any email + password (≥6 chars) signs in and the session persists in `localStorage`. With real Supabase env vars and mocks off, the SPA uses Supabase Auth JWTs.
Architecture references:

- [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) — FastAPI / Supabase connection
- [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) — Workspace domain
- [INTELLIGENCE_STUDIO_ARCHITECTURE.md](./INTELLIGENCE_STUDIO_ARCHITECTURE.md) — Intelligence Studio
- [ORGANISATIONAL_MEMORY_ARCHITECTURE.md](./ORGANISATIONAL_MEMORY_ARCHITECTURE.md) — Organisational Memory (read before building that module)
- [REPORT_STUDIO_ARCHITECTURE.md](./REPORT_STUDIO_ARCHITECTURE.md) — Report Studio (read before building that module)
