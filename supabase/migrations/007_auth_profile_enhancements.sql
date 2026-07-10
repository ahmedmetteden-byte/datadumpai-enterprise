-- DataDumpAI — Auth profile enhancements (email, last_login, signup trigger)

alter table public.user_profiles
    add column if not exists email text not null default '',
    add column if not exists last_login timestamptz;

create index if not exists user_profiles_email_idx on public.user_profiles (email);

-- Auto-create profile and usage rows when a Supabase Auth user registers.
create or replace function public.handle_new_auth_user()
returns trigger as $$
begin
    insert into public.user_profiles (user_id, full_name, email)
    values (
        new.id,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        coalesce(new.email, '')
    )
    on conflict (user_id) do nothing;

    insert into public.user_usage (user_id, period, plan)
    values (
        new.id,
        to_char(now() at time zone 'utc', 'YYYY-MM'),
        'free'
    )
    on conflict (user_id) do nothing;

    return new;
end;
$$ language plpgsql security definer set search_path = public;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_auth_user();
