# Config Investigation Report — `.env` vs Runtime Auth Values

**Date:** 13 July 2026  
**Scope:** Why browser shows `ENVIRONMENT='production'` and an error mentioning `AUTH_DEV_BYPASS=true` when `.env` has `ENVIRONMENT=development` and `AUTH_DEV_BYPASS=false`  
**Status:** Root cause identified — **no fix applied** (debug instrumentation added only)

---

## Executive summary

**The `.env` file is not wrong. The runtime process is not reading it as the sole source of truth.**

Two separate mechanisms explain the mismatch:

| Symptom | Root cause | File | Line |
|---------|------------|------|------|
| `ENVIRONMENT='production'` while `.env` says `development` | `load_dotenv(..., override=False)` does **not** overwrite variables already in `os.environ`; `os.getenv("ENVIRONMENT", "production")` then reads the stale value or defaults to `"production"` | `config.py` | 11, 53 |
| Error text includes `AUTH_DEV_BYPASS=true` | **Static wording** in the error template — not a runtime value dump | `config.py` | 115 |
| `_AUTH_DEV_BYPASS_REQUESTED` is `True` at runtime | `AUTH_DEV_BYPASS` already set to `true`/`1`/`yes` in `os.environ` **before** `load_dotenv` runs (Docker `env_file`, container env, IDE, shell, unrestarted process) | `config.py` | 11, 56–60 |

---

## Step 1 — Debug instrumentation (added)

`validate_production_auth_configuration()` in `config.py` now prints before validation:

```
===== AUTH CONFIG DEBUG =====
ENVIRONMENT: ...
AUTH_DEV_BYPASS: ...
AUTH_DEV_BYPASS_REQUESTED: ...
SUPABASE_URL: ...
SUPABASE_ANON_KEY: ...
os.getenv('ENVIRONMENT'): ...
os.getenv('AUTH_DEV_BYPASS'): ...
_PROJECT_ROOT: ...
.env path: ...
.env exists: ...
=============================
```

Restart Streamlit and read the **terminal** (not only the browser) for this block.

---

## Step 2 — How `AUTH_DEV_BYPASS` is calculated

```53:63:c:\Users\ahmed\Downloads\DataDumpAI-Enterprise\config.py
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()

_AUTH_DEV_BYPASS_REQUESTED = os.getenv("AUTH_DEV_BYPASS", "false").lower() in {
    "1",
    "true",
    "yes",
}

AUTH_DEV_BYPASS = _AUTH_DEV_BYPASS_REQUESTED
```

| Question | Answer |
|----------|--------|
| Comes directly from `.env`? | **Only if** `AUTH_DEV_BYPASS` is not already in `os.environ` when line 11 runs |
| Derived from another variable? | No — direct `os.getenv` parse |
| Overwritten later? | **No** — module constants are set once at import and never updated |
| Inverted accidentally? | No |
| Wrong default? | Default when unset is `"false"` → `False` (correct) |

`auth_dev_bypass_enabled()` (line 69–72) additionally requires `ENVIRONMENT == "development"` but the **startup error** checks `_AUTH_DEV_BYPASS_REQUESTED` directly (line 113).

---

## Step 3 — How `ENVIRONMENT` is calculated

```11:11:c:\Users\ahmed\Downloads\DataDumpAI-Enterprise\config.py
load_dotenv(_PROJECT_ROOT / ".env")
```

```53:53:c:\Users\ahmed\Downloads\DataDumpAI-Enterprise\config.py
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
```

| Question | Answer |
|----------|--------|
| Read from `.env`? | Only via `load_dotenv` on line 11, and only if `ENVIRONMENT` is **not** already in `os.environ` |
| Defaults to `"production"`? | **Yes** — line 53 when `os.getenv("ENVIRONMENT")` returns `None` |
| Overwritten later? | No — frozen at import |
| Hardcoded? | Default `"production"` on line 53 only |

---

## Step 4 — Exact lines responsible for the mismatch

### A) `.env` ignored because `override=False` (primary code path)

**File:** `config.py`  
**Line:** 11

```python
load_dotenv(_PROJECT_ROOT / ".env")  # override=False by default
```

python-dotenv **never overwrites** keys that already exist in `os.environ`.

**Reproduced locally:**

```
# Pre-inject (simulates Docker env_file / shell / IDE):
os.environ['ENVIRONMENT'] = 'production'
os.environ['AUTH_DEV_BYPASS'] = 'true'

load_dotenv(project/.env, override=False)

os.getenv('ENVIRONMENT')      # → 'production'  (NOT 'development' from .env)
os.getenv('AUTH_DEV_BYPASS')  # → 'true'        (NOT 'false' from .env)
```

Then `config` import yields:
- `ENVIRONMENT = 'production'` (line 53)
- `_AUTH_DEV_BYPASS_REQUESTED = True` (lines 56–60)

→ Triggers the startup error at lines 113–118.

**This exactly matches the browser error** (`ENVIRONMENT='production'` + bypass requested).

### B) `ENVIRONMENT` falls back to `"production"` when unset

**File:** `config.py`  
**Line:** 53

If `load_dotenv` fails or `.env` is not found and nothing is in `os.environ`, `ENVIRONMENT` becomes `"production"`.

### C) Error message misread as runtime diagnostics

**File:** `config.py`  
**Lines:** 114–117

```python
"AUTH_DEV_BYPASS=true is only permitted when ENVIRONMENT=development. "
f"Current ENVIRONMENT={ENVIRONMENT!r}. ..."
```

The substring **`AUTH_DEV_BYPASS=true` is hardcoded rule text**, not `print(f"AUTH_DEV_BYPASS={AUTH_DEV_BYPASS}")`.  
The **only** live value in the message is `Current ENVIRONMENT='production'`.

---

## Runtime debug output (fresh process — correct `.env` load)

Simulated clean import from project root (no pre-injected env):

```
=== PRE-LOAD ===
getenv ENVIRONMENT: None
getenv AUTH_DEV_BYPASS: None
load_dotenv returned: True

=== POST load_dotenv ===
getenv ENVIRONMENT: 'development'
getenv AUTH_DEV_BYPASS: 'false'

=== AFTER config import ===
config.ENVIRONMENT: 'development'
config.AUTH_DEV_BYPASS: False
config._AUTH_DEV_BYPASS_REQUESTED: False

warnings: ['Supabase Auth is required for multi-user mode...']
```

**Conclusion:** When nothing pre-seeds `os.environ`, `.env` loads correctly. The bug appears only when the **process environment** already contains conflicting values.

---

## Why Windows “empty” env vars does not rule out pre-injection

These sources set `os.environ` **inside the Python process** but do **not** appear in Windows System Environment Variables UI:

| Source | Typical values | Visible in Windows env UI? |
|--------|----------------|----------------------------|
| **Docker Compose `env_file: .env`** | Injects at container start; stale until `docker compose up --force-recreate` | No (container-only) |
| **Cursor / VS Code `launch.json` env** | Per-run injection | No |
| **Parent PowerShell session** | `$env:AUTH_DEV_BYPASS="true"` for that session | No (session-only) |
| **Streamlit process not restarted** | Module constants from **first** import with old values | N/A — not in Windows registry at all |
| **Old `.env` at container build time** | Baked into image `COPY . .` | No |

---

## Variable trace summary

| Variable | `.env` on disk | Fresh Python import | Process with pre-injected env |
|----------|----------------|---------------------|-------------------------------|
| `os.getenv("ENVIRONMENT")` | N/A | `development` | `production` |
| `os.getenv("AUTH_DEV_BYPASS")` | N/A | `false` | `true` |
| `config.ENVIRONMENT` | N/A | `development` | `production` |
| `config._AUTH_DEV_BYPASS_REQUESTED` | N/A | `False` | `True` |
| Startup bypass error | No | No | **Yes** |

---

## Recommended next checks (no code changes yet)

1. **Restart Streamlit completely** (kill terminal, not browser refresh) and read terminal `===== AUTH CONFIG DEBUG =====` output.
2. If using **Docker**: run `docker compose exec app env | grep -E 'ENVIRONMENT|AUTH_DEV_BYPASS'` — compare to host `.env`.
3. Recreate container after `.env` edits: `docker compose up --force-recreate`.
4. Check Cursor run configuration for injected `ENVIRONMENT` / `AUTH_DEV_BYPASS`.
5. Compare `os.getenv` vs module constants in debug output — if they match but differ from `.env`, pre-injection is confirmed.

---

## Exact root cause (one sentence)

**`config.py` line 11 loads `.env` with `override=False`, so any `ENVIRONMENT=production` and `AUTH_DEV_BYPASS=true` already present in the process environment (Docker, IDE, unrestarted session, or stale container) wins over the on-disk `.env`; line 53 then materializes `ENVIRONMENT='production'` and lines 56–60 set `_AUTH_DEV_BYPASS_REQUESTED=True`, triggering the error at lines 113–118 — while the browser error text misleadingly includes the literal string `AUTH_DEV_BYPASS=true` as policy wording, not as a live variable dump.**
