-- DataDumpAI — Quick Report workspace (user-scoped, no project UUID)

create table if not exists public.quick_report_timeline_events (
    id uuid primary key,
    user_id uuid not null,
    timestamp timestamptz not null,
    action text not null,
    message text not null,
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists quick_report_timeline_events_user_id_idx
    on public.quick_report_timeline_events (user_id, timestamp);

alter table public.quick_report_timeline_events enable row level security;

create policy "Users manage own quick report timeline"
    on public.quick_report_timeline_events for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
