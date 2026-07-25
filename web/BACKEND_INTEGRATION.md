# Backend integration guide

Phase 1 uses a **domain service layer** with mock implementations. UI code talks only to service interfaces—never to fetch URLs or mock fixtures directly. Replacing mocks with FastAPI is a factory switch, not a UI rewrite.

For Workspace UI scope, responsibilities, permissions, and navigation, see [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) **before** implementing that module.

For Intelligence Studio (interactive AI / legacy Copilot), see [INTELLIGENCE_STUDIO_ARCHITECTURE.md](./INTELLIGENCE_STUDIO_ARCHITECTURE.md) **before** implementing that module.

For Organisational Memory (Knowledge Library / corpus), see [ORGANISATIONAL_MEMORY_ARCHITECTURE.md](./ORGANISATIONAL_MEMORY_ARCHITECTURE.md) **before** implementing that module.

For Report Studio (authoring / generation / review), see [REPORT_STUDIO_ARCHITECTURE.md](./REPORT_STUDIO_ARCHITECTURE.md) **before** implementing that module.

## Service container

```ts
import { services } from '@/api/services';

await services.home.getHome(workspaceId);
await services.workspace.listWorkspaces();
await services.knowledge.getSearchSuggestions(workspaceId);
await services.report.listAwaitingReview(workspaceId);
await services.publish.listJobs(workspaceId);
await services.ai.listInsights(workspaceId);
```

| Service | Responsibility | Future FastAPI surface (examples) |
|---------|----------------|-----------------------------------|
| `HomeService` | Home aggregate + greeting + notifications | `GET /api/v1/home`, `/home/greeting`, `/notifications` |
| `WorkspaceService` | Workspaces CRUD, health, team, activity, continue-working, membership | `GET/POST/PATCH /api/v1/workspaces…`, `…/archive`, `…/memberships/me` |
| `KnowledgeService` | Organisational Memory: list/search/get/upload/tag/related/preview/processing + Home search suggestions | `GET/POST …/knowledge…`, `…/search`, `…/search/suggestions` |
| `ReportService` | Report Studio: list/get/generate/draft/sections/templates/export/duplicate/archive/delete + Home awaiting-review / quick actions | `GET/POST …/reports…`, `…/report-templates`, `…/report-jobs`, `…/quick-actions` |
| `PublishService` | Export / publish jobs | `GET/POST …/publish/…` |
| `AIService` | Brief, recommendations, insights | `GET …/ai/brief`, `…/recommendations`, `…/insights` |

Implementations live under `src/api/services/`:

- `Mock*Service` — Phase 1 fixtures (`src/api/mock/data.ts`)
- `Http*Service` — real `apiRequest` calls
- `createServices()` — picks mock vs HTTP via `VITE_USE_MOCK_API`

`MockHomeService` **composes** the other domain services so Home stays a facade. `HttpHomeService` prefers a single BFF `GET /api/v1/home` for one round-trip; granular HTTP services remain available for other screens.

## Current backend reality

| Surface | Status |
|---------|--------|
| Streamlit app (`app.py`) | Live product UI (being replaced) |
| `api/webhook_server.py` | Billing webhooks only |
| Supabase Auth + Postgres + Storage | Source of truth |
| Product REST (`/api/v1/*`) | **Not implemented yet** |

Do not call webhook routes from this SPA. Do not expose `SUPABASE_SERVICE_ROLE_KEY` to the browser.

## Environment

```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=                 # empty → same-origin / Vite proxy
VITE_USE_MOCK_API=true             # false → Http*Service implementations
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

## Switch off mocks

1. Implement the FastAPI routes matching the `Http*Service` paths (start with `GET /api/v1/home` returning `HomePageData`).
2. Set `VITE_USE_MOCK_API=false`.
3. Keep calling `services.*` — no Home component changes.

Optional later: pass `{ accessToken }` as the `auth` argument on service methods (already on every contract).

## Preferred FastAPI mapping

Wire routers to existing Python services—do not reimplement logic in React:

- `services/workspace_service.py` → `WorkspaceService`
- `services/report_service.py` → `ReportService`
- `services/activity_service.py` → activity methods
- `services/project_service.py` → workspace list/get
- Future AI/insights pipeline → `AIService`
- Export pipeline → `PublishService`
- Search pipeline → `KnowledgeService`

## Auth

1. Add `@supabase/supabase-js`.
2. Persist session; pass `accessToken` into service methods / `apiRequest`.
3. Update `AUTH_REDIRECT_URL` when cutting over from Streamlit.

## JSON naming

Frontend types use **camelCase**. Prefer FastAPI serializers that emit camelCase, or map once inside `Http*Service` classes (never in React components).

## Verification checklist

- [ ] `VITE_USE_MOCK_API=false` loads Home via `HttpHomeService`
- [ ] Granular services work for non-Home screens
- [ ] Unauthorized requests redirect to a future `/auth` route
- [ ] Workspace switch still uses `services.home.getHome(workspaceId)`
- [ ] Marketing site untouched
