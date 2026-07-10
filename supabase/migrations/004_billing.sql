-- DataDumpAI Phase 4 — Payment provider fields on user_usage

alter table public.user_usage
    add column if not exists payment_provider text,
    add column if not exists payment_customer_id text,
    add column if not exists payment_subscription_id text,
    add column if not exists payment_reference text,
    add column if not exists cancel_at_period_end boolean not null default false,
    add column if not exists current_period_end timestamptz;

create index if not exists user_usage_payment_customer_id_idx
    on public.user_usage (payment_customer_id);

create index if not exists user_usage_payment_subscription_id_idx
    on public.user_usage (payment_subscription_id);
