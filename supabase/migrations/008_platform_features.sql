-- DataDumpAI — Onboarding, activity logs, and login lockout

alter table public.user_profiles
    add column if not exists onboarding_completed boolean not null default false,
    add column if not exists onboarding_step integer not null default 1,
    add column if not exists onboarding_completed_at timestamptz;

-- ---------------------------------------------------------------------------
-- User activity logs (account-level audit trail)
-- ---------------------------------------------------------------------------

create table if not exists public.user_activity_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    action text not null,
    message text not null default '',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists user_activity_logs_user_id_idx
    on public.user_activity_logs (user_id, created_at desc);

alter table public.user_activity_logs enable row level security;

create policy "Users view own activity logs"
    on public.user_activity_logs for select
    using (auth.uid() = user_id);

create policy "Users insert own activity logs"
    on public.user_activity_logs for insert
    with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Login lockout (server-side only — accessed via service role)
-- ---------------------------------------------------------------------------

create table if not exists public.login_lockouts (
    email text primary key,
    failed_count integer not null default 0,
    locked_until timestamptz,
    last_attempt_at timestamptz not null default now()
);

create index if not exists login_lockouts_locked_until_idx
    on public.login_lockouts (locked_until);

-- No RLS policies — service role manages lockout records before authentication.
