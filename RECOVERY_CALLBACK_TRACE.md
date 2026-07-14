# Password Recovery Callback Trace

Temporary instrumentation for debugging the Supabase password-reset redirect flow.  
**Recovery logic is unchanged** — only logging was added.

## Enable tracing

Set in `.env` or the environment:

```env
RECOVERY_CALLBACK_TRACE=true
```

Or use existing debug mode:

```env
DEBUG=true
```

Restart Streamlit, click a password-reset email link, then inspect:

- **Log file:** `data/recovery_callback_trace.log` (JSON lines, one event per step)
- **stderr:** `[RECOVERY_CALLBACK_TRACE] <step>` lines in the Streamlit terminal

Each log entry includes:

| Field | Description |
|-------|-------------|
| `query_params.type` | `recovery`, `signup`, etc. |
| `query_params.code` | `{present, length, prefix}` — never full value |
| `query_params.token_hash` | `{present, length, prefix}` |
| `query_params.access_token` | `{present, length, prefix}` |
| `query_params.refresh_token` | `{present, length, prefix}` |
| `branch` | `pkce` \| `otp` \| `none` |
| `auth_state.auth_recovery_mode` | Whether recovery mode is active |
| `auth_state.auth_view` | Current auth view (`sign_in`, `reset_password`, …) |

---

## Execution path (code order)

```
app.py
  └─ initialize_auth()                 → step: initialize_auth.*
       └─ handle_auth_callback_query_params()  → step: callback.*
            ├─ auth_type != recovery → callback.exit (not handled)
            ├─ error query params → recovery.fail
            ├─ type=recovery but no code/token_hash → callback.exit (not handled)
            └─ _establish_recovery_session_from_callback()
                 ├─ branch otp  → AuthService.exchange_recovery_token_hash → verify_otp
                 └─ branch pkce → AuthService.exchange_recovery_code → exchange_code_for_session
                      ├─ success → _store_recovery_session() → auth_recovery_mode=True
                      └─ failure → recovery.fail → auth_recovery_mode=False, auth_view=sign_in

  └─ unauthenticated routing           → step: app.unauthenticated_routing
       ├─ active_page=auth → render_auth_gate()
       └─ active_page=landing → landing page (auth gate never runs)

ui/auth/page.py render_auth_page()     → step: auth_page.*
       ├─ is_authenticated() == True → early return (should not happen during recovery)
       ├─ auth_recovery_mode → render_reset_password_form()
       └─ auth_view == sign_in → render_sign_in_form()
```

---

## Branch selection rules

`select_recovery_branch()` in `core/recovery_callback_trace.py` mirrors the handler in `core/auth_callbacks.py`:

| Priority | Condition | Branch | Supabase API |
|----------|-----------|--------|--------------|
| 1 | `token_hash` present | **otp** | `client.auth.verify_otp({type: recovery, token_hash})` |
| 2 | `code` present | **pkce** | `client.auth.exchange_code_for_session({auth_code: code})` |
| — | none of the above | **none** | Handler returns `handled=False` |

Implicit `#access_token=...` / query token pairs are **not** handled. Auth client uses `flow_type="pkce"` so reset emails should land on `?active_page=auth&type=recovery&code=...`.

Log step: `recovery.branch_selected`

---

## Supabase exchange logging

Each exchange logs step `supabase.<operation>` with:

- `supabase_success` — `True` when session+user returned
- `session_returned` — whether `response.session` was non-null
- `user_returned` — whether `response.user` was non-null
- `exception_type` / `supabase_error` — on failure

| Operation | Branch | Method |
|-----------|--------|--------|
| `exchange_code_for_session` | pkce | PKCE code exchange |
| `verify_otp` | otp | Email token hash |

---

## When `auth_recovery_mode` becomes `True`

Only in `_store_recovery_session()` (`core/auth.py`), called after a **successful** exchange in `handle_auth_callback_query_params()`.

Log step: `store_recovery_session` with `auth_recovery_mode=True`, `auth_view=reset_password`, `active_page=auth`.

---

## When `auth_recovery_mode` is cleared / stays `False`

| Scenario | Step | `auth_recovery_mode` after | `auth_view` |
|----------|------|---------------------------|-------------|
| Exchange succeeds | `callback.success` | **True** | `reset_password` |
| Exchange fails (`AuthError`) | `recovery.fail` | **False** (explicitly cleared) | `sign_in` |
| Exchange fails (other exception) | `recovery.fail` | **False** | `sign_in` |
| Supabase `error` query param | `recovery.fail` | **False** | `sign_in` |
| `type=recovery` but no code/token_hash | `callback.exit` | unchanged (usually **False**) | usually `sign_in` |
| `auth_type` not `recovery` | `callback.exit` | unchanged | unchanged |
| Callback skipped (recovery already active) | `initialize_auth.exit` | **True** (unchanged) | `reset_password` |

Log step for explicit clear: `recovery.fail` with `cleared_recovery_mode=True`.

---

## Why the app renders Sign In (decision tree)

Use log step `auth_page.render` and `explain_sign_in` from `app.unauthenticated_routing`.

### Renders **Reset Password**

- `auth_recovery_mode == True`  
  Log: `auth_page.view` = `reset_password_form`

### Renders **Sign In**

All of the following must hold:

1. `auth_recovery_mode == False`
2. `auth_view == "sign_in"` (default, or set by `recovery.fail`)
3. `render_auth_page()` reached (`active_page == "auth"`)

Common causes visible in logs:

| Log pattern | Likely cause |
|-------------|--------------|
| `callback.exit` + `reason=recovery_type_without_actionable_tokens` | `type=recovery` in URL but missing `code` / `token_hash` (e.g. old implicit hash link) |
| `supabase.exchange_code_for_session` + `session_returned=false` | PKCE exchange returned no session |
| `supabase.verify_otp` + `exception_type=...` | OTP/token_hash rejected by Supabase |
| `recovery.exchange_auth_error` / `callback.exchange_failed` | Exchange threw; `recovery.fail` cleared mode and set `auth_view=sign_in` |
| `app.unauthenticated_routing` + `page=landing` | Redirect URL did not land on `active_page=auth`; auth gate never runs |
| `callback.exit` + `reason=auth_type_not_recovery` | Link missing `type=recovery` query param |
| `initialize_auth.exit` + `reason=recovery_mode_active` skipped re-processing | Recovery already established (should show reset form, not sign in) |

### Does **not** reach auth page at all

| Log pattern | Result |
|-------------|--------|
| `app.unauthenticated_routing` + `page=landing` | Landing page shown |

---

## Key log steps reference

| Step | Location | Meaning |
|------|----------|---------|
| `initialize_auth.enter` | `core/auth.py` | Auth init started |
| `callback.enter` | `auth_callbacks.py` | Recovery handler entered; logs branch |
| `recovery.branch_selected` | `auth_callbacks.py` | Which exchange path runs |
| `supabase.*` | `auth_service.py` | Raw Supabase call outcome |
| `callback.exchange_success` | `auth_callbacks.py` | Session object obtained |
| `store_recovery_session` | `core/auth.py` | Recovery mode enabled |
| `recovery.fail` | `auth_callbacks.py` | Failure; mode cleared |
| `app.unauthenticated_routing` | `app.py` | Page routing decision |
| `auth_page.render` | `ui/auth/page.py` | Why sign-in vs reset form |
| `auth_page.view` | `ui/auth/page.py` | Final form rendered |

---

## How to read a failing trace (example)

```json
{"step": "callback.enter", "auth_type": "recovery", "branch": "pkce"}
{"step": "recovery.branch_selected", "branch": "pkce"}
{"step": "supabase.exchange_code_for_session", "supabase_success": false, "exception_type": "AuthApiError", "supabase_error": "..."}
{"step": "recovery.fail", "cleared_recovery_mode": true}
{"step": "auth_page.render", "renders_sign_in": true, "auth_recovery_mode": false}
{"step": "auth_page.view", "view": "sign_in"}
```

**Interpretation:** PKCE branch selected, Supabase rejected `exchange_code_for_session`, recovery mode cleared, Sign In shown with error.

---

## Remove instrumentation

When debugging is complete, delete or disable:

- `core/recovery_callback_trace.py`
- `RECOVERY_CALLBACK_TRACE` log calls in `auth_callbacks.py`, `auth.py`, `app.py`, `auth_service.py`, `ui/auth/page.py`
- This file

Set `RECOVERY_CALLBACK_TRACE=false` to silence without removing code.
