-- Harden signup trigger against orphaned user_profiles rows.
-- Unique email conflicts on user_profiles previously aborted auth.users inserts
-- with a generic "Database error saving new user".

create or replace function public.handle_new_auth_user()
returns trigger as $$
begin
    -- Drop profile/usage rows that claim this email but are not linked to an
    -- existing auth user (orphans left behind after failed or deleted signups).
    delete from public.user_usage uu
    using public.user_profiles up
    where uu.user_id = up.user_id
      and lower(up.email) = lower(coalesce(new.email, ''))
      and up.user_id <> new.id
      and not exists (
          select 1 from auth.users au where au.id = up.user_id
      );

    delete from public.user_profiles up
    where lower(up.email) = lower(coalesce(new.email, ''))
      and up.user_id <> new.id
      and not exists (
          select 1 from auth.users au where au.id = up.user_id
      );

    insert into public.user_profiles (user_id, full_name, email)
    values (
        new.id,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        coalesce(new.email, '')
    )
    on conflict (user_id) do update
        set full_name = excluded.full_name,
            email = excluded.email,
            updated_at = now();

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
