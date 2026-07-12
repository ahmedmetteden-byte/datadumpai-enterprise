# DataDumpAI Security Audit Report

**Date:** 12 July 2026  
**Scope:** Multi-tenant isolation, authentication, session lifecycle, Quick Report, AI Workspace  
**Status:** Remediated with automated test coverage (39 passing isolation/auth tests)

---

## Executive Summary

A full security audit identified **release-blocking gaps** in tenant session hygiene, path traversal defense, duplicate account creation, and incomplete session clearing on user switch/logout. All identified issues in scope have been remediated. Automated tests now fail if cross-user access regresses.

**Fail-closed principle applied:** Any component that cannot positively verify the authenticated user and project ownership returns **no data** (empty lists) or raises **PermissionError** — never another user's content.

**CurrentUser context:** Services obtain the authenticated user via `core/current_user.require_current_user()` — they do not accept a raw `user_id` from UI code. Unauthenticated access raises `AuthenticationRequiredError`. Admin and webhook paths use explicit `for_user_id()` / `current_user_scope()` internal APIs only.

---

## Root Causes

### 1. Incomplete tenant session clearing (HIGH)
**Root cause:** `core/tenant_session.py` only cleared a fixed list of keys. AI Workspace conversation (`ai_workspace_messages`), copilot web sources, visualization feedback keys, and notification state persisted across user switches in the same browser tab.

**Impact:** User B could see User A's conversation text, draft reports, and copilot context on a shared machine.

**Fix:** Expanded `TENANT_DATA_KEYS`, added `TENANT_KEY_PREFIXES` sweep for `ai_workspace_*`, `copilot_*`, `project_report_documents_*`, and visual insights message keys. Cleared on `ensure_tenant_context()` and `clear_auth_session()`.

### 2. Path traversal via `project_id` (MEDIUM → HIGH)
**Root cause:** `FileStore._local_root()` joined `project_id` without validating `..` or path separators. `list_files()` and `write()` did not enforce ownership before access.

**Impact:** A tampered `project_id` could escape the user's projects root and list another user's filesystem data (latent; mitigated by UUID project IDs in UI).

**Fix:** `validate_project_id()` rejects `..`, `/`, `\`. Resolved paths must stay under the user's projects root. All file store operations use sanitized IDs.

### 3. Missing project ownership checks (MEDIUM)
**Root cause:** `DocumentService`, `ReportService`, and `ExportService` accessed filesystem paths for any `project_id` under the user's root without verifying project membership in `projects.json`.

**Impact:** Orphaned or manipulated folders could be read within the same user account; foreign project IDs from another user now fail closed.

**Fix:** `core/project_access.py` — `assert_project_access()` verifies Quick Report (virtual, user-scoped) or registered project ownership. List operations return `[]` on denial; reads raise `PermissionError`.

### 4. Duplicate email registration (HIGH for production)
**Root cause:** `AuthService.sign_up()` did not normalize email or check for existing accounts before calling Supabase. Dev bypass allowed unlimited sign-ups to the same dev user.

**Impact:** Duplicate accounts, confusing auth state, potential data fragmentation.

**Fix:** `services/email_uniqueness.py` — normalize (trim + lowercase), pre-check via JSON registry or Supabase `user_profiles`, backend unique index migration `009_unique_email.sql`. UI shows "Sign In" / "Forgot Password" on duplicate.

### 5. Stale workspace content on project switch (LOW)
**Root cause:** Switching Quick Report ↔ Project did not clear `selected_report`, `draft_report`, or document selection state.

**Fix:** `_clear_workspace_content_state()` in `ui/projects.py` on workspace mode changes.

### 6. `AUTH_DEV_BYPASS` in production (CRITICAL if misconfigured)
**Root cause:** Dev bypass collapses all users into `DEV_USER_ID` with service-role DB access.

**Fix:** `validate_production_auth_configuration()` blocks app startup when `AUTH_DEV_BYPASS=true` and Supabase is configured.

---

## Part 1 — Tenant Isolation Audit

| Data type | Storage | User filter | Ownership check | Fail-closed |
|-----------|---------|-------------|-----------------|-------------|
| Projects | JSON / Supabase | `user_id` in repository | `project_exists()` | Yes |
| Documents | FileStore per user | `FileStore.for_current_user()` | `assert_project_access()` | Yes — `[]` |
| Reports | FileStore per user | `FileStore.for_current_user()` | `assert_project_access()` | Yes — `[]` / raise |
| Exports | FileStore per user | Current user store | `assert_project_access()` | Yes — `[]` |
| Conversations | Streamlit session | Cleared on user switch | N/A (ephemeral) | Yes — cleared |
| Report previews | `draft_report` session | Cleared on user switch | N/A | Yes — cleared |
| Visualizations | Report `charts` dict | Per-user report files | Via report access | Yes |
| Quick Report | `__quick_report__` per user FS | User-scoped root | Virtual ID + FS isolation | Yes |
| AI context | Session + user documents | Tenant session + project access | Yes | Yes |

**Supabase:** All repositories use `.eq("user_id", ...)`. RLS enforced when using user JWT (not dev bypass).

---

## Part 2 — Authentication

- Email normalized: `strip()` + `lower()` before all checks and sign-up
- Duplicate check: `EmailUniquenessService.email_exists()` before account creation
- Backend: `009_unique_email.sql` unique index on `lower(email)`
- UI: Duplicate message with **Sign In** and **Forgot Password** actions
- Supabase `sign_up` errors mapped to duplicate message

---

## Part 3 — Quick Report

- Virtual ID `__quick_report__` is **not global** — physical path is `data/users/{user_id}/projects/__quick_report__/`
- User B cannot list or read User A's Quick Report documents (tested)
- `assert_project_access()` allows Quick Report only within authenticated user's store

---

## Part 4 — AI Workspace

- Documents/reports loaded via `DocumentService` / `ReportService` with project access checks
- Conversation in `ai_workspace_messages` — cleared on user switch
- Visual insights cache keys cleared on tenant session reset
- `ai_workspace_excluded_*` / `ai_workspace_selected_*` cleared via prefix sweep

---

## Part 5 — Session Lifecycle Scenario

| Step | Expected | Verified |
|------|----------|----------|
| User A login, upload, generate | Data under `users/{A}/` | Yes |
| User A logout | All tenant session keys cleared | Yes |
| User B login | Zero projects, docs, reports, AI context | Yes |
| User B logout, User A login | User A data restored | Yes |

---

## Part 6 — Test Coverage

**File:** `tests/test_security_isolation.py` (new) + `tests/test_tenant_isolation.py` + `tests/test_auth.py`

| Test | Status |
|------|--------|
| Require authenticated user (fail closed) | ✓ |
| Login after logout / session reset | ✓ |
| Session reset (AI, copilot, drafts) | ✓ |
| Quick Report isolation | ✓ |
| Project isolation | ✓ |
| Report isolation | ✓ |
| Export isolation | ✓ |
| Conversation isolation | ✓ |
| Visualization cache isolation | ✓ |
| Cached report / draft isolation | ✓ |
| Filesystem path traversal blocked | ✓ |
| FileStore traversal rejected | ✓ |
| JSON backend per-user roots | ✓ |
| Switching users in same browser session | ✓ |
| User A data restored after return | ✓ |

**Run:** `python -m pytest tests/test_security_isolation.py tests/test_tenant_isolation.py tests/test_auth.py`

**Result:** 39 passed

---

## Files Changed

| File | Change |
|------|--------|
| `core/tenant_session.py` | Expanded session clearing, prefix sweep |
| `core/project_access.py` | **New** — fail-closed project access |
| `services/email_uniqueness.py` | **New** — email normalization + duplicate check |
| `services/auth_service.py` | Duplicate prevention, normalized email |
| `services/user_bootstrap.py` | Register email on bootstrap |
| `services/document_service.py` | Project access on read/write |
| `services/report_service.py` | Project access on all report ops |
| `services/export_service.py` | Project access on export listing |
| `storage/file_store.py` | Path traversal protection |
| `ui/projects.py` | Clear workspace content on switch |
| `ui/auth/forms.py` | Duplicate email UX (Sign In / Forgot Password) |
| `config.py` | Production auth misconfiguration guard |
| `app.py` | Block startup on AUTH_DEV_BYPASS + Supabase |
| `supabase/migrations/009_unique_email.sql` | **New** — unique email index |
| `tests/test_security_isolation.py` | **New** — comprehensive isolation tests |
| `tests/test_auth.py` | Duplicate email + test isolation fixes |

---

## Verification Steps (Manual)

1. **User switch:** Sign in as User A → upload doc → generate report → sign out → sign in as User B → confirm empty workspace → sign out → sign in as User A → confirm data restored.
2. **Duplicate email:** Attempt to create account with existing email → see duplicate message with Sign In / Forgot Password.
3. **Quick Report:** User A uploads to Quick Report → User B cannot see file in My Documents or AI Workspace.
4. **Production guard:** Set `AUTH_DEV_BYPASS=true` with Supabase configured → app shows fatal error and stops.
5. **Automated:** Run `pytest tests/test_security_isolation.py tests/test_tenant_isolation.py tests/test_auth.py` — all must pass.

---

## Residual Risks (Documented, Out of Scope)

| Risk | Mitigation |
|------|------------|
| `AUTH_DEV_BYPASS=true` in dev/CI | Blocked when Supabase configured; never enable in production |
| Admin cross-tenant queries | Gated by `is_admin()`; relies on RLS + router |
| Global `FeedbackService` store | Admin-only read; no tenant PII |
| Same-user cross-project doc selection | By design for power users |

---

## Conclusion

Multi-tenant isolation is enforced at **filesystem**, **repository**, **service**, **session**, and **authentication** layers with fail-closed defaults. Automated tests prove isolation across JSON backend paths; Supabase isolation relies on RLS + explicit `user_id` filters + unique email constraint. **Do not release without passing the full security test suite.**
