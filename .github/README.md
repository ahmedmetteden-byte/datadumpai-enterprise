# DataDumpAI Enterprise — CI/CD

Production deployment automation for the DataDumpAI Enterprise platform. This directory adds **deployment infrastructure only** — it does not change application code, Docker service names, domains, or runtime architecture.

For live server layout and operational context, see [PRODUCTION.md](../PRODUCTION.md).

---

## Repository layout

```
.github/
├── workflows/
│   ├── deploy.yml       # Application stack (Docker Compose) → app.getdatadump.com
│   ├── test.yml         # Python tests + compose/workflow validation (reusable)
│   ├── release.yml      # Git tag releases (v*.*.*)
│   └── marketing.yml    # Marketing site (Next.js + PM2) → getdatadump.com
├── scripts/
│   ├── deploy.sh            # Main application deployment orchestration
│   ├── deploy-marketing.sh  # Marketing site deployment (PM2)
│   ├── rollback.sh          # Roll back to a previous commit
│   ├── verify.sh            # Pre-deploy validation
│   ├── cleanup.sh           # Safe Docker image cleanup
│   └── health-check.sh      # Streamlit + webhook health probes
└── README.md
```

`deploy-marketing.sh` is included alongside the requested scripts because the marketing stack (PM2, not Docker) needs the same operational guarantees as the application deploy path.

---

## Workflows

### `test.yml` — Test gate

| Trigger | Purpose |
|---------|---------|
| Pull requests to `main` | Validate changes before merge |
| `workflow_call` | Called by `deploy.yml` and `release.yml` |

Jobs:

1. **Python test suite** — `pytest` on Python 3.12 with isolated JSON/local storage fixtures
2. **Validate Docker Compose** — `docker compose config` on `docker-compose.yml`
3. **Validate workflow syntax** — [actionlint](https://github.com/rhysd/actionlint)

Tests must pass before any production deploy or release proceeds.

### `deploy.yml` — Application deployment

| Trigger | Purpose |
|---------|---------|
| Push to `main` | Deploy Streamlit + webhook stack |
| `workflow_dispatch` | Manual deploy (optional test skip for emergencies) |

Pipeline:

1. Run `test.yml` (skipped only when manually dispatched with **Skip the test gate**)
2. Validate compose + workflow syntax on the runner
3. SSH to production, sync latest `main`, run `.github/scripts/deploy.sh`
4. Publish a deployment summary (commit, duration, health endpoints, status)

**Concurrency:** one production deployment at a time (`cancel-in-progress: false`). If a deploy is already running, additional pushes to `main` queue rather than overlap — protecting container restarts and health checks.

**Deployment summary:** every run writes a markdown report to `$GITHUB_STEP_SUMMARY` (visible on the workflow run page) including commit, duration, and overall status.

**Failure artifacts:** if deploy fails, server logs are collected (deploy output + `docker compose` diagnostics), downloaded via SCP, and uploaded as a workflow artifact named `deployment-logs-<run_id>` (retained 30 days).

### `marketing.yml` — Marketing site deployment

| Trigger | Purpose |
|---------|---------|
| Push to `main` affecting `marketing-site/**` | Deploy Next.js site |
| `workflow_dispatch` | Manual marketing deploy |

Pipeline:

1. `npm ci`, `npm run build`, `npm run lint` on the runner
2. SSH to production, sync `main`, run `.github/scripts/deploy-marketing.sh`

Does not restart Docker containers. PM2 process name: `datadump-marketing`.

**Concurrency:** `marketing-deployment` group with `cancel-in-progress: false` — same queueing behaviour as application deploys.

**Failure artifacts:** on failure, PM2 diagnostics are appended to the server log file and uploaded as `marketing-deployment-logs-<run_id>`.

### `release.yml` — Versioned releases

| Trigger | Purpose |
|---------|---------|
| Push tag `v*.*.*` (e.g. `v1.0.0`) | Create GitHub Release |

Pipeline:

1. Run full test gate
2. Generate release notes from commits since the previous tag
3. Create a GitHub Release (auto-notes + changelog section)

Tags document releases; production deploys still flow through pushes to `main`.

---

## Deployment scripts

### `deploy.sh`

Idempotent production deploy for `/opt/datadumpai-enterprise`:

1. `verify.sh` — directory, `.env`, Docker/Compose version checks, `docker compose config`, git remote
2. Record pre-deploy commit in `.deploy/pre-deploy-commit`
3. `git fetch` + `git reset --hard origin/main` (no merge commits)
4. `docker compose build` + `docker compose up -d`
5. `health-check.sh` — wait for healthy containers and HTTP probes
6. On failure after restart → automatic `rollback.sh` (when `AUTO_ROLLBACK=true`)
7. `cleanup.sh` — prune dangling images only
8. Print deployment summary (commit, duration, container status)

Environment variables (for future staging/dev):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DIR` | `/opt/datadumpai-enterprise` | Application root on server |
| `GIT_BRANCH` | `main` | Branch to deploy |
| `GIT_REMOTE` | `origin` | Git remote name |
| `AUTO_ROLLBACK` | `true` | Roll back on failed health checks |

### `health-check.sh`

Waits for Docker health states (when available), then probes:

- Streamlit: `http://127.0.0.1:8501/_stcore/health`
- Webhook: `http://127.0.0.1:8001/health`

Exits non-zero if either endpoint is unhealthy after the timeout (default 180s). **Deployment fails.**

### `verify.sh`

Pre-flight checks before any destructive step. Validates:

- Docker daemon is running and accessible to the deploy user
- Docker Compose v2 is installed and meets minimum version (default `2.0.0`)
- Docker Engine meets minimum version (default `20.10.0`)
- Compose file renders successfully with production `.env`
- Git remote connectivity

Override minimums with `COMPOSE_MIN_VERSION` or `DOCKER_MIN_VERSION` if needed.

### `rollback.sh`

Rolls back to:

1. Commit argument, or
2. `.deploy/pre-deploy-commit`, or
3. `.deploy/last-successful-commit`

Then rebuilds images, restarts containers, and re-runs health checks.

### `cleanup.sh`

Runs `docker image prune` for **dangling images only**. Images used by running containers are never removed.

### `deploy-marketing.sh`

Syncs repo, runs `npm ci` + `npm run build` in `marketing-site/`, restarts PM2, verifies HTTP on port `3000`.

---

## Rollback strategy

### Automatic rollback (application deploy)

After `docker compose up -d`, if health checks fail, `deploy.sh` invokes `rollback.sh` using the recorded pre-deploy commit.

**Why this is appropriate:** deploys only replace application containers from git. No database migrations run during deploy. The previous commit was serving traffic moments earlier.

**Why full automatic rollback is not always safe (documented limits):**

- Schema migrations or manual server changes outside git would not be reversed
- Marketing PM2 deploys do not auto-rollback (static assets + PM2 restart — manual `git checkout` + rebuild is safer to verify)
- Nginx / SSL / DNS changes are out of scope for these scripts

### Manual rollback (application)

```bash
ssh root@<SERVER_HOST>
cd /opt/datadumpai-enterprise

# Roll back to last known-good commit recorded by deploy.sh
bash .github/scripts/rollback.sh

# Or roll back to a specific commit
bash .github/scripts/rollback.sh abc1234
```

### Manual rollback (marketing)

```bash
cd /opt/datadumpai-enterprise
git fetch origin main --prune
git checkout <previous-commit> -- marketing-site
cd marketing-site
npm ci && npm run build
pm2 restart datadump-marketing
```

See [PRODUCTION.md](../PRODUCTION.md) for nginx-level and legacy-stack rollback (Levels 1–3).

---

## Required GitHub Secrets

Configure in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `SERVER_HOST` | Production server hostname or IP |
| `SERVER_USER` | SSH user (currently `root`; prefer a dedicated deploy user later) |
| `SERVER_SSH_KEY` | Private SSH key (PEM/OpenSSH format) |

Never commit secrets. Never log secret values in workflows or scripts.

### Pinned GitHub Actions

Third-party actions are pinned to immutable commit SHAs (comment shows the release tag). Update deliberately after reviewing release notes.

| Action | Pin | Tag |
|--------|-----|-----|
| `actions/checkout` | `11bd71901bbe5b1630ceea73d27597364c9af683` | v4.2.2 |
| `actions/setup-python` | `0b93645e9fea7318ecaed2b359559ac225c90a2b` | v5.3.0 |
| `actions/setup-node` | `39370e3970a6d050c480ffad4ff0ed4d3fdee5af` | v4.1.0 |
| `actions/upload-artifact` | `65c4c4a1ddee5b72f698fdd19549f0f0fb45cf08` | v4.6.0 |
| `appleboy/ssh-action` | `7eaf76671a0d7eec5d98ee897acda4f968735a17` | v1.2.0 |
| `appleboy/scp-action` | `917f8b81dfc1ccd331fef9e2d61bdc6c8be94634` | v0.1.7 |
| `softprops/action-gh-release` | `c95fe1489396fe8a9eb87c0abf8aa5b2ef267fda` | v2.2.1 |

Workflow linting uses pinned [actionlint](https://github.com/rhysd/actionlint) release `v1.7.7`.

### Migrating from `root` to a dedicated deploy user

Production currently deploys as `root` (`SERVER_USER=root`). This is supported and unchanged. Plan a future migration to a least-privilege deploy account without downtime:

#### 1. Create the deploy user on the server

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
```

#### 2. Grant filesystem access

```bash
sudo chown -R deploy:deploy /opt/datadumpai-enterprise
# Preserve secret permissions
sudo chmod 600 /opt/datadumpai-enterprise/.env
sudo chmod 600 /opt/datadumpai-enterprise/marketing-site/.env.local
```

#### 3. PM2 for the deploy user

Marketing deploys require PM2 under the same user that owns the process:

```bash
sudo -u deploy bash -lc 'cd /opt/datadumpai-enterprise/marketing-site && npm ci && npm run build'
sudo -u deploy pm2 start npm --name datadump-marketing -- start
sudo -u deploy pm2 save
# Enable PM2 startup for the deploy user (follow pm2 startup instructions)
```

#### 4. SSH access

```bash
sudo mkdir -p /home/deploy/.ssh
sudo cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Generate a **new** deploy-only key pair for GitHub Actions rather than reusing the root key.

#### 5. Verify before switching CI

```bash
sudo -u deploy bash -lc 'cd /opt/datadumpai-enterprise && bash .github/scripts/verify.sh'
sudo -u deploy bash -lc 'cd /opt/datadumpai-enterprise && bash .github/scripts/health-check.sh'
```

#### 6. Update GitHub Secrets

| Secret | Change |
|--------|--------|
| `SERVER_USER` | `deploy` |
| `SERVER_SSH_KEY` | New private key for the deploy user |

#### 7. Rollback to root (if needed)

Revert `SERVER_USER` to `root` and the original SSH key in GitHub Secrets. No application or workflow code changes are required — scripts read `SERVER_USER` from secrets only.

**What the deploy user does not need:** root sudo, nginx reload access, or certbot — those remain manual host operations outside the CI/CD deploy path.

---

## Server prerequisites

On the production Ubuntu 24.04 server:

| Requirement | Notes |
|-------------|-------|
| Git repository | `/opt/datadumpai-enterprise` cloned from GitHub |
| Docker + Compose v2 | `docker compose version` |
| `.env` | Production secrets (`chmod 600`) |
| `marketing-site/.env.local` | Public URLs for Next.js |
| PM2 + Node 22 | Marketing site (`pm2 list`) |
| Nginx | Already routing domains (unchanged by CI/CD) |
| SSH key | Public key in `~/.ssh/authorized_keys` for deploy user |
| Outbound git | Server can `git fetch` from GitHub |

One-time bootstrap (if CI/CD files are not on the server yet):

```bash
ssh root@<SERVER_HOST>
cd /opt/datadumpai-enterprise
git fetch origin main --prune
git reset --hard origin/main
chmod +x .github/scripts/*.sh
```

---

## Setup instructions

### 1. Create a feature branch

```bash
git checkout -b feature/cicd
```

### 2. Commit CI/CD files

Add `.github/workflows/`, `.github/scripts/`, and this README. Push the branch.

### 3. Configure GitHub Secrets

Add `SERVER_HOST`, `SERVER_USER`, and `SERVER_SSH_KEY`.

### 4. Optional: GitHub Environment

Create a `production` environment in GitHub for approval gates or environment-scoped secrets.

### 5. Test from the feature branch first

Use **Actions → Deploy DataDumpAI Enterprise → Run workflow** and select your branch, or temporarily add the branch to `deploy.yml` triggers.

Verify:

- Tests pass
- SSH connects
- Health checks succeed
- Deployment summary looks correct

### 6. Merge to `main` only after validation

```bash
git checkout main
git merge feature/cicd
git push origin main
```

---

## How to test the pipeline

### Pull request

Open a PR to `main`. The **Test** workflow runs automatically.

### Application deploy

1. Push to `main` (after merge), or
2. **Actions → Deploy DataDumpAI Enterprise → Run workflow**

Confirm in the workflow summary:

- Commit hash matches the push
- Container status is healthy
- Streamlit and webhook health checks passed

### Marketing deploy

Change a file under `marketing-site/` and push to `main`, or run **Deploy Marketing Site** manually.

### Release

```bash
git tag v1.0.1
git push origin v1.0.1
```

Check **Releases** on GitHub for auto-generated notes.

---

## Manual deployment (GitHub Actions unavailable)

### Application (Docker)

```bash
ssh root@<SERVER_HOST>
cd /opt/datadumpai-enterprise
git fetch origin main --prune
git reset --hard origin/main
chmod +x .github/scripts/*.sh
bash .github/scripts/deploy.sh
```

### Marketing (PM2)

```bash
ssh root@<SERVER_HOST>
cd /opt/datadumpai-enterprise
git fetch origin main --prune
git reset --hard origin/main
chmod +x .github/scripts/*.sh
bash .github/scripts/deploy-marketing.sh
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| SSH connection failed | Wrong host, key, or firewall | Verify secrets; test `ssh -i key user@host` locally |
| `missing .env` | Secrets file absent on server | Create from `.env.example` / `scripts/generate_production_env.sh` |
| Health check timeout | Slow Streamlit cold start | Wait and check `docker compose logs app`; increase `HEALTH_TIMEOUT_SECONDS` |
| Webhook unhealthy | Port 8001 not listening | `docker compose logs webhooks` |
| Deploy script not found | Server not synced | Run bootstrap `git reset --hard origin/main` |
| Tests fail in CI | Code regression | Fix tests locally with `pytest` |
| `docker compose config` fails | Invalid compose or env | Run on server with production `.env` |
| `docker compose version` too old | Missing Compose v2 plugin | Install Docker Compose v2; see `verify.sh` minimums |
| Deploy failed — need logs | Health check or build failure | Download workflow artifact `deployment-logs-<run_id>` from the Actions run |

### Useful server commands

```bash
cd /opt/datadumpai-enterprise
docker compose ps
docker compose logs -f app
docker compose logs -f webhooks
curl -fs http://127.0.0.1:8501/_stcore/health
curl -fs http://127.0.0.1:8001/health
pm2 logs datadump-marketing --lines 100
```

---

## Health checks

| Service | Endpoint | Used by |
|---------|----------|---------|
| Streamlit | `http://127.0.0.1:8501/_stcore/health` | `health-check.sh`, `deploy.sh` |
| Webhook API | `http://127.0.0.1:8001/health` | `health-check.sh`, `deploy.sh` |
| Marketing | `http://127.0.0.1:3000/` | `deploy-marketing.sh` |

Public URLs (via Nginx) are not probed during deploy to avoid CDN/SSL false negatives.

---

## Recovery procedures

1. **Failed deploy with auto-rollback** — Confirm health endpoints; inspect `docker compose logs`
2. **Failed deploy without rollback** — `bash .github/scripts/rollback.sh`
3. **Broken marketing site** — Manual git checkout + `npm run build` + `pm2 restart`
4. **Nginx / routing issues** — See [PRODUCTION.md](../PRODUCTION.md) Level 1 rollback
5. **Full legacy restore** — See [PRODUCTION.md](../PRODUCTION.md) Level 3

Deploy state files (on server):

```
/opt/datadumpai-enterprise/.deploy/
├── pre-deploy-commit      # Commit before latest deploy attempt
├── last-successful-commit # Last commit that passed health checks
└── logs/
    ├── deploy-<run_id>.log           # Application deploy output
    └── marketing-deploy-<run_id>.log # Marketing deploy output
```

---

## Adding another server

1. Clone repo to the same path: `/opt/datadumpai-enterprise`
2. Copy `.env` and `marketing-site/.env.local` securely
3. Start stack once manually (`docker compose up -d`, PM2)
4. Add server-specific secrets (e.g. `SERVER_HOST_STAGING`) — future workflow inputs can select environment
5. Point DNS when ready

---

## Future staging / dev support

The pipeline is designed for multiple environments without redesign:

| Environment | Suggested domain | `APP_DIR` | Trigger |
|-------------|------------------|-----------|---------|
| Development | `dev.getdatadump.com` | `/opt/datadumpai-enterprise-dev` | Push to `develop` |
| Staging | `staging.getdatadump.com` | `/opt/datadumpai-enterprise-staging` | Push to `staging` |
| Production | `app.getdatadump.com` | `/opt/datadumpai-enterprise` | Push to `main` |

Extend workflows with:

- GitHub **Environments** (`staging`, `production`)
- Environment-specific secrets (`SERVER_HOST`, `APP_DIR`)
- Branch filters per environment

Scripts already accept `APP_DIR`, `GIT_BRANCH`, and health URL overrides.

---

## Future improvements

- [x] Deployment log artifacts on workflow failure
- [x] Pinned GitHub Action versions (commit SHAs)
- [ ] Dedicated non-root deploy user with least-privilege sudo (see migration guide above)
- [ ] GitHub Environment protection rules (required reviewers for production)
- [ ] Staging environment workflow on `staging` branch
- [ ] Slack/email notifications on deploy failure
- [ ] Post-deploy smoke tests (authenticated API paths)
- [ ] Metrics export (deploy duration, failure rate)
- [ ] Scheduled `cleanup.sh` during maintenance windows
- [ ] Sentry release tracking tied to `release.yml` tags
- [ ] OIDC-based SSH (no long-lived private keys)

---

## Security notes

- Secrets live only in GitHub Actions secrets and server `.env` files
- Workflows never echo `SERVER_SSH_KEY` or application secrets
- Emergency deploy can skip tests via `workflow_dispatch` — restrict who can dispatch workflows
- Rotate SSH keys periodically; prefer deploy keys or short-lived credentials long term
