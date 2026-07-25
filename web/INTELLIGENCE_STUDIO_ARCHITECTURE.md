# Intelligence Studio Architecture

**Status:** Implemented (Phase 3 UI) — keep this document updated when Studio APIs or modes change.  
**Scope:** Authenticated React app (`web/`) Intelligence Studio module and the FastAPI product surface it will call.  
**Related:** [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md), [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md), Home Insights drawer (read-only intelligence), Streamlit `AskCopilotUseCase` / `CopilotContextService`.

This document is the source of truth for Intelligence Studio decisions. Prefer extending it over inventing patterns in PRs.

---

## 1. Domain responsibilities

### What Intelligence Studio is

**Intelligence Studio** is the interactive AI workspace for asking questions, exploring grounded answers, and acting on organizational knowledge **within the active Workspace**.

It is not a second Home dashboard. It is not report authoring. It is the conversational / investigative surface that sits on top of indexed documents, reports, and (when entitled) live web research.

```
Intelligence Studio
├── Conversation (threads, turns, composer)
├── Grounding (workspace corpus + optional web)
├── Citations & sources
├── Modes (ask / deepen / focus-on-report)     [phased]
├── Side panel (sources, readiness, suggested prompts)
└── Handoffs (open report, upload docs, create report)
```

### Naming note (important)

| Layer | Current name | Meaning |
|-------|--------------|---------|
| Product UI / breadcrumbs / ⌘K | **Intelligence Studio** | User-facing name |
| React route (today) | `/copilot` | Keep path stable for bookmarks; label is Intelligence Studio |
| Streamlit | Copilot | Legacy UI being replaced |
| Python use case | `AskCopilotUseCase` | Server orchestration to wrap, not reimplement in React |
| Python model | `CopilotResult` | Answer + sources + notice |
| Frontend `AIService` (today) | Brief / recommendations / insights | **Read models** for Home drawer — not the Studio chat API |

**Rule for new code:** user-facing copy says **Intelligence Studio**. Code may keep `copilot` in route ids and Python module names until a deliberate rename. Do not introduce a third brand (e.g. “AI Chat”, “Assistant Hub”) without updating this doc.

### Intelligence Studio owns

- Asking questions against the **active workspace** context
- Rendering answers with citations, source lists, and plan/entitlement notices
- Conversation thread UI (local first; server-persisted later)
- Suggested prompts / starter chips derived from workspace readiness
- Focus context (optional “focus report” or document) for a turn
- Handoffs to Documents, Reports, and Workspace Insights (navigation only)
- Client-side orchestration hooks that call `services.ai` / future `IntelligenceService` — **no model calls from the browser**

### Intelligence Studio does **not** own

| Concern | Owner |
|---------|--------|
| Workspace CRUD, team, settings | Workspace module |
| Document upload / indexing | Knowledge / Documents (AI Workspace) |
| Report generation pipelines & editors | Reports module |
| Export / publish job runners | Publish module |
| Dense “Today’s Brief / Recommendations” cards on Home | Home Insights drawer (read-only aggregates via `AIService`) |
| Auth, billing, plan entitlement evaluation | Auth / Plan services (server) |
| Marketing site | `marketing-site/` |

**Boundary with Home Insights:** Home shows *summaries*. Intelligence Studio is where the user *asks and investigates*. Do not duplicate the Insights drawer as a third dashboard inside Studio.

**Boundary with Universal Search:** Search finds and navigates. Studio answers with grounded synthesis. Search may deep-link into Studio with a prefilled question; Studio must not become a raw search results page.

---

## 2. Component hierarchy

Proposed tree under `src/pages/IntelligenceStudio/` (implement later; keep files ≤ ~200 lines):

```
pages/IntelligenceStudio/
  index.ts
  IntelligenceStudioPage.tsx          # Route shell; binds active workspace
  StudioHeader.tsx                    # Title, readiness chip, focus control
  StudioLayout.tsx                    # Main chat + optional sources rail
  conversation/
    ConversationPane.tsx              # Scrollable thread
    MessageBubble.tsx                 # User / assistant turns
    Composer.tsx                      # Input, send, stop, attachments stub
    SuggestedPrompts.tsx              # Empty-state / idle chips
    StreamingIndicator.tsx            # Typing / token progress
  sources/
    SourcesPanel.tsx                  # Workspace + web citations
    SourceCitation.tsx
    FocusContextPicker.tsx            # Optional report/doc focus
  states/
    StudioEmptyState.tsx              # No corpus / first ask
    StudioForbiddenState.tsx
    StudioOfflineState.tsx
  hooks/                              # page-local hooks only if not shared
```

Shared (reuse from Phase 1–2):

```
components/
  layout/AppShell.tsx                 # Global switcher, breadcrumbs, ⌘K
  ui/EmptyState.tsx, Button, Input…
  drawers/…                           # Prefer drawer for mobile sources rail
```

### Composition rules

1. **Pages compose; panes receive props or thin hooks** — no `fetch` in leaf components.
2. **No LLM prompts, temperature, or API keys in React** — only typed service calls.
3. **Reuse Horizon visual language** — canvas, whitespace, Inter/tokens, no purple-glow AI clichés.
4. **One primary job per viewport** — conversation is the hero; sources are secondary.
5. **Workspace context comes from the shell** — do not add a second workspace picker inside Studio (use global switcher).

### Suggested route map

| Route | Purpose |
|-------|---------|
| `/copilot` | Intelligence Studio (canonical for v1) |
| `/copilot?q=` | Prefill composer from search / ⌘K |
| `/copilot?thread=` | Open persisted thread (later) |
| `/intelligence` | Optional alias redirect → `/copilot` (nice-to-have) |

Sidebar / ⌘K label: **Intelligence Studio** (replace “Copilot” in nav copy when implementing). Keep `ROUTES.copilot === '/copilot'`.

Breadcrumbs example:

`Home › Intelligence Studio`

When a thread title exists later:

`Home › Intelligence Studio › Margin anomaly in EMEA`

---

## 3. Layout

### Desktop (≥ `lg`)

```
┌──────────────────────────────────────────────────────────────┐
│ AppShell top bar: breadcrumbs · ⌘K · workspace switcher      │
├──────────────┬───────────────────────────────┬───────────────┤
│ Sidebar      │ StudioHeader                  │ SourcesPanel  │
│              │ ConversationPane              │ (citations,   │
│              │   …messages…                  │  readiness,   │
│              │ Composer (sticky bottom)      │  focus)       │
└──────────────┴───────────────────────────────┴───────────────┘
```

- Main column ~minmax(0, 1fr); sources rail ~320–360px.
- Composer sticky within the main column, not the viewport under the top bar.
- Generous whitespace; avoid multi-widget dashboards above the thread.

### Tablet / mobile

- Single column: conversation + composer.
- Sources open in a **right Drawer** (reuse `components/drawers/Drawer`).
- Suggested prompts collapse into a horizontal chip scroller.

### Empty / first-run layouts

| Condition | Treatment |
|-----------|-----------|
| Workspace has no indexed docs/reports | Empty state: explain grounding; CTA → Documents / upload |
| AI not ready (`WorkspaceAI.ready === false`) | Readiness banner + disabled composer with clear reason |
| Entitlement blocks web research | Inline notice on answers (server `notice` field) — do not hide Ask |
| Zero threads | Suggested prompts + short product sentence (not a marketing wall) |

---

## 4. AI orchestration

### Principles

1. **Server owns intelligence** — FastAPI wraps existing Python (`AskCopilotUseCase`, `CopilotContextService`, `AIService`, plan gates). React never calls OpenAI directly.
2. **Workspace-scoped** — every ask includes `workspaceId` (= project id). Context assembly stays on the server.
3. **Fail closed on secrets** — no service-role or model keys in `VITE_*`.
4. **Optimistic UX, authoritative server** — show pending user message immediately; replace/stream assistant turn from API.
5. **Citations are data** — render from typed `sources` / `webSources`; do not parse prose for links as the primary citation model.
6. **Streaming is a phase-2 enhancement** — v1 may be request/response; design types so `delta` events can attach later without rewriting bubbles.

### Turn lifecycle (v1 — non-streaming)

```
User submits prompt
  → Composer disabled / Stop unused
  → Append local user message (temp id)
  → POST /api/v1/workspaces/:id/intelligence/ask
  → Append assistant message from CopilotAnswerDTO
  → Log activity server-side (copilot.asked)
  → Re-enable composer
```

### Turn lifecycle (later — streaming)

```
POST …/ask?stream=1  (SSE or fetch stream)
  → assistant message status: streaming
  → append text deltas
  → final event carries sources + notice + message id
  → status: complete | error
```

### Modes (phased)

| Mode | Behavior | Phase |
|------|----------|-------|
| `ask` | Default grounded Q&A | v1 |
| `focus` | Pass `focusReportId` / document id into use case | v1 optional |
| `web` | Entitlement-gated; server already decides via plan | v1 (server-driven) |
| `deep` | Plan `can_use_deep_copilot` — server flag only | v1 (opaque to UI) |
| `studio` tools (generate outline → Reports) | Handoff, not inline generation | later |

UI may show a compact “Using workspace · Web research on/off” status derived from **server response metadata**, not from client plan math.

### Relationship to existing Python

Prefer a thin FastAPI adapter:

`POST …/intelligence/ask` → `AskCopilotUseCase.execute(project_id=…, question=…, focus_report=…)` → map `CopilotResult` → camelCase DTO.

Do **not** reimplement context assembly in TypeScript.

---

## 5. API contracts

All routes under `/api/v1`. Bearer = Supabase access token. Client access only through service interfaces (extend `AIService` **or** introduce `IntelligenceService` — see §5.3).

### 5.1 Types to add (before UI)

```ts
interface IntelligenceSource {
  id: string;
  kind: 'document' | 'report' | 'knowledge' | 'web';
  title: string;
  location?: string;      // path, report filename, or URL
  excerpt?: string;
}

interface IntelligenceAskInput {
  question: string;
  focusReportId?: string;
  focusDocumentId?: string;
  threadId?: string;      // ignored until persistence ships
}

interface IntelligenceAskResult {
  answer: string;
  workspaceId: string;
  workspaceName: string;
  sources: IntelligenceSource[];      // mapped from CopilotResult.sources
  webSources: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  notice: string | null;              // plan / web unavailable messaging
  createdAt: string;                  // ISO
}

interface IntelligenceThread {
  id: string;
  workspaceId: string;
  title: string;
  updatedAt: string;
}

interface IntelligenceMessage {
  id: string;
  threadId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: IntelligenceSource[];
  webSources?: IntelligenceAskResult['webSources'];
  notice?: string | null;
  status: 'pending' | 'streaming' | 'complete' | 'error';
  createdAt: string;
}

interface StudioReadiness {
  ready: boolean;
  status: string;                     // mirrors WorkspaceAI.status
  documentCount: number;
  reportCount: number;
  canAsk: boolean;                    // capability + readiness
  webResearchAvailable: boolean;      // from plan endpoint or ask metadata
}
```

Map from Python `CopilotResult`:

| Python | TypeScript |
|--------|------------|
| `answer` | `answer` |
| `project_name` | `workspaceName` |
| `sources: list[str]` | `sources[]` (promote strings → `{ kind, title }` in adapter) |
| `web_sources` | `webSources` |
| `notice` | `notice` |

### 5.2 HTTP surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/workspaces/:id/intelligence/readiness` | Composer enablement + empty states |
| `POST` | `/api/v1/workspaces/:id/intelligence/ask` | Synchronous ask (v1) |
| `POST` | `/api/v1/workspaces/:id/intelligence/ask/stream` | SSE/stream (later) |
| `GET` | `/api/v1/workspaces/:id/intelligence/threads` | List threads (later) |
| `GET` | `/api/v1/workspaces/:id/intelligence/threads/:threadId` | Thread + messages (later) |
| `DELETE` | `/api/v1/workspaces/:id/intelligence/threads/:threadId` | Archive thread (later) |
| `GET` | `/api/v1/workspaces/:id/intelligence/suggestions` | Suggested prompts (optional v1) |

Reuse existing read aggregates where useful (do not block Studio on them):

- `AIService.getTodaysBrief` / `getRecommendations` / `listInsights` — Home drawer only unless Studio explicitly shows a “From today’s brief” chip that **prefills** the composer.

### 5.3 Service layer decision

**Preferred:** introduce `IntelligenceService` in `src/api/services/` for chat/readiness/threads, and keep `AIService` for Home insight cards. Avoid bloating `AIService` into two product surfaces.

```ts
interface IntelligenceService {
  getReadiness(workspaceId: string, auth?: ServiceAuth): Promise<StudioReadiness>;
  ask(workspaceId: string, input: IntelligenceAskInput, auth?: ServiceAuth): Promise<IntelligenceAskResult>;
  listSuggestions?(workspaceId: string, auth?: ServiceAuth): Promise<string[]>;
  // later: listThreads, getThread, deleteThread, askStream
}
```

Mock + HTTP pair via `createServices()` / `VITE_USE_MOCK_API`, same as Workspace.

---

## 6. State management

### Principles

1. **Active workspace** — `WorkspaceContext.activeWorkspaceId` only (already global).
2. **Server state** — readiness, ask results, threads → hooks calling `services.intelligence`.
3. **Conversation state** — v1: page-local React state (messages array). Later: React Query / cache keyed by `workspaceId + threadId`.
4. **URL** — `/copilot` + optional `q` / `thread` query params; do not put full transcripts in the URL.
5. **No Redux** unless multi-surface conversation sharing forces it.

### Hook map

| Hook | Responsibility |
|------|----------------|
| `useWorkspace()` | Active workspace id |
| `useStudioReadiness(workspaceId)` | Enable composer / empty states |
| `useStudioConversation(workspaceId)` | Messages, sendAsk, reset, error |
| `useStudioPermissions(workspaceId)` | Capability flags (fail-closed) |
| `useBreadcrumbs()` | Already global — extend label for Studio |

### Conversation rules

- Switching workspace **clears** the in-memory thread (v1) or prompts “Start new conversation” if dirty.
- Failed asks keep the user message and show an assistant error bubble or toast — do not silently drop the turn.
- Stop button: v1 no-op or aborts `AbortController` on fetch; streaming phase wires cancel.

---

## 7. Permissions & entitlements

### Enforcement model

| Layer | Role |
|-------|------|
| **Supabase RLS** | User can only hit workspaces they belong to |
| **FastAPI** | Membership check + plan gates (`PlanService`) before context/web/LLM |
| **React** | UX gating only |

### Capability flags (Studio-specific)

Extend or compose with `WorkspaceCapabilities`:

```ts
interface StudioCapabilities {
  canView: boolean;           // member of workspace
  canAsk: boolean;            // editor+ (or viewer if product allows ask-only)
  canUseWebResearch: boolean; // from plan — display only; server enforces
  canUseDeepContext: boolean; // from plan — opaque
  canFocusReport: boolean;    // canAsk && reports exist
}
```

**Recommended v1 policy:** `canAsk` for `owner | admin | editor | reviewer`; `viewer` read-only (browse prior threads later, no ask). Confirm with product before coding; until then **fail closed** → viewers cannot send.

### Notices

Plan limitations surface as `IntelligenceAskResult.notice` (already modeled in Streamlit). UI must render notices verbatim near the answer — do not invent alternate copy that contradicts billing.

---

## 8. Navigation & product flow

```
AppShell
  ⌘K → “Launch Intelligence Studio” → /copilot
  Global workspace switcher → Studio refetches readiness / clears thread
  Home Insights → optional “Ask in Studio” chip (prefill q=)
  Universal Search → “Ask Studio about …” → /copilot?q=
  Documents empty CTA → upload, then return to Studio
  Assistant citation click → open report/document route (Reports / Documents)
```

### Deep links

- Cold load `/copilot` with stored `dde.activeWorkspaceId`.
- If no active workspace → empty state CTA to `/workspaces`.
- Forbidden workspace → same forbidden pattern as Workspace module.

---

## 9. Future extension points

| Extension | Hook point |
|-----------|------------|
| Streaming tokens | `askStream` + `MessageBubble` status |
| Persisted threads | `IntelligenceThread` APIs + sidebar thread list |
| Multi-modal attach | Composer → Documents upload handoff first |
| Tool calls (create report draft) | Server tools → navigate to Reports with draft id |
| Eval / feedback | Thumbs on assistant turn → `POST …/feedback` |
| Shared threads | Membership + RLS on thread rows |
| Voice input | Composer enhancement only |
| Per-workspace system instructions | Server config; never free-form secrets in UI |
| Rename route `/copilot` → `/intelligence` | Alias + redirect; update this doc |

### Explicit non-goals (near term)

- Calling OpenAI / Anthropic from the browser
- Rebuilding Home Insights inside Studio
- Client-side RAG / embedding
- Recreating Streamlit Copilot pixel-for-pixel
- Autonomous agents that mutate workspace data without an explicit user confirm handoff
- Service-role keys in the SPA

---

## 10. Definition of Done (implementation gate)

Do not merge the Intelligence Studio UI PR until **all** of the following are true:

### Architecture & contracts

- [ ] `IntelligenceService` (or approved `AIService` extension) exists with Mock + HTTP implementations
- [ ] Types from §5.1 live under `src/types/` and are the only shapes the UI consumes
- [ ] FastAPI route plan documented in [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) (even if still mock-backed)
- [ ] This file’s decision log updated with any policy deviations

### Product behavior

- [ ] Route `/copilot` renders Studio inside `AppShell` with breadcrumbs **Home › Intelligence Studio**
- [ ] Uses **global** workspace switcher only; no duplicate selector in the page header
- [ ] Composer disabled with explanation when readiness/`canAsk` fails (fail-closed)
- [ ] Successful ask renders answer + sources + optional `notice`
- [ ] Empty corpus state CTA points at Documents / Workspaces — exceptional copy, not a blank pane
- [ ] ⌘K “Launch Intelligence Studio” still lands here
- [ ] Workspace switch clears or safely resets the in-progress thread

### Quality bar (match Phase 1–2)

- [ ] Components ≤ ~200 lines; no duplicated JSX blobs
- [ ] No hard-coded product sentences outside `UI_COPY` / API DTOs
- [ ] Accessible composer (label, focus, Escape closes panels)
- [ ] Responsive: sources as drawer on small screens
- [ ] `npm run build` passes
- [ ] Does not modify `marketing-site/` or weaken RLS assumptions

### Out of scope for the first UI PR (explicitly deferred)

- Streaming
- Thread persistence
- Inline report generation
- Web research toggles that bypass server plan checks

---

## 11. Implementation checklist (ordered)

1. Add types (`IntelligenceAskInput`, `IntelligenceAskResult`, `StudioReadiness`, …).
2. Add `IntelligenceService` + mock fixtures shaped like FastAPI responses.
3. Wire `createServices()`; document routes in `BACKEND_INTEGRATION.md`.
4. Replace `/copilot` placeholder with `IntelligenceStudioPage` shell + empty/readiness states.
5. Ship Composer + ConversationPane + SourcesPanel (non-streaming ask).
6. Hook permissions + readiness; fail closed.
7. Prefill from `?q=`; clear thread on workspace change.
8. Update nav/breadcrumb copy to **Intelligence Studio**.
9. Only then: streaming / threads as follow-up PRs against §8.

---

## 12. Decision log

| Date | Decision |
|------|----------|
| 2026-07-25 | User-facing name is **Intelligence Studio**; route remains `/copilot` for v1 |
| 2026-07-25 | Server wraps `AskCopilotUseCase`; no browser-side LLM calls |
| 2026-07-25 | Prefer new `IntelligenceService` separate from Home `AIService` insight cards |
| 2026-07-25 | Home Insights drawer stays the dense summary surface; Studio is interactive Q&A |
| 2026-07-25 | Global workspace switcher is the only workspace control; Studio does not fork context |
| 2026-07-25 | v1 is synchronous ask; streaming and persisted threads are explicit later phases |
| 2026-07-25 | This document is the implementation gate — UI work must not start without §10 DoD awareness |
| 2026-07-25 | Phase 3 UI shipped: conversations list, ask flow, evidence panel, modes (placeholder), mock IntelligenceService |
