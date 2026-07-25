# Workspace Architecture

**Status:** Implemented — UI module shipped; keep this document updated with API/permission changes.  
**Scope:** Authenticated React app (`web/`) and the product FastAPI surface it will call.  
**Related:** [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md), Home (Project Horizon) already shipped.

This document is the source of truth for Workspace decisions. Prefer extending it over inventing patterns in PRs.

---

## 1. Domain responsibilities

### What a Workspace is

In product language, a **Workspace** is the primary container for organizational work:

```
Workspace
├── Metadata (name, description, ownership, activity)
├── Documents / knowledge corpus
├── Reports & drafts
├── AI readiness & insights
├── Team membership & roles
├── Timeline / activity
├── Analytics & health
└── Exports / publish jobs
```

The UI is a window into one active Workspace at a time. Home aggregates a thin slice; the Workspace module owns the full lifecycle of that container.

### Naming note (important)

| Layer | Current name | Meaning |
|-------|--------------|---------|
| Python `models/workspace.py` | `Workspace` | Assembled domain object (project + docs + reports + AI…) |
| Supabase / repositories | `projects` | Persistence row the product calls a workspace |
| React `Project` type | `Project` | API DTO for that row (`src/types/api.ts`) |
| React UI / routes | Workspace | User-facing term |

**Rule for new code:** user-facing copy and routes say **Workspace**. TypeScript may keep `Project` as the persistence DTO until a deliberate rename. Do not introduce a third term (e.g. “Org”, “Space”) without updating this doc.

### Workspace module owns

- Listing, selecting, creating, renaming, archiving workspaces
- Workspace settings (description, defaults, retention hints)
- Health, team, activity, and organizational intelligence surfaces that are workspace-scoped
- Active-workspace context used by Home, Documents, Reports, Copilot, Publish
- Permission checks for workspace-scoped actions (UI gating; server enforces)

### Workspace module does **not** own

| Concern | Owner |
|---------|--------|
| Document upload / indexing UX | Knowledge / Documents module |
| Report authoring & review workflow | Reports module |
| Copilot chat | AI / Copilot module |
| Export job execution UI details | Publish module |
| Auth session / login | Auth module |
| Billing | Billing (server + future Account) |
| Marketing site | `marketing-site/` |

Other modules **consume** `WorkspaceContext` + `services.workspace`; they do not reimplement workspace CRUD or selection.

---

## 2. Component hierarchy

Proposed tree under `src/pages/Workspace/` (implement in a later phase; keep files ≤ ~200 lines):

```
pages/Workspace/
  index.ts
  WorkspacePage.tsx                 # Route shell: header + section outlet
  WorkspaceListPage.tsx             # Optional /workspaces index
  WorkspaceHeader.tsx               # Name, health chip, actions
  WorkspaceSectionNav.tsx           # In-page sections / tabs
  sections/
    OverviewSection.tsx             # Summary metrics + recent activity
    HealthSection.tsx
    TeamSection.tsx
    ActivitySection.tsx
    SettingsSection.tsx             # Rename, description, danger zone
  dialogs/
    CreateWorkspaceDialog.tsx
    ArchiveWorkspaceDialog.tsx

components/ (shared, reuse from Home where possible)
  cards/WorkspaceCard.tsx           # Already used on Home “Continue working”
  drawers/…                         # Prefer drawers for secondary detail
  layout/AppShell.tsx               # Global chrome; workspace switcher may live here later
```

### Composition rules

1. **Pages compose; sections fetch or receive props** — prefer data from hooks (`useWorkspace`, `useWorkspaceDetail`), not ad hoc `fetch` in leaves.
2. **No business logic in JSX** — formatting, permission booleans, and route builders live in `lib/` or hooks.
3. **Reuse Horizon patterns** — same tokens, `SectionHeader`, `Collapsible`, `Drawer`, card hover language as Home.
4. **Insights depth stays out of the main Workspace overview** — deep AI brief / recommendations remain in the Insights drawer pattern (or a dedicated Insights route later), not a second dashboard on the overview.

### Suggested route map

| Route | Purpose |
|-------|---------|
| `/workspaces` | List / switch (optional; selector on Home may suffice initially) |
| `/workspaces/:workspaceId` | Redirect → overview |
| `/workspaces/:workspaceId/overview` | Default workspace landing |
| `/workspaces/:workspaceId/health` | Health detail |
| `/workspaces/:workspaceId/team` | Members |
| `/workspaces/:workspaceId/activity` | Activity feed |
| `/workspaces/:workspaceId/settings` | Settings |

Global nav label: **Workspaces** or keep Home as primary entry and open workspace via selector — decide in implementation PR; default recommendation: **selector everywhere + `/workspaces/:id/overview` for deep links**.

---

## 3. API endpoints

All product APIs are versioned under `/api/v1`. Client access is only through `services.workspace` (and siblings). Bearer = Supabase access token.

### WorkspaceService (core)

| Method | HTTP | Notes |
|--------|------|-------|
| `listWorkspaces()` | `GET /api/v1/workspaces` | Member workspaces for current user |
| `getWorkspace(id)` | `GET /api/v1/workspaces/:id` | Metadata DTO (`Project`) |
| `createWorkspace(body)` | `POST /api/v1/workspaces` | **Add to contract before UI** |
| `updateWorkspace(id, body)` | `PATCH /api/v1/workspaces/:id` | **Add to contract before UI** |
| `archiveWorkspace(id)` | `POST /api/v1/workspaces/:id/archive` | Soft-delete preferred |
| `getHealth(id)` | `GET /api/v1/workspaces/:id/health` | `WorkspaceHealthSummary` |
| `getInsightsOverview(id)` | `GET /api/v1/workspaces/:id/insights/overview` | Card metrics |
| `getTeam(id)` | `GET /api/v1/workspaces/:id/team` | `TeamMember[]` |
| `getOrganizationalIntelligence(id)` | `GET /api/v1/workspaces/:id/organizational-intelligence` | Signals |
| `getRecentActivity(id, limit?)` | `GET /api/v1/workspaces/:id/activity` | `ActivityLog[]` |
| `getContinueWorking(id)` | `GET /api/v1/workspaces/:id/continue-working` | Resume cards |

### Related (other services, workspace-scoped)

| Service | Examples |
|---------|----------|
| `KnowledgeService` | `…/search`, `…/search/suggestions` |
| `ReportService` | `…/reports`, `…/quick-actions` |
| `PublishService` | `…/publish/jobs`, `…/publish/exports` |
| `AIService` | `…/ai/brief`, `…/ai/recommendations`, `…/ai/insights` |
| `HomeService` | `GET /api/v1/home?workspace_id=` BFF aggregate |

### Response shapes

Reuse types in `src/types/api.ts` and `src/types/home.ts`. New write DTOs should be added there first:

```ts
interface CreateWorkspaceInput {
  name: string;
  description?: string;
}

interface UpdateWorkspaceInput {
  name?: string;
  description?: string;
}
```

Backend should assemble from existing Python services (`WorkspaceService`, `ProjectService`, `ActivityService`, etc.) — no duplicated business rules in React.

---

## 4. State management

### Principles

1. **Server state** — workspace lists, detail, health, team, activity → hooks calling `services.*` (React Query optional later; start with simple hooks like `useHomeData`).
2. **Client/session state** — `activeWorkspaceId` only → `WorkspaceContext` (already exists).
3. **URL as source of truth for deep links** — when on `/workspaces/:workspaceId/…`, sync context from the route param.
4. **No global Redux** unless cross-cutting complexity forces it; prefer context + hooks.

### WorkspaceContext (extend carefully)

Current:

- `activeWorkspaceId`
- `setActiveWorkspaceId`

Allowed extensions:

- `workspaces` cache invalidation signal / `revision` counter
- `permissions` for the active workspace (derived from API, not guessed)

Disallowed:

- Storing full report/document graphs in context
- Duplicating Home page DTO in context

### Hook map

| Hook | Responsibility |
|------|----------------|
| `useWorkspace()` | Active id setter/getter (context) |
| `useWorkspaceList()` | `services.workspace.listWorkspaces()` |
| `useWorkspaceDetail(id)` | `getWorkspace` + optional parallel health/team |
| `useWorkspacePermissions(id)` | Maps role → capability flags |

Invalidate list/detail after create/rename/archive.

---

## 5. Permissions

### Enforcement model

| Layer | Role |
|-------|------|
| **Supabase RLS** | Hard boundary — users only see rows they own/are members of |
| **FastAPI** | Re-check membership/role on every mutating route; never trust the client |
| **React** | UX gating only (hide/disable); never the security boundary |

### Roles (target model)

Align with future membership table (today many workspaces are owner-only via `projects.owner_id`):

| Role | Capabilities |
|------|----------------|
| `owner` | Full control including archive & transfer |
| `admin` | Manage members, settings, publish; not transfer ownership |
| `editor` | Upload docs, generate/edit reports, run Copilot |
| `reviewer` | View + comment / approve reports; limited write |
| `viewer` | Read-only knowledge, reports, insights |

UI capability flags (example):

```ts
interface WorkspaceCapabilities {
  canView: boolean;
  canEditSettings: boolean;
  canManageTeam: boolean;
  canUpload: boolean;
  canGenerateReports: boolean;
  canPublish: boolean;
  canArchive: boolean;
}
```

Derive from `role` returned by `GET …/team` or a dedicated `GET …/me` membership endpoint. Do not hard-code role strings in components — map once in `useWorkspacePermissions`.

### Fail-closed

If permissions are loading or the API errors, treat as **no elevated capability**. Match `core/project_access.py` fail-closed spirit.

---

## 6. Navigation flow

```
AppShell (sidebar)
  Home (/home)
    └─ Workspace selector → setActiveWorkspaceId → refetch Home
    └─ View Insights → drawer (workspace-scoped AI/activity)
  Workspaces (future)
    └─ /workspaces → list → /workspaces/:id/overview
    └─ Section nav → health | team | activity | settings
  AI Workspace / Documents
    └─ Uses activeWorkspaceId; no local workspace picker required
  Reports / Copilot / Settings
    └─ Same active workspace unless route overrides
```

### Switching workspace

1. User selects workspace (Hero select, future header switcher, or list page).
2. `setActiveWorkspaceId(id)` (+ optional `navigate` to workspace overview).
3. Dependent queries key on `workspaceId` and refetch.
4. Persist last active id in `localStorage` (optional; document key `dde.activeWorkspaceId`) so reload restores context after auth.

### Deep links

`/workspaces/:workspaceId/overview` must work when opened cold: auth → set active id from param → load detail. If the user lacks access → dedicated forbidden empty state (not a blank Home).

---

## 7. Future extension points

Design so these can land without rewriting the module:

| Extension | Hook point |
|-----------|------------|
| Multi-member workspaces | `TeamSection` + `POST/DELETE …/team` |
| Workspace templates | `CreateWorkspaceDialog` template step |
| Shared / org-level workspaces | List filters + RLS policies |
| Workspace-level feature flags | Capabilities object from API |
| Audit log export | Activity section → PublishService |
| Retention / legal hold | Settings danger zone + backend policy |
| External connectors | Knowledge module; workspace only stores connection refs |
| Mobile compact chrome | `WorkspaceHeader` responsive variants |
| Realtime activity | Subscribe in `useWorkspaceDetail`; keep DTO stable |
| Rename `Project` → `Workspace` in TS | Codemod types + this doc; API path stays `/workspaces` |

### Explicit non-goals (near term)

- Recreating the Streamlit overview pixel-for-pixel
- Building a second “dashboard of dashboards” on Workspace overview
- Client-side search indexing
- Service-role keys in the browser

---

## 8. Implementation checklist (when building the module)

1. Extend `WorkspaceService` contract with create/update/archive (+ HTTP + mock).
2. Add types for write DTOs and `WorkspaceCapabilities`.
3. Sync `WorkspaceContext` with route params.
4. Ship `WorkspacePage` + Overview first; Team/Settings second.
5. Wire permissions fail-closed.
6. Update [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) if routes change.
7. Keep Home Insights drawer as the dense intelligence surface unless product says otherwise.

---

## 9. Decision log

| Date | Decision |
|------|----------|
| 2026-07-24 | Workspace is the product container; React DTO may remain named `Project` until a rename pass |
| 2026-07-24 | UI accesses data only via `services.*`; mock/HTTP swap via `VITE_USE_MOCK_API` |
| 2026-07-24 | Active workspace lives in React context; URL owns deep links |
| 2026-07-24 | Security is RLS + FastAPI; UI permissions are cosmetic |
| 2026-07-24 | This file must be updated when Workspace endpoints or roles change |
| 2026-07-25 | Workspace UI module implemented: list, overview, health, timeline, team, settings |
