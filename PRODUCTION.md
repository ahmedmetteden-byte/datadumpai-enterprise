# DataDumpAI Enterprise — Production

This document describes how DataDumpAI Enterprise is deployed in production. It is the single source of truth for server layout, routing, secrets, and operational procedures.

**Last verified:** July 2026

---

## GitHub repository

| Item | Value |
|------|-------|
| **Repository** | [github.com/ahmedmetteden-byte/datadumpai-enterprise](https://github.com/ahmedmetteden-byte/datadumpai-enterprise) |
| **Default branch** | `main` |
| **Server deploy path** | `/opt/datadumpai-enterprise` |

The server clones from GitHub. Local development may not have a remote configured; production always tracks the GitHub repo.

---

## Server location

| Item | Value |
|------|-------|
| **Provider** | DigitalOcean |
| **Region** | London (`lon1`) |
| **Droplet** | `ubuntu-s-2vcpu-4gb-lon1` (2 vCPU, 4 GB RAM) |
| **Public IP** | `104.248.169.183` |
| **OS** | Ubuntu (Linux) |
| **SSH access** | `root@104.248.169.183` |

### Directory layout on the server

```
/opt/
├── datadumpai-enterprise/       ← LIVE — current v1.0 deployment
├── datadumpai-enterprise-v1/    ← earlier deploy path (superseded)
├── datadump-ai/                 ← LEGACY — old React + FastAPI stack (kept for rollback)
├── datadumpai-v2/               ← stale Streamlit beta (not serving traffic)
└── backups/
    └── datadump-ai-20260709-223602/   ← full legacy backup (code, DB dump, volumes, nginx)
```

---

## Domain names

| Domain | Purpose | Upstream |
|--------|---------|----------|
| `https://getdatadump.com` | Public marketing site | PM2 → `:3000` |
| `https://www.getdatadump.com` | Public marketing site (alias) | PM2 → `:3000` |
| `https://app.getdatadump.com` | Authenticated Streamlit application | Docker → `:8501` |
| `https://app.getdatadump.com/webhooks/*` | Billing webhooks (Stripe, Paystack) | Docker → `:8001` |

HTTP (port 80) on all domains redirects to HTTPS.

---

## Production topology

```
Internet
    │
    ▼
Nginx (:443 / :80)  —  host-level, not containerized
    │
    ├── getdatadump.com / www.getdatadump.com
    │       └── proxy_pass → 127.0.0.1:3000   (PM2: datadump-marketing)
    │
    └── app.getdatadump.com
            ├── /           → 127.0.0.1:8501   (Docker: Streamlit app)
            └── /webhooks/  → 127.0.0.1:8001   (Docker: FastAPI webhooks)

Legacy rollback stack (not serving public traffic):
    datadump-ai-frontend-1  :8080
    datadump-ai-api-1       :8000
    datadump-ai-db-1        :5432
    datadump-ai-qdrant-1    :6333
```

---

## Docker services

Compose file: `docker-compose.yml` (run from `/opt/datadumpai-enterprise`).

| Container | Service | Port | Command | Health check |
|-----------|---------|------|---------|--------------|
| `datadumpai-enterprise-app-1` | Streamlit application | `8501` | `streamlit run app.py` | `GET /_stcore/health` |
| `datadumpai-enterprise-webhooks-1` | Billing webhooks | `8001` | `uvicorn api.webhook_server:app` | `GET /health` |

Both containers:

- Read secrets from `/opt/datadumpai-enterprise/.env`
- Share the `app_data` Docker volume mounted at `/app/data`
- Restart policy: `unless-stopped`

### Common Docker commands

```bash
cd /opt/datadumpai-enterprise

# Status
docker compose ps

# Rebuild and restart after code or env changes
docker compose build
docker compose up -d

# Logs
docker compose logs -f app
docker compose logs -f webhooks

# Health checks (from the server)
curl -s http://127.0.0.1:8501/_stcore/health
curl -s http://127.0.0.1:8001/health
```

---

## PM2 services

The Next.js marketing site runs outside Docker under PM2.

| Item | Value |
|------|-------|
| **Process name** | `datadump-marketing` |
| **Working directory** | `/opt/datadumpai-enterprise/marketing-site` |
| **Command** | `npm start` (production build via `next start`) |
| **Port** | `3000` |
| **Node.js** | v22.x |

### Common PM2 commands

```bash
cd /opt/datadumpai-enterprise/marketing-site

# Build after code or env changes
npm ci
npm run build

# Restart the marketing site
pm2 restart datadump-marketing

# Status and logs
pm2 list
pm2 logs datadump-marketing --lines 100
```

Environment for the marketing site lives in `marketing-site/.env.local` (not committed). See `marketing-site/.env.example` for the variable list.

---

## Nginx routing

Active config: `/etc/nginx/sites-available/getdatadump` (symlinked from `sites-enabled`).

Reference copy in the repo: `deploy/nginx-getdatadump-v1.conf` (Streamlit-only layout — production nginx has been updated for the marketing site split).

### Current routing rules

| Server name | Location | Upstream | Notes |
|-------------|----------|----------|-------|
| `getdatadump.com`, `www.getdatadump.com` | `/` | `http://127.0.0.1:3000` | WebSocket headers for Next.js |
| `app.getdatadump.com` | `/` | `http://127.0.0.1:8501` | Streamlit; `proxy_read_timeout 86400` |
| `app.getdatadump.com` | `/webhooks/` | `http://127.0.0.1:8001` | Stripe and Paystack endpoints |

`client_max_body_size` is `50m` on the app vhost (document uploads).

After any nginx change:

```bash
nginx -t && systemctl reload nginx
```

---

## SSL configuration

| Item | Value |
|------|-------|
| **Provider** | Let's Encrypt (Certbot) |
| **Certificate name** | `getdatadump.com` |
| **Domains covered** | `getdatadump.com`, `www.getdatadump.com`, `app.getdatadump.com` |
| **Certificate path** | `/etc/letsencrypt/live/getdatadump.com/fullchain.pem` |
| **Private key path** | `/etc/letsencrypt/live/getdatadump.com/privkey.pem` |
| **Options include** | `/etc/letsencrypt/options-ssl-nginx.conf` |
| **DH params** | `/etc/letsencrypt/ssl-dhparams.pem` |
| **Auto-renewal** | Certbot systemd timer |

Check certificate status:

```bash
certbot certificates
```

Nginx cutovers do not require reissuing certificates — only upstream targets change.

---

## Environment variables

### Streamlit + webhooks (`.env` on server)

Generated from `.env.example`. Production values are **never committed**. Use `scripts/generate_production_env.sh` to bootstrap from the legacy stack, then add Supabase keys manually.

| Category | Variables |
|----------|-----------|
| **AI** | `OPENAI_API_KEY` |
| **Supabase Auth** | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_REDIRECT_URL`, `AUTH_DEV_BYPASS` |
| **Storage backends** | `DATABASE_BACKEND`, `STORAGE_BACKEND`, `SUPABASE_STORAGE_BUCKET` |
| **Lockout** | `LOCKOUT_MAX_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES` |
| **Billing** | `PAYMENTS_ENABLED`, `STRIPE_*`, `PAYSTACK_*`, `BILLING_SUCCESS_URL`, `BILLING_CANCEL_URL`, `BILLING_WEBHOOK_BASE_URL` |
| **Email** | `EMAIL_ENABLED`, `EMAIL_FROM`, `EMAIL_FROM_NAME`, `SMTP_*`, `RESEND_API_KEY` |
| **Admin** | `ADMIN_USER_IDS`, `ADMIN_EMAILS` |
| **Analytics** | `ANALYTICS_ENABLED`, `ANALYTICS_PROVIDER`, `POSTHOG_*`, `PLAUSIBLE_DOMAIN` |
| **General** | `SITE_URL`, `DEBUG` |

Production requirements:

- `AUTH_DEV_BYPASS=false`
- `AUTH_REDIRECT_URL=https://app.getdatadump.com`
- `DATABASE_BACKEND=supabase` and `STORAGE_BACKEND=supabase`
- `SUPABASE_SERVICE_ROLE_KEY` stays server-side only — never expose to the browser

Webhook URLs registered with payment providers:

- Stripe: `https://app.getdatadump.com/webhooks/stripe`
- Paystack: `https://app.getdatadump.com/webhooks/paystack`

### Marketing site (`marketing-site/.env.local`)

| Variable | Production value |
|----------|------------------|
| `NEXT_PUBLIC_SITE_URL` | `https://www.getdatadump.com` |
| `NEXT_PUBLIC_APP_URL` | `https://app.getdatadump.com` |
| `NEXT_PUBLIC_CONTACT_EMAIL` | `hello@getdatadump.com` |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID` | *(optional — GA4)* |
| `NEXT_PUBLIC_SENTRY_DSN` | *(optional — error monitoring)* |

---

## Deployment process

### Standard deploy (application update)

```bash
ssh root@104.248.169.183

cd /opt/datadumpai-enterprise
git pull origin main

# Backend (Streamlit + webhooks)
docker compose build
docker compose up -d

# Marketing site
cd marketing-site
npm ci
npm run build
pm2 restart datadump-marketing

# Verify
curl -s http://127.0.0.1:8501/_stcore/health
curl -s http://127.0.0.1:8001/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
```

### First-time or greenfield deploy

1. Clone the repo to `/opt/datadumpai-enterprise`
2. Create `.env` from `.env.example` or run `scripts/generate_production_env.sh`
3. Add Supabase credentials; set `AUTH_DEV_BYPASS=false`
4. Run Supabase migrations (`supabase/migrations/001` through `008`)
5. Configure Supabase Auth redirect URL: `https://app.getdatadump.com`
6. `docker compose up -d --build`
7. Build and start marketing site under PM2 (see PM2 section)
8. Install nginx config, run `nginx -t && systemctl reload nginx`
9. Update Stripe/Paystack webhook endpoints

Alternative bootstrap script: `deploy/remote-setup.sh` (generates `.env` from legacy `/opt/datadump-ai/backend/.env`, builds and starts Docker).

### Pre-deploy checklist

- [ ] Supabase migrations applied
- [ ] `.env` complete and `chmod 600`
- [ ] `marketing-site/.env.local` set with correct public URLs
- [ ] Stripe webhook URL points to `app.getdatadump.com/webhooks/stripe`
- [ ] Health endpoints return OK before switching nginx

---

## Rollback procedure

Two rollback levels exist depending on how far a deploy progressed.

### Level 1 — Revert nginx only (< 1 minute)

Use when Docker/PM2 services are healthy but routing is wrong, or you need to restore the **legacy React + FastAPI stack**.

```bash
ssh root@104.248.169.183

# Pre-cutover nginx backup from July 2026 deploy
cp /opt/backups/datadump-ai-20260709-223602/nginx-getdatadump.conf \
   /etc/nginx/sites-available/getdatadump

nginx -t && systemctl reload nginx
```

The legacy containers (`datadump-ai-*` on ports 8080/8000) remain running and immediately receive traffic again. No rebuild required.

### Level 2 — Roll back application containers

Use when the new Streamlit or webhook containers are broken but nginx routing is correct.

```bash
cd /opt/datadumpai-enterprise
git checkout <previous-commit>
docker compose build
docker compose up -d
```

For the marketing site:

```bash
cd /opt/datadumpai-enterprise/marketing-site
git checkout <previous-commit>
npm ci && npm run build
pm2 restart datadump-marketing
```

### Level 3 — Full data restore (legacy stack)

Only if Postgres/Qdrant data from the old platform must be recovered:

1. Stop new containers: `docker compose -f /opt/datadumpai-enterprise/docker-compose.yml down`
2. Restore from `/opt/backups/datadump-ai-20260709-223602/`:
   - `postgres-dump.sql`
   - `docker-volumes.tar.gz`
   - `datadump-ai-code.tar.gz`
3. Restart legacy stack: `docker compose -f /opt/datadump-ai/docker-compose.yml up -d`
4. Apply Level 1 nginx rollback

### Post-rollback verification

```bash
# Legacy stack health
curl -sk https://getdatadump.com/api/v1/system/health

# Or current stack health
curl -sk https://app.getdatadump.com/_stcore/health
curl -sk https://www.getdatadump.com/ -o /dev/null -w "%{http_code}\n"
```

---

## Related documentation

- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) — application design, data flow, and component details
- [marketing-site/README.md](./marketing-site/README.md) — marketing site development and env vars
- [.env.example](./.env.example) — full environment variable reference

---

## Operational notes

- **Legacy stack:** The old `datadump-ai-*` containers are intentionally kept running for instant rollback. Remove only after several days of stable production and explicit approval.
- **Secrets:** Never commit `.env`, `.env.local`, or Supabase service role keys. Rotate keys if exposed.
- **Disk:** Docker build cache can grow large; prune during maintenance windows with `docker system prune` (not during active deploys).
- **Monitoring:** PM2 logs at `/root/.pm2/logs/`. Docker logs via `docker compose logs`.
