-- Sprint 2: workspace archive + document indexing status

alter table public.projects
    add column if not exists archived_at timestamptz;

create index if not exists projects_archived_at_idx
    on public.projects (user_id, archived_at);

alter table public.documents
    add column if not exists mime_type text not null default '',
    add column if not exists status text not null default 'uploaded',
    add column if not exists index_stage text not null default 'queued',
    add column if not exists progress_percent integer not null default 0,
    add column if not exists error_message text,
    add column if not exists indexed_at timestamptz,
    add column if not exists chunk_count integer not null default 0,
    add column if not exists title text not null default '';

create index if not exists documents_status_idx
    on public.documents (project_id, status);

comment on column public.documents.status is
    'uploaded | extracting | processing | indexed | failed';
comment on column public.documents.index_stage is
    'queued | extracting | chunking | embedding | upserting | indexed | failed';
