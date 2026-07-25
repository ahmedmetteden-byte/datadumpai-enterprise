# Report Studio Architecture

**Status:** Reference design — **implementation gate**. Do not ship Report Studio UI until this document is agreed and the Definition of Done in §15 is satisfied.  
**Scope:** Authenticated React app (`web/`) Report Studio module and the FastAPI / generation surface it will call.  
**Related:** [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md), [ORGANISATIONAL_MEMORY_ARCHITECTURE.md](./ORGANISATIONAL_MEMORY_ARCHITECTURE.md), [INTELLIGENCE_STUDIO_ARCHITECTURE.md](./INTELLIGENCE_STUDIO_ARCHITECTURE.md), [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md), Python `models/report_data.py` / report generation services, existing stub `ReportService`.

This document is the source of truth for Report Studio decisions. Prefer extending it over inventing patterns in PRs.

---

## 1. Purpose

**Report Studio** transforms organisational knowledge into professional, editable reports.

It **consumes**:

| Source | How Report Studio uses it |
|--------|---------------------------|
| **Organisational Memory** | Source selection, excerpts, citations, charts/tables grounded in artefacts |
| **Intelligence Studio** | Optional handoffs (e.g. “Create report from this answer”); shared readiness / corpus signals — not embedded chat |

It **produces**:

- Executive reports
- Board papers
- Operational reports
- Compliance reports
- Meeting summaries
- Project reports
- Policy reports
- Risk assessments (template family)

It does **not** own:

| Concern | Owner |
|---------|--------|
| Knowledge indexing / upload pipeline | Organisational Memory |
| AI conversations / threads | Intelligence Studio |
| Export job runners, download packaging, SharePoint/email delivery | Publish module |
| Workspace CRUD, team, settings | Workspace module |
| Auth / billing / plan evaluation | Auth / Plan (server) |
| Marketing site | `marketing-site/` |

**Boundary with Memory:** Memory stores published / indexed report **artefacts** for search and Studio grounding. Report Studio owns **authoring** (drafts, sections, regenerate). When a report is Published, Memory may ingest an immutable snapshot — Studio does not reimplement indexing.

**Boundary with Intelligence Studio:** Studio answers questions with citations. Report Studio authors structured documents. Studio may deep-link into Report Studio with intent/prefill; Report Studio must not embed a chat composer.

**Boundary with Publish:** Report Studio’s `export()` may enqueue a job or return a client-ready payload; **job status, retries, and delivery channels** belong to `PublishService`.

---

## 2. Domain responsibilities

### Naming

| Layer | Name | Meaning |
|-------|------|---------|
| Product UI | **Report Studio** | User-facing |
| React route (proposed) | `/reports` (existing nav) · `/reports/new` · `/reports/:id` | Keep `/reports` as list/studio entry |
| Python today | `ReportData`, report generation services | Canonical structured payload |
| Frontend service | `ReportService` | Already stubbed for Home (`listReports`, `listAwaitingReview`, `getQuickActions`); **expand** for Studio |

**Rule:** user-facing copy says **Report Studio** (page title) or **Reports** (nav brevity). Do not invent a third brand (“Doc Lab”, “Narrative Hub”) without updating this doc.

### Owns

- Template gallery and report wizard (intent → template → sources → generate)
- Report list, draft/editor surfaces, outline, section editing
- Structured generation orchestration (client calls server; no LLM in browser)
- Citations / references UI bound to Memory artefacts
- Charts and tables as first-class section blocks
- Version history (read + restore draft versions)
- Review panel (ready for review → reviewed → approved handoff)
- AI assist actions on sections (regenerate, expand, shorten, rewrite, suggest charts, missing evidence)
- Client contracts on `ReportService` for the above

### Does **not** own

See §1 ownership table. Additionally: no workspace picker inside Studio (use global `WorkspaceContext`); no Memory upload UI except navigation CTAs.

---

## 3. Report domain model

All entities are **workspace-scoped** unless noted. IDs are opaque strings (UUIDs in production). Align field naming with camelCase DTOs; map from Python `ReportData` in FastAPI adapters.

### 3.1 Entity relationship (conceptual)

```
Workspace
  └── ReportTemplate (catalog; may be global + workspace overrides)
  └── Report
        ├── Draft (current working body; 1 active draft pointer)
        ├── Version[] (immutable snapshots of body + metadata)
        ├── Section[] (ordered outline)
        │     ├── Citation[] / block refs
        │     ├── Chart[]
        │     └── Table[]
        ├── Appendix[]
        ├── Reference[]          # bibliography / source list
        ├── Citation[]           # cross-cutting citation index
        └── Approval[]           # future workflow
```

### 3.2 `Report`

Editable / lifecycle-managed report instance.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `workspaceId` | string | |
| `title` | string | |
| `templateId` | string \| null | Origin template |
| `templateKey` | string \| null | Stable key e.g. `executive` |
| `reportType` | string | Product family (maps Python `report_type`) |
| `status` | `ReportLifecycleStatus` | See §4 |
| `summary` | string \| null | Short blurb for lists |
| `authorId` | string | |
| `authorName` | string \| null | Denormalised for lists |
| `currentDraftId` | string \| null | |
| `currentVersionId` | string \| null | Last frozen version |
| `sourceKnowledgeIds` | string[] | Memory artefacts used at generation |
| `createdAt` | ISO datetime | |
| `updatedAt` | ISO datetime | |
| `publishedAt` | ISO datetime \| null | |
| `archivedAt` | ISO datetime \| null | |

List DTO may stay thin (`ReportSummary` today); expand without breaking Home.

### 3.3 `ReportTemplate`

Reusable structure + generation defaults.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `key` | `ReportTemplateKey` | Stable enum-like string |
| `name` | string | Display |
| `description` | string | |
| `category` | string | e.g. executive, board, ops |
| `defaultSectionOutline` | `TemplateSectionSpec[]` | Titles + optional prompts |
| `supportedExportFormats` | `ExportFormat[]` | |
| `planTier` | string[] \| null | null = all entitled workspaces |
| `previewImageUrl` | string \| null | Optional gallery art |

### 3.4 `Section`

Ordered content unit inside a report/draft.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `draftId` | string | Belongs to a draft body |
| `key` | string | Stable within template e.g. `exec_summary` |
| `title` | string | |
| `order` | number | |
| `body` | string | Structured text (markdown or rich JSON — decide in decision log; default **markdown** v1) |
| `kind` | `narrative` \| `metrics` \| `chart_block` \| `table_block` \| `appendix` | |
| `citationIds` | string[] | |
| `chartIds` | string[] | |
| `tableIds` | string[] | |
| `status` | `empty` \| `generating` \| `ready` \| `stale` | Section-level AI state |
| `updatedAt` | ISO datetime | |

### 3.5 `Citation`

Grounded pointer into Organisational Memory (or web if ever entitled — v1 Memory-only).

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `knowledgeId` | string \| null | Memory artefact |
| `knowledgeType` | string \| null | document / meeting / … |
| `title` | string | |
| `excerpt` | string \| null | |
| `locator` | string \| null | Page, timestamp, section |
| `sectionIds` | string[] | Where cited |

### 3.6 `Chart`

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `sectionId` | string | |
| `title` | string | |
| `chartType` | `bar` \| `line` \| `pie` \| `area` \| `combo` \| `other` | |
| `spec` | object | Vega-lite / internal schema — opaque to UI beyond renderer |
| `sourceKnowledgeIds` | string[] | Provenance |
| `caption` | string \| null | |

### 3.7 `Table`

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `sectionId` | string | |
| `title` | string | |
| `columns` | string[] | |
| `rows` | Array<Array<string \| number \| null>> | |
| `sourceKnowledgeIds` | string[] | |
| `caption` | string \| null | |

### 3.8 `Appendix`

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `title` | string | |
| `order` | number | |
| `body` | string | |
| `knowledgeId` | string \| null | Optional attached artefact |

### 3.9 `Reference`

Bibliography / source register (may overlap citations; references are user-facing list, citations are inline anchors).

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `label` | string | Display label |
| `knowledgeId` | string \| null | |
| `url` | string \| null | External if allowed later |
| `order` | number | |

### 3.10 `Draft`

Mutable working copy of the report body.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `revision` | number | Monotonic for conflict detection |
| `sections` | `Section[]` | Or ids + fetch |
| `charts` / `tables` | embedded or referenced | |
| `autosaveAt` | ISO datetime \| null | |
| `generationJobId` | string \| null | Active generate run |
| `updatedAt` | ISO datetime | |
| `updatedBy` | string | |

### 3.11 `Version`

Immutable snapshot (after generate complete, explicit save version, or approve).

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `label` | string | e.g. `v3` or user note |
| `createdAt` | ISO datetime | |
| `createdBy` | string | |
| `snapshot` | object | Frozen draft body |
| `lifecycleStatusAtCapture` | `ReportLifecycleStatus` | |

### 3.12 `Approval` (future)

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `reportId` | string | |
| `versionId` | string | |
| `status` | `pending` \| `approved` \| `rejected` | |
| `reviewerId` | string | |
| `comment` | string \| null | |
| `decidedAt` | ISO datetime \| null | |

v1 may advance `Reviewed` / `Approved` via simple status transitions without a full approval entity; keep the type reserved.

### 3.13 Alignment with Python `ReportData`

| Python `ReportData` | Studio model |
|---------------------|--------------|
| `title`, `report_type`, `narrative` | Report + Draft sections |
| `sections[]` | `Section[]` |
| `citations[]` | `Citation[]` |
| `charts`, `metrics`, `kpis` | `Chart` / table blocks / section metrics |
| `source_documents` | `sourceKnowledgeIds` / References |
| `executive_summary` | Section with key `exec_summary` |

FastAPI should map `ReportData` ↔ Studio DTOs; React must not reimplement compose/markdown pipelines.

---

## 4. Report lifecycle

```
Draft → Generating → Ready for Review → Reviewed → Approved → Published → Archived
```

| State | Meaning | Who can edit body | Typical next |
|-------|---------|-------------------|--------------|
| **Draft** | Created (empty or partial); not in a generate job | Author / editors | Generating (on generate) or stay Draft while editing |
| **Generating** | Server AI job running (full report or bulk sections) | Locked or read-only with progress | Ready for Review on success; Draft on failure |
| **Ready for Review** | Structured draft complete enough for human review | Author may still edit; reviewers read | Reviewed |
| **Reviewed** | Human review completed (comments/checklist cleared or marked done) | Limited edits; major regen may reset to Ready for Review | Approved |
| **Approved** | Formal sign-off for publication | Freeze preferred; admin override | Published |
| **Published** | Released; snapshot available to Memory / consumers | Immutable by default; “create new version” forks Draft | Archived |
| **Archived** | Soft-removed from default lists | No | Restore → previous non-archived (policy TBD) |

**Home mapping:** today’s `ReportSummary.status` values (`draft`, `ready`, `awaiting_review`, `archived`) map approximately:

| Legacy summary | Lifecycle |
|----------------|-----------|
| `draft` | Draft / Generating |
| `ready` | Approved / Published (list “ready”) — clarify in adapter |
| `awaiting_review` | Ready for Review / Reviewed |
| `archived` | Archived |

Decision: **Studio UI and new APIs use the full lifecycle enum**; Home adapters map until Home is updated.

**Failure:** Generation errors return the report to **Draft** with `lastError` on the generation job — not a separate lifecycle state.

---

## 5. Generation flow

```
User Intent
  → Template Selection
  → Knowledge Retrieval
  → AI Reasoning
  → Structured Draft
  → Charts & Tables
  → Citations
  → Editor
  → Review
```

| Stage | Owner | Client behaviour |
|-------|-------|------------------|
| **User Intent** | Wizard / Intelligence handoff | Collect title, audience, time range, goals |
| **Template Selection** | `listTemplates` + gallery | Pick `ReportTemplate` |
| **Knowledge Retrieval** | Server + Memory APIs | User may pin `sourceKnowledgeIds`; server may expand via search |
| **AI Reasoning** | FastAPI / existing Python generators | No prompts or keys in React |
| **Structured Draft** | Server writes Draft + Sections | Poll `generation` status; optimistic skeleton outline |
| **Charts & Tables** | Server (or follow-up job) | Render when `spec` / rows arrive |
| **Citations** | Server links Memory locators | CitationPanel reads typed citations |
| **Editor** | Report Studio | Autosave `saveDraft` / `updateSection` |
| **Review** | ReviewPanel + status transitions | Ready for Review → Reviewed → Approved |

**Regenerate section** re-enters Reasoning → Structured Draft for one `sectionId` without resetting the whole lifecycle (section `status: generating` → `ready`; report may stay Ready for Review).

---

## 6. Component hierarchy

Proposed tree under `src/pages/ReportStudio/` (implement later; keep files ≤ ~200 lines):

```
pages/ReportStudio/
  index.ts
  ReportStudioPage.tsx           # Route shell; binds active workspace
  TemplateGallery.tsx
  ReportWizard.tsx               # Intent → template → sources → generate
  ReportList.tsx
  ReportEditor.tsx               # Centre host
  OutlinePanel.tsx
  SectionEditor.tsx
  CitationPanel.tsx              # Report citations (not Studio chat evidence)
  ChartPanel.tsx
  ExportMenu.tsx
  VersionHistory.tsx
  ReviewPanel.tsx
  EmptyState.tsx                 # or reuse components/ui/EmptyState
  states/
    ReportForbiddenState.tsx
    GenerationProgress.tsx
```

Named deliverables from the product brief map 1:1 to the files above.

Shared reuse:

```
components/layout/AppShell.tsx
components/ui/*          # EmptyState, Button, Modal, …
components/drawers/Drawer.tsx   # Mobile outline / citations
context/WorkspaceContext.tsx
```

### Composition rules

1. **Pages compose; leaves take props or thin hooks** — no `fetch` in section leaves.
2. **No LLM prompts, temperatures, or API keys in React** — only `services.report` (and Memory reads for source pickers).
3. **Horizon visual language** — structured document editor, not a dense BI dashboard.
4. **Active workspace from shell only** — no second workspace picker.
5. **Publish handoff** — ExportMenu calls `report.export` and/or `publish.enqueueExport`; do not rebuild job runners in the editor.

### Route map

| Route | Purpose |
|-------|---------|
| `/reports` | Report Studio home: list + templates entry |
| `/reports/new` | Wizard (template + intent) |
| `/reports/:reportId` | Editor for existing report |
| `/reports/:reportId/review` | Optional focused review mode (or query `?panel=review`) |

Nav label: keep **Reports**; page title **Report Studio**.

Breadcrumbs:

`Home › Report Studio`  
`Home › Report Studio › Q2 Operating Review`

---

## 7. Layout

### Desktop (≥ `lg`)

```
┌────────────────────────────────────────────────────────────────┐
│ AppShell: breadcrumbs · ⌘K · workspace switcher                │
├────────────────┬─────────────────────────────┬─────────────────┤
│ Templates /    │ Editor                      │ Outline /       │
│ Reports list   │  SectionEditor              │ Citations /     │
│                │  (structured body)          │ Insights        │
└────────────────┴─────────────────────────────┴─────────────────┘
```

- Left rail ~260–300px (list + template shortcuts).
- Centre `minmax(0, 1fr)` — primary reading/editing surface.
- Right rail ~320–360px — tabs: Outline · Citations · Insights (generation hints / missing evidence).

Wizard and gallery may use a focused full-width layout before the three-pane editor appears.

### Mobile

- Editor full width.
- Outline and Citations in **Drawers**.
- Report list / templates via top actions or a left sheet.

### Empty states

| Condition | Treatment |
|-----------|-----------|
| No reports | CTA: **Create report** → wizard; secondary: open Memory / Studio |
| No templates entitled | Explain plan; link Account/upgrade later |
| Generating | Progress, not a blank editor |
| No citations yet | Explain grounding after generate |
| Forbidden workspace | Same fail-closed pattern as Workspace module |

---

## 8. Service layer

Client access only through **`ReportService`** (expand existing stub). Bearer = Supabase access token. Mock + HTTP via `createServices()` / `VITE_USE_MOCK_API`.

Keep Home helpers: `listAwaitingReview`, `getQuickActions`.

### 8.1 Target interface

```ts
interface ReportService {
  // Existing (keep)
  listReports(workspaceId: string, auth?: ServiceAuth): Promise<ReportSummary[]>;
  listAwaitingReview(workspaceId: string, auth?: ServiceAuth): Promise<ReportSummary[]>;
  getQuickActions(workspaceId: string, auth?: ServiceAuth): Promise<QuickAction[]>;

  // Report Studio
  getReport(
    workspaceId: string,
    reportId: string,
    auth?: ServiceAuth,
  ): Promise<ReportDetail>;

  generate(
    workspaceId: string,
    input: ReportGenerateInput,
    auth?: ServiceAuth,
  ): Promise<ReportGenerationJob>;  // or ReportDetail + job id

  saveDraft(
    workspaceId: string,
    reportId: string,
    input: ReportDraftSaveInput,
    auth?: ServiceAuth,
  ): Promise<Draft>;

  updateSection(
    workspaceId: string,
    reportId: string,
    sectionId: string,
    input: SectionUpdateInput,
    auth?: ServiceAuth,
  ): Promise<Section>;

  listTemplates(
    workspaceId: string,
    auth?: ServiceAuth,
  ): Promise<ReportTemplate[]>;

  export(
    workspaceId: string,
    reportId: string,
    input: ReportExportInput,
    auth?: ServiceAuth,
  ): Promise<ReportExportResult>;  // may wrap PublishJob

  duplicate(
    workspaceId: string,
    reportId: string,
    auth?: ServiceAuth,
  ): Promise<ReportSummary>;

  archive(
    workspaceId: string,
    reportId: string,
    auth?: ServiceAuth,
  ): Promise<void>;

  delete(
    workspaceId: string,
    reportId: string,
    auth?: ServiceAuth,
  ): Promise<void>;

  // Recommended companions (v1 or immediately after)
  listVersions?(workspaceId: string, reportId: string, auth?: ServiceAuth): Promise<Version[]>;
  restoreVersion?(workspaceId: string, reportId: string, versionId: string, auth?: ServiceAuth): Promise<Draft>;
  transitionStatus?(
    workspaceId: string,
    reportId: string,
    status: ReportLifecycleStatus,
    auth?: ServiceAuth,
  ): Promise<ReportDetail>;
  assistSection?(
    workspaceId: string,
    reportId: string,
    sectionId: string,
    action: ReportAssistAction,
    auth?: ServiceAuth,
  ): Promise<Section>;
  generationStatus?(
    workspaceId: string,
    jobId: string,
    auth?: ServiceAuth,
  ): Promise<ReportGenerationJob>;
}
```

### 8.2 Input / DTO sketches

```ts
type ReportLifecycleStatus =
  | 'draft'
  | 'generating'
  | 'ready_for_review'
  | 'reviewed'
  | 'approved'
  | 'published'
  | 'archived';

type ReportTemplateKey =
  | 'executive'
  | 'board_paper'
  | 'monthly_operations'
  | 'compliance'
  | 'project_status'
  | 'meeting_summary'
  | 'policy_review'
  | 'risk_assessment';

type ReportAssistAction =
  | 'regenerate'
  | 'expand'
  | 'shorten'
  | 'rewrite'
  | 'suggest_charts'
  | 'missing_evidence';

type ExportFormat = 'pdf' | 'docx' | 'pptx' | 'markdown' | 'html';

interface ReportGenerateInput {
  templateId?: string;
  templateKey?: ReportTemplateKey;
  title: string;
  intent?: string;
  sourceKnowledgeIds?: string[];
  audience?: string;
  dateRange?: { from?: string; to?: string };
}

interface ReportDraftSaveInput {
  revision: number;          // optimistic concurrency
  title?: string;
  sections?: SectionUpdateInput[];
}

interface SectionUpdateInput {
  title?: string;
  body?: string;
  order?: number;
}

interface ReportExportInput {
  format: ExportFormat;
  versionId?: string;        // default current approved/published snapshot
}

interface ReportExportResult {
  jobId?: string;            // when delegated to Publish
  downloadUrl?: string;      // short-lived when synchronous mock/dev
  format: ExportFormat;
  status: 'queued' | 'ready' | 'failed';
}

interface ReportGenerationJob {
  id: string;
  reportId: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progressPercent?: number;
  stage?: string;
  errorMessage?: string;
  updatedAt: string;
}
```

### 8.3 HTTP mapping (illustrative)

| Method | Path |
|--------|------|
| `GET` | `/api/v1/workspaces/:id/reports` |
| `GET` | `/api/v1/workspaces/:id/reports/:rid` |
| `POST` | `/api/v1/workspaces/:id/reports/generate` |
| `PUT` | `/api/v1/workspaces/:id/reports/:rid/draft` |
| `PATCH` | `/api/v1/workspaces/:id/reports/:rid/sections/:sid` |
| `GET` | `/api/v1/workspaces/:id/report-templates` |
| `POST` | `/api/v1/workspaces/:id/reports/:rid/export` |
| `POST` | `/api/v1/workspaces/:id/reports/:rid/duplicate` |
| `POST` | `/api/v1/workspaces/:id/reports/:rid/archive` |
| `DELETE` | `/api/v1/workspaces/:id/reports/:rid` |
| `GET` | `/api/v1/workspaces/:id/reports/:rid/versions` |
| `POST` | `/api/v1/workspaces/:id/reports/:rid/assist` |
| `GET` | `/api/v1/workspaces/:id/report-jobs/:jobId` |

Backend wraps existing Python report generators and `ReportData` — **no duplicated generation logic in React**.

---

## 9. Report templates

| Key | Name | Typical use |
|-----|------|-------------|
| `executive` | Executive Report | Leadership narrative + KPIs |
| `board_paper` | Board Paper | Formal board pack section |
| `monthly_operations` | Monthly Operations | Ops cadence / variance |
| `compliance` | Compliance Report | Controls, gaps, evidence |
| `project_status` | Project Status | Initiative progress / risks |
| `meeting_summary` | Meeting Summary | Decisions + actions from Memory meetings |
| `policy_review` | Policy Review | Policy delta + recommendations |
| `risk_assessment` | Risk Assessment | Risk register narrative + tables |

Templates define default outline, suggested Memory filters, and export presets. Workspace may later override copy; marketplace templates are an extension (§14).

---

## 10. Editor

### Principles

- **Structured editing** — outline-driven sections, not a single freeform blob as the only model (narrative markdown *inside* sections is fine).
- **Sections** — create, reorder, regenerate, lock while generating.
- **Tables & charts** — first-class blocks with provenance; edit data where safe; regenerate from sources when assist requests it.
- **References & citations** — CitationPanel + inline markers; open Memory preview via navigation, do not embed Memory’s full library.
- **Autosave** — debounced `saveDraft` / `updateSection` with `revision` conflict handling (toast + reload or merge policy TBD in decision log).

### AI features (server-backed)

| Action | Scope |
|--------|-------|
| Generate report | Full wizard → job |
| Regenerate section | One section |
| Expand / Shorten / Rewrite | Section body |
| Suggest charts | Returns chart specs or suggestions list |
| Identify missing evidence | Insights rail + optional citation gaps |

UI shows assist affordances only when `ReportCapabilities.canAssist` is true; failures surface server `notice` / error — never silent.

---

## 11. Export architecture

Report Studio initiates export; **Publish** owns durable jobs and external delivery.

| Format | v1 stance |
|--------|-----------|
| **PDF** | Primary; enqueue or sync mock |
| **DOCX** | Supported |
| **PPTX** | Supported (board / exec) |
| **Markdown** | Supported (dev + interop) |
| **HTML** | Supported (preview / email body later) |

**Future channels** (Publish / integrations — not Report Studio core):

- SharePoint
- Email

`ExportMenu` lists formats from template + capabilities; disabled formats explain plan or readiness reasons.

---

## 12. State management

| Concern | Location |
|---------|----------|
| **Current report** | Route `/reports/:reportId` + `useReport(reportId)` |
| **Draft status** | From `getReport` / draft DTO; autosave dirty flag local |
| **Generation** | Poll `generationStatus(jobId)` while `status === generating` |
| **Editor** | Local section selection, focus, unsaved buffer |
| **Selection** | Selected `sectionId`, citation id, chart id |
| **History** | `listVersions` panel state |
| **Export** | ExportMenu + optional Publish job id |
| Active workspace | `WorkspaceContext` only |

No Redux. Prefer hooks:

- `useReportList(workspaceId)`
- `useReportEditor(reportId)`
- `useReportGeneration(jobId)`
- `useReportTemplates(workspaceId)`
- `useReportAutosave(reportId)`

---

## 13. Permissions

| Layer | Role |
|-------|------|
| **Supabase RLS** | Hard isolation by workspace membership |
| **FastAPI** | Re-check membership; plan gates for generate / export / assist |
| **React** | Fail-closed capability flags only |

```ts
interface ReportCapabilities {
  canView: boolean;
  canCreate: boolean;
  canEdit: boolean;
  canGenerate: boolean;     // plan + corpus readiness
  canAssist: boolean;       // section AI actions
  canExport: boolean;
  canDuplicate: boolean;
  canArchive: boolean;
  canDelete: boolean;       // owner/admin fail-closed
  canApprove: boolean;      // future; hide if false
  canPublish: boolean;      // may require Publish entitlement
}
```

Viewers: read + export if entitled. Editors+: create/edit/generate. Approve/publish: role + plan. Destructive delete: fail closed unless role allows.

Plan awareness: generation models, deep regenerate, and premium export formats may 402/403 with `notice`; UI disables or explains — never bypass.

Corpus readiness: if Memory has zero indexable sources, wizard warns and may block generate (`canGenerate === false`) with CTA to Library.

---

## 14. Extension points

| Extension | Hook |
|-----------|------|
| **Collaboration** | Presence + draft `revision` / CRDT later |
| **Comments** | Anchored to `sectionId` + range |
| **Approvals** | `Approval` entity + ReviewPanel workflow |
| **Real-time editing** | Websocket on draft; conflict policy |
| **Workflow** | Status machine hooks / automations |
| **Templates marketplace** | External template catalog → `listTemplates` |
| Intelligence handoff | `/reports/new?from=studio&thread=` prefill intent |
| Memory snapshot on publish | Server writes Knowledge `report` artefact |
| Custom section types | Plugin `kind` + renderer registry |

### Explicit non-goals (near term)

- Calling model providers from the browser
- Embedding Intelligence Studio chat inside the editor
- Rebuilding Publish job runners or SharePoint auth in Report Studio
- Client-side RAG / embeddings
- Recreating Streamlit report UI pixel-for-pixel
- Service-role keys in the SPA
- Real-time multiplayer as a v1 blocker

---

## 15. Definition of Done (architecture gate)

This architecture is **approved for implementation** when:

- [ ] Domain ownership boundaries are accepted (esp. vs Memory / Intelligence Studio / Publish / Workspace)
- [ ] Entity set and relationships in §3 are accepted
- [ ] Lifecycle states in §4 are accepted (including Home status mapping approach)
- [ ] Generation flow in §5 is accepted
- [ ] Component hierarchy and routes in §6–7 are accepted
- [ ] `ReportService` methods in §8 are accepted as the client contract
- [ ] Template set in §9 is accepted
- [ ] Editor + AI assist + export stances in §10–11 are accepted
- [ ] Permissions fail-closed + plan-aware stance in §13 is accepted
- [ ] Extension points in §14 are acknowledged as non-blocking for v1
- [ ] Links from `README` / `BACKEND_INTEGRATION` point here

When the above hold, UI/API work may begin **without architectural ambiguity**. Any deviation requires a decision-log entry in §16.

### Implementation readiness checklist (first Report Studio UI PR — later)

1. Expand `ReportService` types + Mock/HTTP for `getReport`, `listTemplates`, `generate`, `saveDraft`, `updateSection`.
2. Ship `ReportStudioPage` list + empty state + template gallery entry.
3. Wizard → mock generation job → editor shell with outline + section editor.
4. CitationPanel wired to mock Memory ids; ExportMenu stubs to Publish or mock download.
5. Lifecycle transitions + review panel; wire Home `awaiting_review` to new statuses when ready.

---

## 16. Decision log

| Date | Decision |
|------|----------|
| 2026-07-25 | Report Studio owns authoring; Memory owns indexed report artefacts; Publish owns delivery jobs |
| 2026-07-25 | Expand existing `ReportService` rather than inventing a second client service name |
| 2026-07-25 | Canonical routes `/reports`, `/reports/new`, `/reports/:id`; nav label Reports; page title Report Studio |
| 2026-07-25 | Lifecycle: Draft → Generating → Ready for Review → Reviewed → Approved → Published → Archived |
| 2026-07-25 | Section body default: markdown in v1; rich JSON left as extension |
| 2026-07-25 | No LLM calls from the browser; generation and assist are server-only |
| 2026-07-25 | Export initiates from Report Studio; durable jobs and SharePoint/email are Publish |
| 2026-07-25 | Template keys fixed for v1 catalog (executive through risk_assessment) |
| 2026-07-25 | Approvals entity reserved; v1 may use status transitions only |
