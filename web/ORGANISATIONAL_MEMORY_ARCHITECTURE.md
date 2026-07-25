# Organisational Memory Architecture

**Status:** Reference design — **implementation gate**. Do not ship UI until this document is agreed and the Definition of Done in §11 is satisfied.  
**Scope:** Authenticated React app (`web/`) Organisational Memory module (Knowledge Library) and the FastAPI / indexing surface it will call.  
**Related:** [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md), [INTELLIGENCE_STUDIO_ARCHITECTURE.md](./INTELLIGENCE_STUDIO_ARCHITECTURE.md), [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md), Python `models/knowledge.py`, Streamlit documents / search pipelines.

This document is the source of truth for Organisational Memory decisions. Prefer extending it over inventing patterns in PRs.

---

## 1. Purpose

**Organisational Memory** is the knowledge backbone of DataDumpAI.

It owns **organisational knowledge** for the active Workspace: what was uploaded, said, decided, promised, and published — plus the indexes that make that knowledge findable by humans and AI.

It powers:

| Consumer | How Memory is used |
|----------|--------------------|
| **Intelligence Studio** | Grounding context, citations, readiness (`documentCount` / corpus) |
| **Report Studio** (future) | Source selection, excerpts, provenance |
| **Search** (Universal Search + Library search) | Keyword + semantic retrieval over the corpus |
| **Future AI Agents** | Tooling over `search`, `related`, `getKnowledge`, graph edges |

Organisational Memory is **not** a chatbot, **not** a report editor, and **not** workspace admin.

---

## 2. Domain responsibilities

### Naming

| Layer | Name | Meaning |
|-------|------|---------|
| Product UI | **Organisational Memory** / **Knowledge Library** | User-facing |
| React route (proposed) | `/knowledge` (Phase 4); `/library` redirects | Keep `/knowledge` as canonical v1; `/library` → `/knowledge` |
| Python today | `KnowledgeStore` / `KnowledgeEntry` | Persistence-oriented corpus view |
| Frontend service | `KnowledgeService` | Already stubbed for search suggestions; **expand** to own Memory APIs |

**Rule:** user-facing copy may say “Library” in nav for brevity; page title **Organisational Memory** or **Knowledge Library**. Do not invent a third brand (“Vault”, “Corpus Hub”) without updating this doc.

### Owns

- Knowledge Library UX (browse, filter, tag, preview, upload entry points)
- Documents, meetings, transcripts, reports (as **knowledge artefacts** — not report editing)
- Decisions, action items, policies, projects (as structured knowledge entities)
- Relationships between artefacts
- Metadata and tags
- Knowledge indexing lifecycle and processing status surfaces
- Semantic / keyword retrieval APIs consumed by Search and Studio

### Does **not** own

| Concern | Owner |
|---------|--------|
| Workspace CRUD, team, settings | Workspace module |
| AI conversations / threads | Intelligence Studio |
| Report drafting, sections, regenerate | Report Studio |
| Export job runners, download packaging | Publish module |
| Auth / billing / plan evaluation | Auth / Plan (server) |
| Marketing site | `marketing-site/` |

**Boundary with Documents (AI Workspace):** Upload and processing **status** live in Memory. Heavy “AI Workspace” chat-to-report flows stay elsewhere; Memory supplies the corpus those flows read.

**Boundary with Intelligence Studio:** Studio **reads** Memory via server context assembly. Memory never embeds a chat composer.

---

## 3. Knowledge model

### 3.1 Core entities

All entities are **workspace-scoped** unless noted. IDs are opaque strings (UUIDs in production).

#### `Document`

Uploaded or ingested file (PDF, DOCX, XLSX, PPTX, TXT, audio container, etc.).

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `workspaceId` | string | |
| `title` | string | Display name |
| `filename` | string | Original filename |
| `mimeType` | string | |
| `sizeBytes` | number | |
| `storagePath` | string | Supabase Storage / object key |
| `status` | `uploading \| extracting \| indexing \| ready \| failed` | Processing |
| `uploadedAt` | ISO datetime | |
| `uploadedBy` | user id | |
| `tagIds` | string[] | |
| `projectRefId` | string \| null | Optional link to Project entity |
| `checksum` | string \| null | Dedup / versioning later |

#### `Meeting`

A scheduled or recorded collaboration event.

| Field | Notes |
|-------|-------|
| `id`, `workspaceId`, `title` | |
| `heldAt` | Meeting time |
| `participants` | Display names / user ids |
| `transcriptId` | Optional link to `Transcript` |
| `recordingDocumentId` | Optional source media as `Document` |
| `tagIds` | |
| `status` | Processing of transcript / summary |

#### `Transcript`

Textual record of a meeting (or call).

| Field | Notes |
|-------|-------|
| `id`, `meetingId`, `workspaceId` | |
| `language` | |
| `fullTextRef` | Storage pointer (not always inlined) |
| `segments` | Optional timed segments for UI |
| `status` | |

#### `Decision`

An explicit organisational decision captured from meetings, reports, or manual entry.

| Field | Notes |
|-------|-------|
| `id`, `workspaceId`, `title`, `summary` | |
| `decidedAt` | |
| `sourceIds` | Related knowledge ids |
| `ownerId` | Optional accountable person |
| `status` | `proposed \| accepted \| superseded` |

#### `ActionItem`

A trackable follow-up.

| Field | Notes |
|-------|-------|
| `id`, `workspaceId`, `title` | |
| `assigneeId` | Optional |
| `dueAt` | Optional |
| `status` | `open \| done \| cancelled` |
| `sourceIds` | Meeting / report / decision links |
| `priority` | `low \| medium \| high` |

#### `Policy`

Governing document or rule set (compliance, security, process).

| Field | Notes |
|-------|-------|
| `id`, `workspaceId`, `title` | |
| `documentId` | Backing file when applicable |
| `effectiveFrom` / `effectiveTo` | |
| `jurisdiction` | Optional |
| `tagIds` | |

#### `Report`

Generated or imported analytical artefact **as knowledge** (immutable snapshot for Memory). Editing lives in Report Studio; Memory stores the published/indexed version.

| Field | Notes |
|-------|-------|
| `id`, `workspaceId`, `title`, `filename` | Align with existing `ReportSummary` |
| `reportType` | |
| `createdAt`, `status` | `draft` may be excluded from AI corpus until ready |
| `sourceDocumentIds` | Provenance |
| `tagIds` | |

#### `Project`

Structured initiative inside a Workspace (not the Workspace itself). Distinct from React `Project` DTO used historically for workspace rows — see naming note below.

| Field | Notes |
|-------|-------|
| `id`, `workspaceId`, `name`, `description` | |
| `status` | `active \| on_hold \| closed` |
| `linkedKnowledgeIds` | |

**Naming collision:** Today React `Project` ≈ Workspace persistence row. For Memory, use TypeScript name **`KnowledgeProject`** (or `Initiative`) until the Workspace DTO rename lands. User-facing label: **Project**.

#### `Tag`

| Field | Notes |
|-------|------|
| `id`, `workspaceId`, `label`, `color?` | Workspace-unique label |

#### `KnowledgeRelationship`

Directed or undirected edge in the knowledge graph.

| Field | Notes |
|-------|------|
| `id`, `workspaceId` | |
| `fromId`, `toId` | Knowledge artefact ids |
| `fromType`, `toType` | Entity discriminant |
| `predicate` | e.g. `cites`, `derived_from`, `decides`, `assigns`, `mentions`, `supersedes` |
| `weight` | Optional confidence 0–1 |
| `createdAt` | |

#### `WorkspaceKnowledge` (aggregate)

Server-assembled view of the corpus for one workspace — spiritual successor to Python `KnowledgeStore`.

```ts
interface WorkspaceKnowledge {
  workspaceId: string;
  ready: boolean;
  counts: {
    documents: number;
    meetings: number;
    reports: number;
    decisions: number;
    actionItems: number;
    policies: number;
    projects: number;
  };
  // Optional recent entries for Library landing
  recent: KnowledgeListItem[];
}
```

#### Unified list item (Library row/card)

```ts
type KnowledgeEntityType =
  | 'document'
  | 'meeting'
  | 'transcript'
  | 'decision'
  | 'action_item'
  | 'policy'
  | 'report'
  | 'project';

interface KnowledgeListItem {
  id: string;
  workspaceId: string;
  type: KnowledgeEntityType;
  title: string;
  summary?: string;
  status?: string;
  tagIds: string[];
  updatedAt: string;
  createdAt: string;
  authorName?: string;
}
```

### 3.2 Relationships (conceptual)

```
Workspace
  └── WorkspaceKnowledge
        ├── Document ──chunk──► Embedding
        ├── Meeting ──has──► Transcript
        │     └── produces ──► Decision | ActionItem
        ├── Report ──cites──► Document | Meeting
        ├── Policy ──backed_by──► Document
        ├── KnowledgeProject ──links──► *artefacts
        └── Tag ──labels──► *artefacts

KnowledgeRelationship edges connect any pair with a predicate.
```

Intelligence Studio and Search **never** invent edges client-side; they read `related()` / graph APIs.

---

## 4. Indexing pipeline

Every ingestible artefact (primarily Document, Meeting recording, imported Report) follows:

```
Upload
  → Extraction
  → Metadata
  → Chunking
  → Embeddings
  → Knowledge Graph
  → Search Index
  → Available to AI
```

### Stage details

| Stage | Responsibility | Outputs | Failure mode |
|-------|----------------|---------|--------------|
| **1. Upload** | Accept file(s); write to object storage; create `Document` row `status=uploading` | Storage path, checksum | Quarantine; user-visible failed |
| **2. Extraction** | Parse text/tables; optional OCR; audio → transcript job | Raw text / structured blocks; `status=extracting` | Retryable; mark `failed` with reason |
| **3. Metadata** | Title, author, dates, mime, page count, language, PII flags (future) | Metadata JSON on entity | Soft-fail with defaults |
| **4. Chunking** | Split into retrieval units with overlap; preserve headings | Chunk records `{id, documentId, ordinal, text, tokens}` | Fail indexing; keep raw extract |
| **5. Embeddings** | Vectorize chunks (server model); store vectors | Embedding rows / vector index ids | Degrade to keyword-only |
| **6. Knowledge Graph** | Extract entities/links (decisions, people, citations); write `KnowledgeRelationship` | Edges + optional Decision/ActionItem stubs | Non-blocking for “ready” |
| **7. Search Index** | Upsert keyword index (and filters: type, tags, dates, author) | Searchable docs | Block “ready” if both keyword + vector fail |
| **8. Available to AI** | Flip `status=ready`; bump workspace readiness; notify | Studio/Search can cite | Activity log `knowledge.indexed` |

### Processing status API

UI polls or subscribes to `processingStatus(knowledgeId)` / workspace batch status. States must be stable enums shared with TypeScript.

### Idempotency

Re-upload with same checksum → version bump or reject duplicate (product choice; default **new version**, keep prior for provenance). Document in decision log when implemented.

---

## 5. Component hierarchy

Proposed tree under `src/pages/OrganisationalMemory/` (implement later; ≤ ~200 lines per file):

```
pages/OrganisationalMemory/
  index.ts
  MemoryPage.tsx                 # Route shell; binds active workspace
  MemoryLayout.tsx               # Filters | Library | Preview
  library/
    KnowledgeLibrary.tsx         # Centre host
    KnowledgeTable.tsx
    KnowledgeCards.tsx           # Alternate density
    KnowledgeToolbar.tsx         # View toggle, sort, upload
  filters/
    MemoryFilters.tsx
    TagManager.tsx
    CollectionsNav.tsx           # Saved views / smart collections (later)
  detail/
    KnowledgeDetail.tsx
    KnowledgePreview.tsx
    MetadataPanel.tsx
    RelationshipViewer.tsx
    KnowledgeTimeline.tsx
  dialogs/
    UploadDialog.tsx
    ProcessingStatus.tsx
  states/
    MemoryEmptyState.tsx
    MemoryForbiddenState.tsx
```

Shared reuse: `AppShell`, `EmptyState`, `Drawer` (mobile preview), `Modal`, Horizon tokens.

### Composition rules

1. Data via `services.knowledge` only — no direct Storage SDK in leaves (optional upload signed-URL helper in service layer).
2. No business logic in JSX — filters and query builders in hooks/`lib/memory`.
3. Horizon visual language — library, not dashboard of widgets.
4. Active workspace from global `WorkspaceContext` only.

### Route map

| Route | Purpose |
|-------|---------|
| `/knowledge` | Organisational Memory (canonical) |
| `/knowledge?type=document` | Prefill type filter |
| `/knowledge/:knowledgeId` | Deep link → select + preview |
| `/library` | Redirect → `/knowledge` |
| `/memory` | Optional alias → `/knowledge` |

Nav label: keep **Library** or rename to **Memory** in a dedicated copy PR; default recommendation: nav **Library**, page title **Organisational Memory**.

Breadcrumbs: `Home › Organisational Memory` · with selection `Home › Organisational Memory › Q2 Operating Pack.pdf`.

---

## 6. Layout

### Desktop (≥ `lg`)

```
┌──────────────────────────────────────────────────────────────┐
│ AppShell: breadcrumbs · ⌘K · workspace switcher              │
├────────────┬─────────────────────────────┬───────────────────┤
│ Filters    │ Knowledge Library           │ Preview           │
│ Tags       │  (table or cards)           │ Metadata          │
│ Collections│  toolbar + pagination       │ Relationships     │
└────────────┴─────────────────────────────┴───────────────────┘
```

- Left rail ~240–280px; centre `minmax(0,1fr)`; right preview ~320–360px.
- Selecting a row updates preview without full page navigation (URL may still update for deep links).

### Mobile

- Centre library full width.
- Filters in a sheet/drawer.
- Preview in a right `Drawer` or full-screen detail route.

### Empty state

Exceptional first-run copy (not a blank table): explain that Memory feeds Studio and Reports; primary CTA **Upload documents**; secondary **Open Intelligence Studio** after corpus exists.

---

## 7. API contracts

Client access only through **`KnowledgeService`** (expand existing stub). Bearer = Supabase access token. Mock + HTTP via `createServices()` / `VITE_USE_MOCK_API`.

### 7.1 Service interface (target)

```ts
interface KnowledgeService {
  // Existing (keep)
  getSearchSuggestions(workspaceId: string, auth?: ServiceAuth): Promise<UniversalSearchPayload>;
  search(workspaceId: string, query: string, auth?: ServiceAuth): Promise</* hits */>;

  // Memory module
  listKnowledge(
    workspaceId: string,
    query: KnowledgeListQuery,
    auth?: ServiceAuth,
  ): Promise<Paginated<KnowledgeListItem>>;

  getKnowledge(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeDetail>;

  upload(
    workspaceId: string,
    input: KnowledgeUploadInput,
    auth?: ServiceAuth,
  ): Promise<KnowledgeListItem>;  // returns processing entity

  delete(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<void>;

  tag(
    workspaceId: string,
    knowledgeId: string,
    tagIds: string[],
    auth?: ServiceAuth,
  ): Promise<KnowledgeListItem>;

  related(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeRelationship[]>; // or related list items

  preview(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgePreview>;

  processingStatus(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ): Promise<KnowledgeProcessingStatus>;

  // Tag admin (Library)
  listTags?(workspaceId: string, auth?: ServiceAuth): Promise<Tag[]>;
  createTag?(workspaceId: string, label: string, auth?: ServiceAuth): Promise<Tag>;
}
```

### 7.2 Query & DTO sketches

```ts
interface KnowledgeListQuery {
  q?: string;                    // keyword
  semantic?: boolean;            // prefer vector path when true
  types?: KnowledgeEntityType[];
  tagIds?: string[];
  authorId?: string;
  projectId?: string;
  dateFrom?: string;
  dateTo?: string;
  status?: string[];
  limit?: number;
  offset?: number;
  sort?: 'updated_at' | 'created_at' | 'title' | 'relevance';
}

interface KnowledgeDetail extends KnowledgeListItem {
  metadata: Record<string, unknown>;
  storagePath?: string;
  relationships: KnowledgeRelationship[];
  processing?: KnowledgeProcessingStatus;
}

interface KnowledgePreview {
  knowledgeId: string;
  kind: 'text' | 'pdf' | 'html' | 'unsupported';
  textExcerpt?: string;
  pages?: Array<{ page: number; text: string }>;
  url?: string;                  // short-lived signed URL
}

interface KnowledgeProcessingStatus {
  knowledgeId: string;
  status: 'uploading' | 'extracting' | 'indexing' | 'ready' | 'failed';
  stage: string;                 // human-readable current stage
  progressPercent?: number;
  errorMessage?: string;
  updatedAt: string;
}

interface KnowledgeUploadInput {
  fileName: string;
  mimeType: string;
  sizeBytes: number;
  // Either multipart via API or { uploadUrl, token } two-step
}
```

### 7.3 HTTP mapping (illustrative)

| Method | Path |
|--------|------|
| `GET` | `/api/v1/workspaces/:id/knowledge` |
| `GET` | `/api/v1/workspaces/:id/knowledge/:kid` |
| `POST` | `/api/v1/workspaces/:id/knowledge/upload` |
| `DELETE` | `/api/v1/workspaces/:id/knowledge/:kid` |
| `POST` | `/api/v1/workspaces/:id/knowledge/:kid/tags` |
| `GET` | `/api/v1/workspaces/:id/knowledge/search` |
| `GET` | `/api/v1/workspaces/:id/knowledge/:kid/related` |
| `GET` | `/api/v1/workspaces/:id/knowledge/:kid/preview` |
| `GET` | `/api/v1/workspaces/:id/knowledge/:kid/processing` |

Backend should wrap existing document/report repositories and future index workers — **no duplicated business rules in React**.

---

## 8. State management

| Concern | Location |
|---------|----------|
| Active workspace | `WorkspaceContext` (global) |
| Filters / search query | Page URL query params + hook `useMemoryFilters` (shareable links) |
| Selection (`knowledgeId`) | URL param or local state synced to URL |
| Preview payload | Derived from `getKnowledge` / `preview` query |
| Processing | Poll `processingStatus` while `status !== ready\|failed` |
| Pagination | `limit` / `offset` (or cursor later) in list query |
| View mode (table/cards) | Local preference `localStorage` key `dde.memory.view` |

No Redux. Prefer hooks:

- `useMemoryLibrary(workspaceId, query)`
- `useMemorySelection(knowledgeId)`
- `useMemoryProcessing(knowledgeId)`
- `useMemoryTags(workspaceId)`

---

## 9. Search architecture

Library search and Universal Search share **server** retrieval; UIs differ.

| Dimension | Behaviour |
|-----------|-----------|
| **Keyword** | Full-text / ILIKE / search engine over titles + chunk text |
| **Semantic** | Embedding kNN over chunks; return parent artefacts |
| **Tag** | Filter `tagIds` |
| **Author** | Filter uploader / owner |
| **Date** | `createdAt` / `updatedAt` / `heldAt` range |
| **Document type** | `KnowledgeEntityType` (+ mime family) |
| **Project** | `projectRefId` / `KnowledgeProject` link |

**Hybrid default:** keyword + semantic fusion when `q` present; pure filters when `q` empty.

**Ranking:** relevance when searching; `updated_at` when browsing.

Universal Search on Home remains a thin client of `KnowledgeService.search` / suggestions — not a second index.

---

## 10. Permissions

| Layer | Role |
|-------|------|
| **Supabase RLS** | Hard isolation by workspace membership |
| **FastAPI** | Re-check membership; plan gates for OCR / connectors / storage quotas |
| **React** | Fail-closed capability flags only |

```ts
interface MemoryCapabilities {
  canView: boolean;
  canUpload: boolean;      // align with WorkspaceCapabilities.canUpload
  canDelete: boolean;      // owner/admin/editor policy TBD
  canTag: boolean;
  canManageTags: boolean;  // admin+
  canUseSemanticSearch: boolean; // plan-aware
  canUseConnectors: boolean;     // plan-aware; later
}
```

Viewers: read + search. Editors+: upload/tag. Destructive delete: fail closed unless role allows.

Plan awareness: semantic search, OCR, and external connectors may 402/403 from API with a `notice`; UI disables or explains — never bypass.

---

## 11. Extension points

| Extension | Hook |
|-----------|------|
| **Knowledge Graph UI** | `RelationshipViewer` + graph query API |
| **OCR** | Extraction stage flag; processing status |
| **Versioning** | Document versions table; preview “as of” |
| **External connectors** | Ingest workers writing the same `Document` model |
| SharePoint / Google Drive / OneDrive | Connector adapters → Upload pipeline |
| Slack / Email | Message → Document or Meeting artefact |
| Confluence / Notion | Page import → Document + relationships |
| Realtime processing | Websocket/SSE on `processingStatus` |
| Retention / legal hold | Cross-link Workspace settings; Memory respects hold flags |

### Explicit non-goals (near term)

- Editing report narrative inside Library
- Running Intelligence Studio inside Memory
- Client-side embeddings
- Service-role keys in the browser
- Recreating Streamlit document UI pixel-for-pixel

---

## 12. Definition of Done (architecture gate)

This architecture is **approved for implementation** when:

- [ ] Domain ownership boundaries are accepted (esp. vs Studio / Report Studio / Workspace)
- [ ] Entity set and relationships in §3 are accepted (including `KnowledgeProject` naming)
- [ ] Indexing pipeline stages and status enums in §4 are accepted
- [ ] `KnowledgeService` methods in §7 are accepted as the client contract
- [ ] Search dimensions in §9 are accepted
- [ ] Permissions fail-closed + plan-aware stance in §10 is accepted
- [ ] Extension points in §11 are acknowledged as non-blocking for v1
- [ ] Links from `README` / `BACKEND_INTEGRATION` point here

When the above hold, UI/API work may begin **without architectural ambiguity**. Any deviation requires a decision-log entry in §13.

### Implementation readiness checklist (first Memory UI PR — later)

1. Expand `KnowledgeService` types + Mock/HTTP for `listKnowledge`, `getKnowledge`, `upload`, `processingStatus`.
2. Ship `MemoryPage` layout with empty state + upload dialog.
3. Table/cards + filters; preview pane.
4. Wire search hybrid behind service; no client RAG.
5. Update Intelligence Studio readiness to consume real corpus counts when API exists.

---

## 13. Decision log

| Date | Decision |
|------|----------|
| 2026-07-25 | Organisational Memory is the knowledge backbone; Studio/Search/Agents consume it |
| 2026-07-25 | Canonical route `/library`; optional `/memory` alias |
| 2026-07-25 | Phase 4: canonical route `/knowledge` (+ `/knowledge/:id`); `/library` redirects |
| 2026-07-25 | Expand existing `KnowledgeService` rather than inventing a second client service name |
| 2026-07-25 | Use `KnowledgeProject` in TypeScript to avoid collision with Workspace `Project` DTO |
| 2026-07-25 | Indexing pipeline is server-side; UI only observes `processingStatus` |
| 2026-07-25 | Graph enrichment is non-blocking for artefact `ready` status |
| 2026-07-25 | This document is the implementation gate — no Memory UI before DoD in §12 |
