-- DataDumpAI — Supabase Storage bucket for documents, reports, and exports

insert into storage.buckets (id, name, public)
values ('datadumpai-files', 'datadumpai-files', false)
on conflict (id) do nothing;

create policy "Users read own files"
    on storage.objects for select
    using (
        bucket_id = 'datadumpai-files'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "Users upload own files"
    on storage.objects for insert
    with check (
        bucket_id = 'datadumpai-files'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "Users update own files"
    on storage.objects for update
    using (
        bucket_id = 'datadumpai-files'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "Users delete own files"
    on storage.objects for delete
    using (
        bucket_id = 'datadumpai-files'
        and auth.uid()::text = (storage.foldername(name))[1]
    );
