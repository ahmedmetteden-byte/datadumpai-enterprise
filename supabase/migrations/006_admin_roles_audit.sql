-- DataDumpAI Phase 6 — Admin audit logs

create table if not exists public.audit_logs (
    id uuid primary key default gen_random_uuid(),
    actor_user_id uuid,
    action text not null,
    target_type text,
    target_id text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists audit_logs_created_at_idx on public.audit_logs (created_at desc);
create index if not exists audit_logs_actor_user_id_idx on public.audit_logs (actor_user_id);

-- Service role bypasses RLS; admins query via service role in AdminService.
