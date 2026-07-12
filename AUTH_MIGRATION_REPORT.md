# Authentication Migration Report — Dev Bypass to Supabase Multi-User

**Date:** 13 July 2026  
**Scope:** Remove `AUTH_DEV_BYPASS` from normal application use; enforce Supabase Auth for all multi-user flows

---

## Summary

DataDumpAI now runs in **true multi-user mode** by default. Every sign-up, sign-in, sign-out, password reset, email verification, and session restoration uses **Supabase Auth** and returns each user's **real Supabase UUID**.

`AUTH_DEV_BYPASS` is **restricted** to `ENVIRONMENT=development` with an explicit opt-in. Any other environment **refuses to start** if `AUTH_DEV_BYPASS=true`.

---

## Configuration changes

| File | Change |
|------|--------|
| `config.py` | Added `ENVIRONMENT` (default `production`). Added `auth_dev_bypass_enabled()` = `ENVIRONMENT=development` AND `AUTH_DEV_BYPASS` requested. Replaced startup guard: block bypass outside development; require Supabase when bypass disabled. |
| `.env.example` | Added `ENVIRONMENT=production`. Documented bypass restriction. `AUTH_DEV_BYPASS=false` by default. |
| `.env` | Removed `AUTH_DEV_BYPASS=true`. Set `ENVIRONMENT=production`, `AUTH_DEV_BYPASS=false`. Supabase credentials must be added. |
| `.env.ci.example` | `ENVIRONMENT=test`, `AUTH_DEV_BYPASS=false` |
| `.github/workflows/test.yml` | CI uses `ENVIRONMENT=test`, `AUTH_DEV_BYPASS=false` |
| `scripts/generate_production_env.sh` | Production sets `ENVIRONMENT=production`. Staging fallback sets `ENVIRONMENT=development` + bypass only when Supabase missing. |
| `deploy/remote-setup.sh` | Added `ENVIRONMENT=development` alongside legacy bypass for transitional deploy scripts. |

---

## `DEV_USER_ID` — removed or restricted

| File | Before | After |
|------|--------|-------|
| `services/auth_service.py` `sign_in()` | Always returned `DEV_USER_ID` when bypass on | Uses Supabase; `dev_sign_in()` only when `auth_dev_bypass_enabled()` |
| `services/auth_service.py` `sign_up()` | Created local account with `DEV_USER_ID` when bypass on | Uses Supabase `auth.sign_up()`; returns real UUID. `dev_sign_up()` isolated to dev bypass only. |
| `services/auth_service.py` `restore_session()` | Replaced session with `dev_sign_in()` → `DEV_USER_ID` | Restores Supabase session via `set_session()` |
| `services/auth_service.py` `refresh_session()` | Replaced session with `dev_sign_in()` | Uses Supabase `refresh_session()` |
| `services/auth_service.py` `sign_up()` (Supabase) | Pre-checked JSON registry + `register_email()` | Removed local pre-check and `register_email()` — Supabase is source of truth for duplicates |
| `core/database.py` | Service-role client when `AUTH_DEV_BYPASS` | Service-role only when `auth_dev_bypass_enabled()` |
| `core/auth_persistence.py` | Skipped cookies when bypass | Skipped cookies only when `auth_dev_bypass_enabled()` |
| `core/auth.py` `_restore_persisted_session()` | Skipped cookie restore when bypass | Cookie restore runs in multi-user mode |
| `tests/conftest.py` | `AUTH_DEV_BYPASS=true` for all tests | Uses `bind_current_user(TEST_USER)` without bypass |
| `ui/auth/page.py` | "Sign in with any email" dev bypass banner | Removed. Error message requires Supabase only. |

`DEV_USER_ID` and `DEV_USER_EMAIL` **remain defined** in `config.py` for the isolated `dev_sign_in()` / `dev_sign_up()` helpers used only when `auth_dev_bypass_enabled()` is true. They are **never used** in normal Supabase flows.

---

## Authentication flow (production)

### Sign-up
1. `ui/auth/forms.py` → `core/auth.sign_up()` → `AuthService.sign_up()`
2. Supabase `auth.sign_up()` with email, password, `full_name` metadata
3. Duplicate email → Supabase error → `AuthError(DUPLICATE_EMAIL_MESSAGE)`
4. Returns `AuthSession` with **real Supabase UUID** or `None` if email verification pending

### Sign-in
1. `AuthService.sign_in()` → Supabase `sign_in_with_password()`
2. Email verification required before session stored
3. Session tokens persisted when "Remember me" enabled

### Session restoration (page refresh)
1. `core/auth.initialize_auth()` reads session tokens from `st.session_state`
2. Falls back to `restore_persisted_tokens()` from browser cookies
3. `AuthService.restore_session(access, refresh)` → Supabase `set_session()`
4. **No `DEV_USER_ID` substitution**

### Sign-out
1. `AuthService.sign_out()` → Supabase `sign_out()`
2. Clears cookies and tenant session

### Password reset / email verification
- Unchanged — already used Supabase via `send_password_reset()`, `exchange_auth_code()`, etc.

---

## Startup guards

`validate_production_auth_configuration()` now fails startup when:

1. `AUTH_DEV_BYPASS=true` and `ENVIRONMENT != development`
2. Supabase is not configured and dev bypass is not enabled

---

## Test changes

| File | Change |
|------|--------|
| `tests/conftest.py` | Removed global `AUTH_DEV_BYPASS=true`. Added `enable_dev_auth_bypass()` helper for legacy dev tests only. |
| `tests/test_auth.py` | Dev bypass tests use `enable_dev_auth_bypass()`. Added `test_supabase_sign_up_returns_distinct_user_ids`, `test_supabase_duplicate_sign_up_returns_error`, `test_restore_session_uses_supabase_tokens`, `test_auth_dev_bypass_blocked_outside_development`. |
| `tests/test_security_isolation.py` | Duplicate email test uses `enable_dev_auth_bypass()`. |
| `tests/test_platform_features.py` | Patches `auth_dev_bypass_enabled` instead of `AUTH_DEV_BYPASS`. |

---

## Manual verification checklist

After adding Supabase credentials to `.env`:

```
ENVIRONMENT=production
AUTH_DEV_BYPASS=false
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

1. **Sign up** `Ahmed@example.com` → note UUID A in Supabase dashboard / session
2. **Sign out**
3. **Sign up** `John@example.com` → note UUID B (must differ from A)
4. **Verify isolation:**
   - `data/users/{UUID_A}/projects/` ≠ `data/users/{UUID_B}/projects/`
   - Projects, documents, reports, Quick Report all scoped per UUID
5. **Duplicate sign-up** `Ahmed@example.com` again → must show duplicate email error from Supabase
6. **Page refresh** while signed in → session restored from tokens, same UUID (not `DEV_USER_ID`)

---

## Files modified

- `config.py`
- `services/auth_service.py`
- `core/auth.py`
- `core/auth_persistence.py`
- `core/database.py`
- `core/runtime_investigation.py`
- `ui/auth/page.py`
- `app.py` (unchanged logic; startup validation uses updated config)
- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_security_isolation.py`
- `tests/test_platform_features.py`
- `.env`, `.env.example`, `.env.ci.example`
- `.github/workflows/test.yml`
- `scripts/generate_production_env.sh`
- `deploy/remote-setup.sh`

---

## Legacy dev bypass (optional, development only)

To use single-user local mode without Supabase (not recommended for multi-user testing):

```
ENVIRONMENT=development
AUTH_DEV_BYPASS=true
```

This still maps all users to `DEV_USER_ID` and must **never** be used for multi-user manual testing.
