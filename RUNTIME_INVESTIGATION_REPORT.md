# Runtime Investigation Report — Tenant Isolation Failure

**Date:** 12 July 2026  
**Scope:** Why two different users share the same workspace; why duplicate email registration appears to succeed  
**Method:** Code trace, on-disk evidence, runtime investigation instrumentation (no security fixes applied)

---

## Executive conclusion

**Root cause is proven:** Manual testing runs with `AUTH_DEV_BYPASS=true` in `.env`. Under dev bypass, **every login and registration resolves to the same user ID** (`DEV_USER_ID`) and **the same on-disk workspace**. Automated tests pass because they **inject different user IDs via `bind_current_user()`** without exercising the real auth path.

| Symptom | Exact failing component | Evidence |
|---------|-------------------------|----------|
| Two users share workspace | `AUTH_DEV_BYPASS` + `AuthService.dev_sign_in()` / `dev_sign_up()` | Same `user.id` for all sign-ins; same `data/users/00000000-0000-4000-8000-000000000001/` path |
| Duplicate email “succeeds” (Sign In path) | `AuthService.sign_in()` under dev bypass | Sign-in ignores email/password; no `email_exists()` check |
| Duplicate email on Sign Up | `EmailUniquenessService` **does** block same email on `sign_up()` | Registry on disk shows emails mapped to `DEV_USER_ID`; second `sign_up` with same email should raise `AuthError` |
| Tests falsely green | `tests/conftest.py` `auth_context` fixture | Monkeypatches `get_current_user` and `bind_current_user(TEST_USER)` — never calls `dev_sign_in()` |

**Stop condition met (Part 7 & 8):** User A and User B sign-in IDs are identical, and storage paths are identical.

---

## Part 6 — Backend configuration (verified)

### On-disk configuration

**File:** `.env`

```
AUTH_DEV_BYPASS=true
AUTH_REDIRECT_URL=http://localhost:8501
```

No `SUPABASE_URL` / `SUPABASE_ANON_KEY` are set. No `DEBUG=true`.

### Effective runtime values

| Setting | Configured | Effective at runtime |
|---------|------------|----------------------|
| `AUTH_DEV_BYPASS` | `true` | **Active** |
| `DATABASE_BACKEND` | default `supabase` | **JSON** (`use_database()` = false — Supabase not configured) |
| `STORAGE_BACKEND` | default `supabase` | **JSON/local** (`use_supabase_storage()` = false) |
| Authentication provider | — | **`AUTH_DEV_BYPASS`** (not Supabase) |
| `DEV_USER_ID` | — | `00000000-0000-4000-8000-000000000001` |

### Startup guard gap

`validate_production_auth_configuration()` in `config.py` only blocks startup when **`AUTH_DEV_BYPASS=true` AND Supabase is configured**. With no Supabase keys, the app **starts normally** with dev bypass enabled. Manual multi-user testing is therefore running in **single-user dev mode** without any warning unless `RUNTIME_INVESTIGATION=true` or `DEBUG=true`.

---

## Part 7 — User identity (proven identical)

### Code path

```98:112:c:\Users\ahmed\Downloads\DataDumpAI-Enterprise\services\auth_service.py
    def dev_sign_in(self) -> AuthSession:
        ...
        user = User(
            id=DEV_USER_ID,
            email=DEV_USER_EMAIL,
            full_name="Local Developer",
            email_verified=True,
        )
```

```216:230:c:\Users\ahmed\Downloads\DataDumpAI-Enterprise\services\auth_service.py
    def sign_in(self, email: str, password: str) -> AuthSession:
        normalized_email = normalize_email(email)
        if AUTH_DEV_BYPASS:
            session = self.dev_sign_in()
            ...
            return session
```

### Expected runtime result

| Action | Email entered | Resolved `user.id` | Resolved `user.email` |
|--------|---------------|--------------------|-----------------------|
| Sign in User A | `user-a@example.com` | `00000000-0000-4000-8000-000000000001` | `dev@localhost` |
| Sign in User B | `user-b@example.com` | `00000000-0000-4000-8000-000000000001` | `dev@localhost` |

**IDs identical: YES — investigation stops here for identity.**

`restore_session()` and `refresh_session()` also call `dev_sign_in()` under bypass, so persisted sessions cannot restore per-email identity.

### Sign-up assigns the same ID

```131:136:c:\Users\ahmed\Downloads\DataDumpAI-Enterprise\services\auth_service.py
        user = User(
            id=DEV_USER_ID,
            email=normalized_email,
            ...
        )
```

Sign-up stores the typed email in session **once**, but the next sign-in or session restore **reverts to `dev@localhost`**.

---

## Part 8 — Storage paths (proven identical)

### Resolution

`core/user_paths.py` → `get_user_projects_root(user_id)` → `data/users/{user_id}/projects/`

With both users resolving to `DEV_USER_ID`:

```
User A workspace: data/users/00000000-0000-4000-8000-000000000001/projects/
User B workspace: data/users/00000000-0000-4000-8000-000000000001/projects/
Quick Report:     data/users/00000000-0000-4000-8000-000000000001/projects/__quick_report__/
```

**Workspace paths identical: YES — investigation stops here for storage.**

### On-disk evidence (live data directory)

The dev user directory contains real Quick Report artifacts:

- `data/users/00000000-0000-4000-8000-000000000001/projects/__quick_report__/reports/`
- `data/users/00000000-0000-4000-8000-000000000001/projects/__quick_report__/exports/`
- `data/users/00000000-0000-4000-8000-000000000001/profile.json` (email: `dev@localhost`)

All manual testers using dev bypass read and write **this single tree**.

### Legacy path note

A pre-multi-tenant tree still exists at `data/projects/` (no `users/{id}` prefix). Current services use per-user paths when `CurrentUser` is wired correctly, but dev bypass ensures everyone hits the same `{id}`.

---

## Part 1 — Authentication trace (what logs will show)

Instrumentation added in `core/runtime_investigation.py`, hooked into:

| Event | File | Log event |
|-------|------|-----------|
| Login / session store | `core/auth.py` `_store_session()` | `auth.session` action=`login_or_session_store` |
| Logout | `core/auth.py` `clear_auth_session()` | `auth.session` action=`logout` |
| Registration | `core/auth.py` `sign_up()` | `auth.registration` |
| Dev bypass sign-in | `services/auth_service.py` `sign_in()` | `auth.session` action=`sign_in_dev_bypass`, `requested_email` vs actual |

Example log shape:

```
Authenticated user
  ID: 00000000-0000-4000-8000-000000000001
  Email: dev@localhost
  authentication_backend: AUTH_DEV_BYPASS (local dev — all users share DEV_USER_ID)
  storage_backend: JSON/local filesystem
  workspace_path: data/users/00000000-0000-4000-8000-000000000001/projects/
  quick_report_path: data/users/00000000-0000-4000-8000-000000000001/projects/__quick_report__/
```

Enable with `RUNTIME_INVESTIGATION=true` or `DEBUG=true`. Output: `data/runtime_investigation.log` + stderr.

---

## Part 2–4 — Data loading trace

Instrumentation logs **before access filtering**:

| Data | File | Log event |
|------|------|-----------|
| Projects | `services/project_service.py` `get_projects()` | `data.projects` |
| Documents | `services/document_service.py` `get_documents()` | `data.documents` |
| Reports | `services/report_service.py` `get_reports()` | `data.reports` |

Under dev bypass, all loads will show the same `user_id` and filesystem path regardless of who signed in.

---

## Part 5 — Duplicate email registration

### Why duplicate registration *appears* to succeed

| User action | Duplicate check runs? | Result |
|-------------|----------------------|--------|
| **Sign In** (any email) | **No** | Always succeeds → same `DEV_USER_ID` |
| **Sign Up** (same email twice) | **Yes** (`email_exists`) | Second attempt should fail with `AuthError` |
| **Sign Up** (different emails) | N/A | Both succeed → **same `DEV_USER_ID`** → shared workspace (not a duplicate-email bug) |

### On-disk registry

**File:** `data/auth_email_registry.json`

```json
{
  "ada@example.com": "00000000-0000-4000-8000-000000000099",
  "new.user@example.com": "00000000-0000-4000-8000-000000000001"
}
```

Dev sign-ups map emails to `DEV_USER_ID`. A second `sign_up("new.user@example.com")` should hit `email_exists()` and raise.

### Why manual testers still see “duplicate registration works”

1. They use **Sign In**, not Sign Up — no duplicate gate.
2. They register **different emails** — allowed under dev bypass, but both map to one ID.
3. Session shows signup email briefly, then sign-in restores `dev@localhost` — looks like a new account was created when it was the same tenant all along.

### Email check backend

`EmailUniquenessService.email_exists()` uses JSON registry + profile scan because `use_database()` is false (Supabase not configured). This path works for `sign_up()` but is **never invoked for `sign_in()`**.

---

## Why automated tests pass but manual testing fails

| Automated tests | Manual app session |
|-----------------|-------------------|
| `conftest.py` sets `AUTH_DEV_BYPASS=true` **and** `bind_current_user(TEST_USER)` with distinct IDs per test | Only `AUTH_DEV_BYPASS=true` from `.env` |
| `ProjectService()` uses bound `CurrentUser`, not `dev_sign_in()` | `AuthService.sign_in()` → `dev_sign_in()` → always `DEV_USER_ID` |
| `test_tenant_isolation.py` calls `bind_current_user(USER_B)` before User B actions | Manual User B sign-in never gets a distinct ID |
| Isolation tests never assert that **auth assigns unique IDs** | Manual flow exposes auth-layer collapse |

**The security fixes (CurrentUser, project access, session clearing) are downstream of auth. They cannot compensate when auth assigns one user ID to everyone.**

---

## Files responsible

| File | Role in failure |
|------|-----------------|
| `.env` | Sets `AUTH_DEV_BYPASS=true` for local runs |
| `config.py` | `DEV_USER_ID`, `AUTH_DEV_BYPASS`; weak startup guard (only blocks bypass + Supabase) |
| `services/auth_service.py` | `dev_sign_in()`, `dev_sign_up()`, `sign_in()` bypass branch |
| `core/auth.py` | Stores session from auth service without validating unique identity |
| `core/auth_persistence.py` | Skips cookie restore under bypass; refresh always returns dev user |
| `tests/conftest.py` | Masks auth failure by binding synthetic users |
| `tests/test_security_isolation.py` | Tests services with injected users, not real auth |

---

## How to reproduce with instrumentation

1. Ensure `.env` contains `AUTH_DEV_BYPASS=true` (current state).
2. Set `RUNTIME_INVESTIGATION=true` in `.env`.
3. Run standalone script:
   ```
   python scripts/investigate_tenant_runtime.py
   ```
4. Or run Streamlit, sign in as two different emails, inspect `data/runtime_investigation.log`.

The script prints Parts 5–8 and exits non-zero when IDs collide.

---

## Recommended next step (not implemented per instructions)

Only after accepting this root cause:

1. Disable `AUTH_DEV_BYPASS` for multi-user manual testing.
2. Configure Supabase Auth so `sign_in()` / `sign_up()` return distinct `user.id` values.
3. Add an integration test that exercises **`AuthService.sign_in()`** (not `bind_current_user`) for two users and asserts different IDs and storage roots.

**No security fix was applied in this investigation pass.**
