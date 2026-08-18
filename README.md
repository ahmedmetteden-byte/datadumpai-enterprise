# DataDumpAI Enterprise

An organizational knowledge and reporting platform. Users upload documents into a project, the app indexes them for semantic search, and an AI reporting assistant generates retrieval-grounded reports — findings backed by cited evidence rather than a blind document dump — exportable to PDF, Word, or PowerPoint.

For the full system design (services, data flow, tenant isolation, request lifecycle), see **[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)**. For server ops (deploy, rollback, env vars), see **[PRODUCTION.md](./PRODUCTION.md)**.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite, served behind its own nginx (`web/`) |
| Backend API | FastAPI (`api/`) |
| Auth / database / file storage | Supabase (Auth, Postgres, Storage) |
| Vector search | Qdrant — chunk embeddings for retrieval-grounded reports and the Intelligence Studio chat |
| AI | OpenAI (chat + `text-embedding-3-small` embeddings) |
| Marketing site | Next.js 15 (`marketing-site/`), deployed separately |

## Repository layout

```
api/            FastAPI app: routers, JWT auth, request schemas
web/            React SPA (the authenticated application)
services/       Business logic shared across the API — indexing, retrieval,
                report generation, billing, exports, etc.
core/           Request-scoped current-user resolution, Supabase clients
repositories/   Data access (Supabase or local-JSON fallback)
storage/        Blob storage abstraction (Supabase Storage or local disk)
models/         Shared data models
supabase/       SQL migrations
marketing-site/ Public Next.js site (separate deploy, PM2)
tests/          pytest suite for the backend
deploy/         Server bootstrap scripts, reference nginx config
scripts/        One-off ops/maintenance scripts
```

## Local development

Requires Docker and an OpenAI API key at minimum; a Supabase project is needed for real auth (see "Auth bypass" below for a credential-free local path).

1. Copy `.env.example` to `.env` at the repo root and fill in `OPENAI_API_KEY`. Copy `web/.env.example` to `web/.env` for the frontend's own `VITE_*` variables — the two files are **not** shared; Vite only reads from `web/`.
2. Start the stack:

   ```bash
   docker compose up -d --build
   ```

   This brings up:

   | Service | Port | Purpose |
   |---|---|---|
   | `frontend` | `3001` → `80` | React SPA + nginx (proxies `/api/` to `api` same-origin) |
   | `api` | `8000` | Product API |
   | `webhooks` | `8001` | Paystack (and dormant Stripe) billing webhooks |
   | `qdrant` | `6333` / `6334` | Vector search |

3. Open `http://localhost:3001`.

### Auth bypass for local dev without Supabase

Set `ENVIRONMENT=development` and `AUTH_DEV_BYPASS=true` in `.env` to skip real Supabase sign-in for a single local dev user. The app refuses to start with this bypass enabled outside `ENVIRONMENT=development` — it can't accidentally ship to production.

### Running tests

`tests/` is not bind-mounted into the container, so copy it in before running:

```bash
docker compose cp tests api:/app/tests
docker compose exec api python3 -m pytest tests/ -q
```

## Deployment

Automatic on every push to `main` via `.github/workflows/deploy.yml` — a pre-deploy test gate, artifact validation, then an SSH deploy with automatic rollback on failed health checks. See [PRODUCTION.md](./PRODUCTION.md) for server details, manual rollback, and environment variable reference.

## License

Proprietary. All rights reserved — see [LICENSE.txt](./LICENSE.txt).
