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

Open [http://localhost:5173](http://localhost:5173). Phase 1 uses mock Home data (`VITE_USE_MOCK_API=true`).

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
  pages/Home/          # Horizon Home composition
  components/          # cards, drawers, layout, ui
  api/
    services/          # Home, Workspace, Knowledge, Report, Publish, AI
    mock/data.ts       # Domain fixtures for Mock*Service
    client.ts          # Shared fetch + Bearer helper
  types/               # Typed API models
  hooks/               # Data + disclosure hooks
  context/             # Workspace selection
  constants/           # Routes + chrome copy
```

UI imports `services` from `@/api/services` (never mock data or URLs).

Architecture references:

- [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) — FastAPI / Supabase connection
- [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) — Workspace domain
- [INTELLIGENCE_STUDIO_ARCHITECTURE.md](./INTELLIGENCE_STUDIO_ARCHITECTURE.md) — Intelligence Studio
- [ORGANISATIONAL_MEMORY_ARCHITECTURE.md](./ORGANISATIONAL_MEMORY_ARCHITECTURE.md) — Organisational Memory (read before building that module)
- [REPORT_STUDIO_ARCHITECTURE.md](./REPORT_STUDIO_ARCHITECTURE.md) — Report Studio (read before building that module)
