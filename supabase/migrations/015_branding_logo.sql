-- DataDumpAI — custom report logo for Professional+ plans ("Branded reports
-- with your logo"). Stores the Supabase Storage key (or local path) of the
-- account's uploaded logo; empty string means no custom logo is set.

alter table public.user_profiles
    add column if not exists branding_logo_key text not null default '';
