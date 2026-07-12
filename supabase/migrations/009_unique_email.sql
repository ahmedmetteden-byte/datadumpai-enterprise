-- Enforce unique email addresses at the database layer.

create unique index if not exists user_profiles_email_unique_idx
    on public.user_profiles (lower(email))
    where email <> '';
