-- DataDumpAI Phase 2 — PostgreSQL schema (Supabase)
-- Run in Supabase SQL Editor or via supabase db push

-- ---------------------------------------------------------------------------
-- User profile (extends Supabase Auth users)
-- ---------------------------------------------------------------------------

create table if not exists public.user_profiles (
    user_id uuid primary key,
    full_name text not null default '',
    company text not null default '',
    job_title text not null default '',
    photo_url text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Subscription usage counters
-- ---------------------------------------------------------------------------

create table if not exists public.user_usage (
    user_id uuid primary key,
    plan text not null default 'free',
    period text not null,
    reports_generated integer not null default 0,
    uploads integer not null default 0,
    updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Projects
-- ---------------------------------------------------------------------------

create table if not exists public.projects (
    id uuid primary key,
    user_id uuid not null,
    name text not null,
    description text not null default '',
    storage_used bigint not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_activity timestamptz not null default now(),
    unique (user_id, name)
);

create index if not exists projects_user_id_idx on public.projects (user_id);

-- ---------------------------------------------------------------------------
-- Documents (metadata — files stay on disk / object storage)
-- ---------------------------------------------------------------------------

create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects (id) on delete cascade,
    user_id uuid not null,
    filename text not null,
    size bigint not null default 0,
    storage_path text not null,
    uploaded_at timestamptz not null default now(),
    unique (project_id, filename)
);

create index if not exists documents_project_id_idx on public.documents (project_id);

-- ---------------------------------------------------------------------------
-- Reports
-- ---------------------------------------------------------------------------

create table if not exists public.reports (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects (id) on delete cascade,
    user_id uuid not null,
    filename text not null,
    name text not null,
    storage_path text not null,
    size bigint not null default 0,
    report_type text not null default '',
    source_documents jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    unique (project_id, filename)
);

create index if not exists reports_project_id_idx on public.reports (project_id);

-- ---------------------------------------------------------------------------
-- Exports
-- ---------------------------------------------------------------------------

create table if not exists public.exports (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects (id) on delete cascade,
    user_id uuid not null,
    filename text not null,
    format text not null default '',
    mime_type text not null default '',
    size bigint not null default 0,
    storage_path text not null,
    exported_at timestamptz not null default now(),
    unique (project_id, filename)
);

create index if not exists exports_project_id_idx on public.exports (project_id);

-- ---------------------------------------------------------------------------
-- Timeline events
-- ---------------------------------------------------------------------------

create table if not exists public.timeline_events (
    id uuid primary key,
    project_id uuid not null references public.projects (id) on delete cascade,
    user_id uuid not null,
    timestamp timestamptz not null,
    action text not null,
    message text not null,
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists timeline_events_project_id_idx
    on public.timeline_events (project_id, timestamp);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------

alter table public.user_profiles enable row level security;
alter table public.user_usage enable row level security;
alter table public.projects enable row level security;
alter table public.documents enable row level security;
alter table public.reports enable row level security;
alter table public.exports enable row level security;
alter table public.timeline_events enable row level security;

create policy "Users manage own profile"
    on public.user_profiles for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage own usage"
    on public.user_usage for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage own projects"
    on public.projects for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage own documents"
    on public.documents for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage own reports"
    on public.reports for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage own exports"
    on public.exports for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage own timeline events"
    on public.timeline_events for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Updated-at trigger
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists user_profiles_updated_at on public.user_profiles;
create trigger user_profiles_updated_at
    before update on public.user_profiles
    for each row execute function public.set_updated_at();

drop trigger if exists user_usage_updated_at on public.user_usage;
create trigger user_usage_updated_at
    before update on public.user_usage
    for each row execute function public.set_updated_at();

drop trigger if exists projects_updated_at on public.projects;
create trigger projects_updated_at
    before update on public.projects
    for each row execute function public.set_updated_at();
