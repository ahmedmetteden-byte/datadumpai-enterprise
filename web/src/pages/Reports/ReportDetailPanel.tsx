import { useCallback, useEffect, useMemo, useState } from 'react';
import { InlineRequestStatus } from '@/components/feedback';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { CopyButton } from '@/components/ui/CopyButton';
import { ReportMarkdown } from '@/components/ui/ReportMarkdown';
import { ExportFilenameDialog } from '@/pages/Reports/ExportFilenameDialog';
import { ExportUpgradeDialog } from '@/pages/Reports/ExportUpgradeDialog';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useRequestFeedback } from '@/context/RequestFeedbackContext';
import { UI_COPY } from '@/constants/ui';
import type { ReportDetail, ReportExportFormat } from '@/types/reports';

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

const DEFAULT_TEMPLATE_ID = 'executive_summary';
const DEFAULT_PERIOD_ID = 'custom';

export function ReportDetailPanel({
  workspaceId,
  reportId,
  onSaved,
  onRegenerated,
}: {
  workspaceId: string;
  reportId: string;
  onSaved?: (report: ReportDetail) => void;
  onRegenerated?: (report: ReportDetail) => void;
}) {
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const feedback = useRequestFeedback();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ReportExportFormat | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [exportFormatPrompt, setExportFormatPrompt] = useState<ReportExportFormat | null>(null);
  const [exportUpgradePrompt, setExportUpgradePrompt] = useState<ReportExportFormat | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await services.report.getReport(
        workspaceId,
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
  }, [workspaceId, reportId, auth]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleExport(format: ReportExportFormat, filename: string) {
    if (!report) return;
    setExporting(format);
    try {
      await feedback.run(
        async () => {
          const blob = await services.report.export(
            workspaceId,
            report.id,
            format,
            auth,
          );
          downloadBlob(blob, filename);
        },
        {
          loading: UI_COPY.requestLoading,
          success: UI_COPY.requestSuccess,
          // No static `error` override here — feedback.run() falls back to
          // err.message, which is now the backend's actual detail (e.g. a
          // plan-upgrade reason for a 403) instead of a generic message
          // that hides why the export failed.
        },
      );
    } catch {
      /* toast already shows error + retry */
    } finally {
      setExporting(null);
    }
  }

  function handleExportClick(format: ReportExportFormat) {
    if (report?.lockedExportFormats?.[format]) {
      setExportUpgradePrompt(format);
      return;
    }
    setExportFormatPrompt(format);
  }

  async function handleRegenerate() {
    if (!report) return;
    setRegenerating(true);
    setError(null);
    try {
      const created = await feedback.run(
        async () => {
          const draft = await services.report.generate(
            workspaceId,
            {
              templateId: report.templateId || DEFAULT_TEMPLATE_ID,
              periodId: report.periodId || DEFAULT_PERIOD_ID,
              instructions: report.instructions || undefined,
            },
            auth,
          );
          return services.report.save(workspaceId, draft.id, 'ready', auth);
        },
        {
          loading: UI_COPY.reportsRegenerating,
          success: UI_COPY.reportsRegenerated,
          error: UI_COPY.homeComposerGenerateError,
        },
      );
      setReport(created);
      onRegenerated?.(created);
    } catch {
      /* toast already shows error + retry */
    } finally {
      setRegenerating(false);
    }
  }

  async function handleSave() {
    if (!report) return;
    try {
      const saved = await feedback.run(
        () => services.report.save(workspaceId, report.id, 'ready', auth),
        {
          loading: UI_COPY.requestLoading,
          success: UI_COPY.reportsSaved,
          error: UI_COPY.reportsGenerateError,
        },
      );
      setReport(saved);
      onSaved?.(saved);
    } catch {
      /* toast already shows error + retry */
    }
  }

  if (loading && !report) {
    return <InlineRequestStatus kind="loading" message={UI_COPY.reportsLoading} />;
  }

  if (error && !report) {
    return (
      <InlineRequestStatus
        kind="error"
        message={error}
        onRetry={() => void reload()}
      />
    );
  }

  if (!report) return null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={report.status === 'ready' ? 'success' : 'neutral'}>
          {report.status.replace('_', ' ')}
        </Badge>
        <span className="text-small text-ink-muted">
          {report.periodName || report.reportType}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {report.status === 'draft' ? (
          <Button size="sm" onClick={() => void handleSave()}>
            {UI_COPY.reportsSaveAction}
          </Button>
        ) : null}
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="secondary"
            disabled={Boolean(exporting)}
            onClick={() => handleExportClick('docx')}
          >
            {UI_COPY.reportsExportWord}
          </Button>
          {report.lockedExportFormats?.docx ? (
            <Badge tone="warning" className="text-[10px]">
              {report.lockedExportFormats.docx}+
            </Badge>
          ) : null}
        </div>
        <Button
          size="sm"
          variant="secondary"
          disabled={Boolean(exporting)}
          onClick={() => handleExportClick('pdf')}
        >
          {UI_COPY.reportsExportPdf}
        </Button>
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="secondary"
            disabled={Boolean(exporting)}
            onClick={() => handleExportClick('pptx')}
          >
            {UI_COPY.reportsExportPptx}
          </Button>
          {report.lockedExportFormats?.pptx ? (
            <Badge tone="warning" className="text-[10px]">
              {report.lockedExportFormats.pptx}+
            </Badge>
          ) : null}
        </div>
        <Button
          size="sm"
          variant="ghost"
          disabled={regenerating}
          onClick={() => void handleRegenerate()}
        >
          {regenerating ? UI_COPY.reportsRegenerating : UI_COPY.reportsRegenerate}
        </Button>
      </div>

      <section className="rounded-xl border border-surface-border bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h3 className="text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.reportsPreview}
          </h3>
          {report.content ? <CopyButton text={report.content} /> : null}
        </div>
        <div className="max-h-[36rem] overflow-auto">
          {report.content ? (
            <ReportMarkdown content={report.content} />
          ) : (
            <p className="text-small text-ink-muted">—</p>
          )}
        </div>
      </section>

      {report.sourceDocuments && report.sourceDocuments.length > 0 ? (
        <section>
          <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.reportsSources}
          </h3>
          <ul className="space-y-1 text-small text-ink-muted">
            {report.sourceDocuments.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <ExportFilenameDialog
        format={exportFormatPrompt}
        defaultName={report.name}
        onClose={() => setExportFormatPrompt(null)}
        onConfirm={(filename) => {
          const format = exportFormatPrompt;
          setExportFormatPrompt(null);
          if (format) void handleExport(format, filename);
        }}
      />
      <ExportUpgradeDialog
        format={exportUpgradePrompt}
        requiredPlan={
          exportUpgradePrompt
            ? (report.lockedExportFormats?.[exportUpgradePrompt] ?? null)
            : null
        }
        onClose={() => setExportUpgradePrompt(null)}
      />
    </div>
  );
}
