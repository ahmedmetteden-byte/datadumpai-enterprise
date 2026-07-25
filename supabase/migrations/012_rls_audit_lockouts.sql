-- DataDumpAI — RLS for service-only and admin-scoped tables
--
-- Safe to run once via supabase migration history. Statements below are also
-- idempotent if re-executed manually (IF NOT EXISTS / DROP POLICY IF EXISTS /
-- CREATE OR REPLACE).
--
-- Audit summary (migrations 001–011):
--   RLS already enabled with owner policies (auth.uid() = user_id):
--     user_profiles, user_usage, projects, documents, reports, exports,
--     timeline_events, user_activity_logs, quick_report_timeline_events
--   RLS missing (this migration):
--     audit_logs, login_lockouts
--
-- Tenancy note:
--   There is no workspace_members / shared-workspace schema. Isolation is
--   single-owner: each project and child row is scoped by user_id. Existing
--   owner policies already enforce "only your workspace data."
--
-- Application note:
--   This migration does not change AdminService or other app code.
--   LockoutService already uses service_role (bypasses RLS).

-- ---------------------------------------------------------------------------
-- Helper: platform admin check (used by audit_logs policies)
-- ---------------------------------------------------------------------------
-- SECURITY DEFINER so the policy can read user_profiles.role without
-- depending on the caller's SELECT policy recursion edge cases.
-- Only returns true when auth.uid() has role = 'admin'.

create or replace function public.is_platform_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.user_profiles
        where user_id = auth.uid()
          and role = 'admin'
    );
$$;

revoke all on function public.is_platform_admin() from public;
grant execute on function public.is_platform_admin() to authenticated;

comment on function public.is_platform_admin() is
    'Returns true when auth.uid() has user_profiles.role = admin. '
    'SECURITY DEFINER helper for RLS policies on admin-only tables '
    '(e.g. audit_logs). Ordinary users always get false.';

-- ---------------------------------------------------------------------------
-- login_lockouts — enable RLS, no policies for anon/authenticated
-- ---------------------------------------------------------------------------
-- Why: stores emails, failed attempt counts, and lock timestamps. Written
-- before authentication by LockoutService via the service role. Any JWT
-- access would be a privilege escalation.
--
-- Policy set: none.
-- Effect with RLS enabled + no policies:
--   - anon / authenticated: denied
--   - service_role: bypasses RLS (unchanged app path)

alter table public.login_lockouts enable row level security;

-- Explicitly force RLS even for table owners (defense in depth on managed
-- Postgres roles). service_role still bypasses RLS by design in Supabase.
alter table public.login_lockouts force row level security;

comment on table public.login_lockouts is
    'Pre-auth lockout state (email, failure counts, lock expiry). '
    'RLS is enabled with no policies so anon/authenticated cannot access; '
    'only service_role (LockoutService) may read or write.';

-- ---------------------------------------------------------------------------
-- audit_logs — enable RLS; platform admins only
-- ---------------------------------------------------------------------------
-- Why: cross-tenant admin actions (actor, target, metadata). Must not be
-- readable or writable by ordinary authenticated users.
--
-- Policies below:
--   1) Admins can SELECT all rows (admin console).
--   2) Admins can INSERT rows only when actor_user_id = auth.uid()
--      (cannot forge another actor).
--   No UPDATE / DELETE policies — audit trail is append-only under JWT.
--   service_role still bypasses RLS for server-side maintenance.

alter table public.audit_logs enable row level security;
alter table public.audit_logs force row level security;

comment on table public.audit_logs is
    'Platform admin action history. RLS restricts JWT access to admins; '
    'no UPDATE/DELETE policies keep the trail append-only for authenticated.';

drop policy if exists "Admins read audit logs" on public.audit_logs;
create policy "Admins read audit logs"
    on public.audit_logs
    for select
    to authenticated
    using (public.is_platform_admin());

comment on policy "Admins read audit logs"
    on public.audit_logs is
    'Allows platform administrators to review audit history. '
    'Ordinary authenticated users have no SELECT policy and are denied. '
    'Audit logs remain append-only.';

drop policy if exists "Admins insert own audit actions" on public.audit_logs;
create policy "Admins insert own audit actions"
    on public.audit_logs
    for insert
    to authenticated
    with check (
        public.is_platform_admin()
        and actor_user_id = auth.uid()
    );

comment on policy "Admins insert own audit actions"
    on public.audit_logs is
    'Allows platform administrators to record their own actions only '
    '(actor_user_id must equal auth.uid()). Audit logs remain append-only: '
    'there are no UPDATE or DELETE policies for authenticated.';
