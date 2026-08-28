import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PageRequestState } from '@/components/feedback';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useRequestFeedback } from '@/context/RequestFeedbackContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { ROUTES, UI_COPY } from '@/constants/ui';
import type { ReportDetail, ReportExportFormat } from '@/types/reports';

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const { activeWorkspaceId } = useWorkspace();
  const feedback = useRequestFeedback();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ReportExportFormat | null>(null);

  const reload = useCallback(async () => {
    if (!activeWorkspaceId || !reportId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const detail = await services.report.getReport(
        activeWorkspaceId,
        reportId,
        auth,
      );
      setReport(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.reportsLoadError);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [activeWorkspaceId, reportId, auth]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleExport(format: ReportExportFormat) {
    if (!activeWorkspaceId || !report) return;
    setExporting(format);
    try {
      await feedback.run(
        async () => {
          const blob = await services.report.export(
            activeWorkspaceId,
            report.id,
            format,
            auth,
          );
          downloadBlob(
            blob,
            `${report.name}.${format === 'pptx' ? 'pptx' : format}`,
          );
        },
        {
          loading: UI_COPY.requestLoading,
          success: UI_COPY.requestSuccess,
          // No static `error` override — feedback.run() falls back to
          // err.message, the backend's actual detail, instead of a generic
          // message that hides why the export failed.
        },
      );
    } catch {
      // Toast already shows Error + Retry via feedback.run
    } finally {
      setExporting(null);
    }
  }

  async function handleSave() {
    if (!activeWorkspaceId || !report) return;
    try {
      const saved = await feedback.run(
        () =>
          services.report.save(activeWorkspaceId, report.id, 'ready', auth),
        {
          loading: UI_COPY.requestLoading,
          success: UI_COPY.reportsSaved,
          // No static `error` override — feedback.run() falls back to
          // err.message, the backend's actual detail, instead of a generic
          // message that hides why the save failed.
        },
      );
      setReport(saved);
    } catch {
      // Toast already shows Error + Retry via feedback.run
    }
  }

  if (!activeWorkspaceId) {
    return (
      <EmptyState
        className="min-h-[50vh]"
        title={UI_COPY.reportsTitle}
        description={UI_COPY.reportsNoWorkspace}
        actionLabel={UI_COPY.workspacesTitle}
        actionHref={ROUTES.workspaces}
      />
    );
  }

  return (
    <PageRequestState
      loading={loading && !report}
      error={!report ? error : null}
      onRetry={() => void reload()}
      loadingMessage={UI_COPY.reportsLoading}
      errorTitle={UI_COPY.reportsLoadError}
    >
      {report ? (
        <div className="mx-auto max-w-3xl space-y-6 pb-16">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <Link
                to={ROUTES.reports}
                className="text-caption font-medium text-brand-600 hover:text-brand-700"
              >
                ← {UI_COPY.reportsTitle}
              </Link>
              <h1 className="mt-2 text-page-title text-ink">{report.name}</h1>
              <p className="mt-1 text-small text-ink-muted">
                {report.periodName || report.reportType} · {UI_COPY.reportsStatus}:{' '}
                <Badge tone={report.status === 'ready' ? 'success' : 'neutral'}>
                  {report.status.replace('_', ' ')}
                </Badge>
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {report.status === 'draft' ? (
                <Button size="sm" onClick={() => void handleSave()}>
                  {UI_COPY.reportsSaveAction}
                </Button>
              ) : null}
              <Button
                size="sm"
                variant="secondary"
                disabled={Boolean(exporting)}
                onClick={() => void handleExport('docx')}
              >
                {UI_COPY.reportsExportWord}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={Boolean(exporting)}
                onClick={() => void handleExport('pdf')}
              >
                {UI_COPY.reportsExportPdf}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={Boolean(exporting)}
                onClick={() => void handleExport('pptx')}
              >
                {UI_COPY.reportsExportPptx}
              </Button>
            </div>
          </div>

          <section className="rounded-xl border border-surface-border bg-white p-5 shadow-sm">
            <h2 className="text-caption uppercase tracking-wide text-ink-faint">
              {UI_COPY.reportsPreview}
            </h2>
            <pre className="mt-3 max-h-[32rem] overflow-auto whitespace-pre-wrap text-small leading-relaxed text-ink">
              {report.content || '—'}
            </pre>
          </section>

          {report.sourceDocuments && report.sourceDocuments.length > 0 ? (
            <section>
              <h2 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
                {UI_COPY.reportsSources}
              </h2>
              <ul className="space-y-1 text-small text-ink-muted">
                {report.sourceDocuments.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </PageRequestState>
  );
}
