-- DataDumpAI Phase 5 — Profile preferences and notification settings

alter table public.user_profiles
    add column if not exists timezone text not null default 'UTC',
    add column if not exists locale text not null default 'en',
    add column if not exists role text not null default 'user',
    add column if not exists notification_preferences jsonb not null default '{
        "report_ready": true,
        "usage_alerts": true,
        "billing": true,
        "product_updates": false
    }'::jsonb;

create index if not exists user_profiles_role_idx on public.user_profiles (role);
