-- Let uploaders tag a document with the date its content covers, so
-- report generation can filter by period on real content dates instead
-- of upload time.

alter table public.documents
    add column if not exists period_date date;

comment on column public.documents.period_date is
    'Date the document''s content covers, as tagged by the uploader at upload time. '
    'Null for documents uploaded before this field existed or left untagged — '
    'report period filtering falls back to uploaded_at in that case.';
