# DataDumpAI Enterprise — System Architecture

This document describes the overall system design: how components interact, where data lives, and how traffic flows from the public internet to application services.

For server-specific deployment details (IPs, SSH, rollback commands), see [PRODUCTION.md](./PRODUCTION.md).

> **This document was rewritten to match what's actually running in production.** The previous version described Streamlit as the primary authenticated application. That's no longer true: the product was rebuilt as a FastAPI + React SPA. Streamlit (`app.py`, `ui/`, `application/`, and the `core/*.py`/`services/*.py` modules exclusive to it) had zero live traffic since that rebuild and has since been deleted from the repo entirely, along with its Docker service — see "Version history" below.

---

## Overview

DataDumpAI Enterprise is a multi-surface product:

| Surface | Technology | Role |
|---------|------------|------|
| **Marketing site** | Next.js 15 (App Router) | Public homepage, SEO, pricing, docs, contact |
| **Application** | FastAPI (`api/`) + React SPA (`web/`) | Authenticated workspace — projects, documents, AI reports, billing |
| **Webhook service** | FastAPI (`api/webhook_server.py`) | Paystack (and dormant Stripe) subscription events |
| **Vector search** | Qdrant | Document chunk embeddings for retrieval-grounded report generation |
| **Platform backend** | Supabase | Auth, PostgreSQL metadata, object storage |

The marketing site and application are **separate deployables** on the same server, fronted by Nginx.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Public Internet                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Nginx (host :443)     │
                    └───────────┬───────────┘
            ┌───────────────────┼───────────────────┐
            │                   │                   │
   www.getdatadump.com    app.getdatadump.com       │
            │                   │                   │
   ┌────────▼────────┐  ┌───────▼────────┐         │
   │  PM2 :3000      │  │ Docker         │         │
   │  Next.js        │  │ frontend :3001 │         │
   │  marketing-site │  │ (React SPA +   │         │
   │                 │  │  nginx)        │         │
   └────────┬────────┘  └───────┬────────┘         │
            │                   │ same-origin       │
            │ Launch App        │ /api/* proxy      │
            └──────────────────►│                   │
                                ┌▼──────────────┐    │
                                │ Docker api    │    │
                                │ :8000         │    │
                                │ (FastAPI)     │◄───┼── Docker qdrant :6333
                                └───────┬───────┘    │
                                        │             │
                                        │  ┌──────────▼──────────┐
                                        │  │ Docker webhooks :8001│
                                        │  │ (Paystack/Stripe)    │
                                        │  └──────────┬───────────┘
                                        │             │
                              ┌─────────▼─────────────▼──┐
                              │      Supabase Cloud      │
                              │  Auth · Postgres · Storage│
                              └─────────────────────────┘
                                           │
                              ┌────────────▼────────────┐
                              │       OpenAI API         │
                              └─────────────────────────┘
```

---

## Application: FastAPI + React SPA

**Backend entry point:** `api/app.py` (product API), `api/webhook_server.py` (payment webhooks, separate process)
**Frontend entry point:** `web/` — a Vite/React SPA, built to static files and served by its own nginx inside the `frontend` container (`web/nginx.conf`)

This is what a real user actually reaches at `app.getdatadump.com` today. Verified directly: `GET /` returns the SPA shell; `GET /api/v1/health` returns `{"status":"ok"}` from FastAPI.

### Responsibilities

- User authentication (Supabase Auth, JWT-verified per request in `api/deps.py`)
- Projects ("workspaces") — create, list, document upload, background indexing status
- Document library — multi-format extraction (PDF via 3 engines + OCR fallback, DOCX, XLSX/CSV with verified numeric stats, TXT)
- Retrieval-grounded AI report generation (`services/spa_report_generation_service.py` + `services/report_retrieval_service.py`) — reports are generated from semantically-retrieved document chunks via Qdrant, not a blind dump of the first N documents
- "Ask AI" / Intelligence Studio chat — real RAG over the workspace's indexed documents, with optional live web search
- Report export: PDF / DOCX / PPTX, plan-gated
- Billing UI (Paystack checkout; Stripe code path exists but is hard-disabled at the service layer)

### Application layers

```
api/
├── app.py                      ← FastAPI entry, mounts routers under /api/v1
├── webhook_server.py            ← Separate FastAPI process for payment webhooks
├── deps.py                      ← JWT auth, per-request principal/access-token resolution
├── auth_jwt.py                  ← AuthenticatedPrincipal
├── schemas/                     ← Pydantic request/response models
└── routers/                     ← workspaces, knowledge, reports, intelligence, billing, me, home, public

web/
├── src/pages/                   ← Home, Knowledge (Library), Account, Billing
├── src/components/
├── src/services/                ← Typed API clients (fetch wrappers per router)
└── nginx.conf                   ← Serves the built SPA; proxies /api/ → api:8000 same-origin

services/                        ← Shared business logic (used by api/, NOT by the dead Streamlit stack
│                                   except services/ai_service.py, which is Streamlit-only)
├── document_processor.py        ← Text/table extraction per file type
├── indexing_service.py          ← extract → chunk → embed → Qdrant upsert pipeline
├── report_retrieval_service.py  ← Facet-query retrieval + evidence assembly for report generation
├── spa_report_generation_service.py  ← Report prompt construction + OpenAI call + save
├── intelligence_rag_service.py  ← RAG for the chat/Copilot feature
├── report_service.py            ← Report persistence
├── project_service.py, document_service.py  ← Project/document persistence
├── billing_service.py           ← Paystack/Stripe facade
└── ...

core/
├── current_user.py              ← Request-scoped CurrentUser via ContextVar; the only mechanism
│                                   for api/ and services/. Fails closed (raises
│                                   AuthenticationRequiredError / returns None) when no override is
│                                   bound — no fallback to anything else.
└── database.py                  ← Supabase client, user-scoped and service-role

repositories/                    ← Data access (Supabase or JSON fallback), shared
storage/file_store.py            ← Blob storage abstraction (Supabase Storage or local filesystem), shared
qdrant/                          ← (external service, see docker-compose.yml) — chunk vectors, one
                                    collection, tenant-isolated by a workspace_id payload filter
```

### Request lifecycle

1. Browser loads the SPA from `frontend` (nginx serves static files, or `index.html` for client-side routes).
2. SPA calls `/api/...` same-origin; `frontend`'s nginx proxies these to `api:8000`.
3. `api/deps.py` verifies the Supabase JWT and resolves an `AuthenticatedPrincipal`; route handlers wrap their body in `user_request_scope(principal)`, which binds `core/current_user.py`'s request-scoped `CurrentUser` for the duration of the request.
4. Services (`ProjectService`, `DocumentService`, `ReportService`, etc.) read/write through `repositories/` (Supabase Postgres or local JSON) and `storage/file_store.py` (Supabase Storage or local filesystem), using the request's access token — not a global/shared client — so tenant isolation follows the token, not application logic.
5. Document upload triggers a background indexing job (`services/indexing_service.py`): extract text → chunk → embed (OpenAI) → upsert into Qdrant, tagged with `workspace_id`.
6. Report generation retrieves relevant chunks from Qdrant per a set of fixed "facet" queries (summary/findings/risks/opportunities/recommendations + the user's instructions), assembles evidence within a character budget, and calls OpenAI to write the report — see `services/report_retrieval_service.py`.

### Known pitfalls (read before touching auth-adjacent code)

- **Current-user resolution**: every live-path service must resolve the current user via `core.current_user` (a bound `CurrentUser`, or `require_current_user()`). This used to have a second, Streamlit-session-backed mechanism (`core/auth.py`) that a live service could accidentally call directly — that bug broke checkout in production once and was found in two other services before `core/auth.py` was deleted along with the rest of the Streamlit stack. `core/current_user.py` now has no fallback of any kind; a missing binding fails closed immediately.
- **Workspace vs Project**: the API and UI call the top-level container a "workspace," but it is implemented as a single-level project — there is no multi-project-per-organization nesting, and no `WorkspaceType`/`SubscriptionPlan` database enum. Treat "workspace" and "project" as the same thing when reading this codebase.

---

## Retired: the original Streamlit application

The product's original implementation — `app.py`, `ui/` (67 files), `application/`, `services/ai_service.py`, plus a dozen `core/*.py` modules that existed only to support it (`auth.py`, `navigation.py`, `auth_callbacks.py`, and others) — has been deleted from the repo. It had zero live traffic since the FastAPI + React SPA rebuild; deletion just made that unreachability permanent by removing the code and its Docker service (`app`, port 8501) rather than leaving it dormant. Two shared, still-live files (`services/auth_service.py`, `core/database.py`'s admin-user HTTP helpers) had a couple of diagnostic-only calls into Streamlit-coupled tracing modules — those calls were replaced with plain logging rather than deleting the surrounding (real, non-Streamlit) auth logic. See git history around the "Retire dead Streamlit stack" commit for the full file list.

Not yet done (tracked separately, non-blocking): trimming the now-unused `streamlit` package and its companions from `requirements.txt` (blocked on a small refactor of `services/notification_service.py`, which still imports it for an in-app notification feature that was never reachable outside a real Streamlit session), and the matching `Dockerfile`/CI-script cleanup.

---

## Next.js marketing site

**Location:** `marketing-site/`
**Framework:** Next.js 15, TypeScript, Tailwind CSS, App Router

### Responsibilities

- Public product homepage and brand presence
- SEO (metadata API, JSON-LD, sitemap, robots.txt)
- Marketing pages: Features, Solutions, Industries, Pricing, About, Contact
- Legal pages: Privacy, Terms, Security
- "Launch App" CTA → links to the React SPA at `NEXT_PUBLIC_APP_URL`
- Contact form → wired to a real backend endpoint (`api/routers/public.py`), not client-side-only

### Runtime

- **Development:** `npm run dev` → `localhost:3000`
- **Production:** `npm run build && npm start` under PM2 on port 3000
- Nginx proxies `getdatadump.com` / `www.getdatadump.com` → `:3000`

The marketing site has no backend of its own beyond that one contact-form call into the product API.

---

## FastAPI webhook service

**Entry point:** `api/webhook_server.py`
**Runtime:** Separate Docker container (`webhooks`, same image as the other Python services, different `uvicorn` command), port 8001

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Container health check |
| `POST` | `/webhooks/paystack` | Paystack charge/subscription events (primary, active) |
| `POST` | `/webhooks/stripe` | Stripe subscription lifecycle events (code path present but Stripe checkout is hard-disabled at the service layer — see `services/billing_service.py`) |

Events update subscription state via `billing_repository` using the Supabase service-role client (not a per-request user token, since webhooks have no authenticated user).

---

## Storage

DataDumpAI uses a dual-storage model: **metadata in PostgreSQL**, **blobs in object storage**, both with a local-filesystem/JSON fallback for development.

### Metadata (Supabase PostgreSQL)

When `DATABASE_BACKEND=supabase`, application records live in Supabase (`user_profiles`, `user_usage`, `projects`, `documents`, `reports`, `subscriptions`, `activity_logs`, `login_lockouts`). Schema in `supabase/migrations/001` through `008`; Row Level Security enforces per-user isolation.

**Fallback:** `DATABASE_BACKEND=json` stores metadata as JSON files under `data/users/{user_id}/` (development only).

### File blobs (Supabase Storage)

When `STORAGE_BACKEND=supabase`, files live in the private bucket `datadumpai-files` at `{user_id}/{project_id}/{category}/{filename}` (`documents`, `reports`, `exports`). Access is controlled by Supabase Storage policies; the server uses `SUPABASE_SERVICE_ROLE_KEY` for privileged operations.

**Fallback:** `STORAGE_BACKEND=local` writes to `data/users/{user_id}/projects/{project_id}/` on disk — the `app_data` Docker volume in production, shared across the `app`, `api`, and `webhooks` containers (not `frontend`, which serves only static files and has no backend logic).

### Vector storage (Qdrant)

New since the retrieval-grounded report generation work: `services/qdrant_service.py` upserts one point per document chunk, embedded with OpenAI `text-embedding-3-small`, tagged with a `workspace_id` payload field. All queries filter strictly by `workspace_id`, which is the tenant-isolation boundary at this layer — the actual "does this user own this workspace" check happens one layer up, at project ownership resolution (`ProjectService.get_project`), before a `workspace_id` ever reaches Qdrant. Data persists in the `qdrant_data` Docker volume.

---

## Supabase integration

Supabase is the production platform backend for auth, database, and file storage.

- Email/password sign-up with email confirmation; password reset via magic link; anonymous sign-ins disabled in production.
- `AUTH_REDIRECT_URL` must match the SPA domain (`https://app.getdatadump.com`).
- `AUTH_DEV_BYPASS=true` bypasses Supabase for local dev only.
- **Client-side:** `SUPABASE_URL` + `SUPABASE_ANON_KEY`. **Server-side:** `SUPABASE_SERVICE_ROLE_KEY` (lockout tracking, admin ops, storage uploads, webhook processing).
- `core/database.py` provides `get_database_client(access_token=...)` (user-scoped, respects RLS) and `get_service_role_client()` (server-side).
- Migrations apply in order via the Supabase SQL editor or CLI, `supabase/migrations/001` through `008`. Legacy JSON migration: `scripts/migrate_json_to_supabase.py`.

---

## Docker layout

```
/opt/datadumpai-enterprise/
├── Dockerfile              ← Python 3.12-slim, shared by app/api/webhooks
├── web/Dockerfile          ← Node build → static nginx image, for frontend
├── docker-compose.yml      ← 5 services (below)
├── .env                    ← production secrets (not in git)
└── (application source)
```

```yaml
services:
  frontend:   # React SPA + nginx → :3001 (host) — what app.getdatadump.com actually serves
  app:        # Streamlit → :8501 — dead code, still built/run, not routed to
  api:        # uvicorn api.app:app → :8000 — the live product API
  webhooks:   # uvicorn api.webhook_server:app → :8001
  qdrant:     # qdrant/qdrant:v1.13.2 → :6333/:6334

volumes:
  app_data:    # Shared /app/data for local fallback storage (app, api, webhooks)
  qdrant_data: # Qdrant's own storage
```

`app`, `api`, and `webhooks` all build from the same root `Dockerfile` and differ only by command. `frontend` builds separately from `web/` and bakes `VITE_*` env vars into the static bundle at build time — changing them requires a rebuild, not just a restart.

---

## Deployment flow

Deploys run via GitHub Actions (`.github/workflows/deploy.yml`) on every push to `main`:

1. **Test gate** (`test.yml`) — pytest suite must pass (skippable only via manual `workflow_dispatch` with an explicit override).
2. **Validate** — `docker compose config` and workflow lint (`actionlint`) against the target ref.
3. **Deploy** — SSHes into the production server, `git fetch && git reset --hard` to the deploy ref, then runs `.github/scripts/deploy.sh` (which runs `docker compose build`/`up -d` for the changed services; a plain Python-file-only change can also be picked up by the `app`/`api`/`webhooks` containers' read-only bind mounts without a rebuild, but the deploy script rebuilds regardless for consistency).
4. **On failure** — automatic rollback (`AUTO_ROLLBACK=true`), diagnostic log collection (compose `ps`, container logs, health probes), uploaded as a workflow artifact.
5. **Summary** — commit, duration, and health-probe results posted to the GitHub Actions run summary.

Marketing site deploys separately via `.github/workflows/marketing.yml` (`npm ci && npm run build`, `pm2 restart`).

Manual rollback: `bash .github/scripts/rollback.sh` on the server.

---

## Nginx topology

Nginx runs on the host (not in Docker) and terminates TLS for all public domains. The host-level config is not tracked in this repo (only a reference/historical config lives at [deploy/nginx-getdatadump-v1.conf](./deploy/nginx-getdatadump-v1.conf), explicitly labeled Streamlit-only era — do not treat it as current). What's confirmed by tracing live requests:

- `getdatadump.com` / `www.getdatadump.com` → PM2 Next.js on `:3000`.
- `app.getdatadump.com` `/` → the `frontend` container (React SPA).
- `app.getdatadump.com` `/api/*` → same-origin, proxied by `frontend`'s own nginx (`web/nginx.conf`) to `api:8000`. Whether the host nginx also has a direct `/api/` location or this proxy hop happens entirely inside the `frontend` container is not re-verified here — treat `web/nginx.conf` as authoritative for the proxy behavior either way.
- `app.getdatadump.com` `/webhooks/*` → `webhooks:8001`.
- Nothing routes to `:8501` (Streamlit) — confirmed dead path.

---

## External integrations

| Service | Used by | Purpose |
|---------|---------|---------|
| **OpenAI** | `services/` (live path) | Report generation, chat/Copilot, `text-embedding-3-small` embeddings |
| **Qdrant** | `services/qdrant_service.py` | Vector search for retrieval-grounded reports and chat RAG |
| **Supabase** | Auth, DB, Storage | Platform backend |
| **Paystack** | Billing UI + `webhooks` | Subscriptions (NGN) — the only active payment provider |
| **Stripe** | Webhook handler only | Code path present, hard-disabled at the service layer (`services/billing_service.py`); not offered to users |
| **SMTP / Resend** | Email service | Verification, notifications, billing alerts |
| **Google Analytics** | Marketing site | Optional traffic analytics |
| **Sentry** | Marketing site | Optional error monitoring |

---

## Testing

- **Backend:** `pytest` (400+ tests covering auth, billing, retrieval, report generation, document extraction, storage, security/tenant isolation)
- **Marketing site:** `npm run lint`, `npm run build` (production build verification)
- **Frontend (`web/`):** typecheck + build as part of CI

Run tests locally before deploying (`docker compose exec api python3 -m pytest tests/ -q`, with a fresh copy of `tests/` into the container since it's not bind-mounted). Production health endpoints confirm runtime availability but not functional correctness — verify real user flows after any deploy that touches report generation, retrieval, or billing.

---

## Version history

| Version | Stack | Notes |
|---------|-------|-------|
| Legacy (`/opt/datadump-ai`) | FastAPI + React + Postgres + Qdrant | Pre-Enterprise; kept for rollback |
| v1.0 (`/opt/datadumpai-enterprise`) | Streamlit + Supabase + FastAPI webhooks | Superseded — Streamlit code and its Docker service have been deleted |
| **Current** | **FastAPI (`api/`) + React SPA (`web/`) + Supabase + Qdrant + FastAPI webhooks** | **Live production application** |
| Marketing split | Next.js on PM2, `app.` subdomain for the product | Unchanged, still current |

---

## Related files

| File | Description |
|------|--------------|
| [PRODUCTION.md](./PRODUCTION.md) | Server ops, env vars, deploy and rollback |
| [docker-compose.yml](./docker-compose.yml) | Container definitions |
| [Dockerfile](./Dockerfile) | Python services image (api/webhooks) |
| [web/Dockerfile](./web/Dockerfile) | Frontend SPA image |
| [web/nginx.conf](./web/nginx.conf) | Frontend container's internal nginx — same-origin `/api` proxy |
| [deploy/nginx-getdatadump-v1.conf](./deploy/nginx-getdatadump-v1.conf) | Reference nginx config (Streamlit-only era — historical, not current) |
| [deploy/remote-setup.sh](./deploy/remote-setup.sh) | Server bootstrap script |
| [.github/workflows/deploy.yml](./.github/workflows/deploy.yml) | Production deploy pipeline |
| [.env.example](./.env.example) | Environment variable template |
| [marketing-site/README.md](./marketing-site/README.md) | Marketing site docs |
