-- DataDumpAI Phase 3 — Subscription fields on user_usage

alter table public.user_usage
    add column if not exists subscription_status text not null default 'none',
    add column if not exists trial_ends_at timestamptz,
    add column if not exists billing_plan text;

-- Backfill billing_plan from existing plan column
update public.user_usage
set billing_plan = plan
where billing_plan is null;
