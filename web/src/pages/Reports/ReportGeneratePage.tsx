import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { InlineRequestStatus } from '@/components/feedback';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Input } from '@/components/ui/Input';
import { ReportCharts } from '@/components/ui/ReportCharts';
import { ReportMarkdown } from '@/components/ui/ReportMarkdown';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Spinner } from '@/components/ui/Spinner';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';
import { parseReportContent } from '@/lib/reportCharts';
import type {
  ReportDetail,
  ReportExportFormat,
  ReportPeriod,
  ReportTemplate,
} from '@/types/reports';

type Step =
  | 'workspace'
  | 'period'
  | 'template'
  | 'generate'
  | 'save'
  | 'export';

const STEPS: Step[] = [
  'workspace',
  'period',
  'template',
  'generate',
  'save',
  'export',
];

const STEP_LABEL: Record<Step, string> = {
  workspace: UI_COPY.reportsStepWorkspace,
  period: UI_COPY.reportsStepPeriod,
  template: UI_COPY.reportsStepTemplate,
  generate: UI_COPY.reportsStepGenerate,
  save: UI_COPY.reportsStepSave,
  export: UI_COPY.reportsStepExport,
};

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReportGeneratePage() {
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspace();
  const { workspaces } = useWorkspaceList();

  const [step, setStep] = useState<Step>('workspace');
  const [workspaceId, setWorkspaceId] = useState(activeWorkspaceId);
  const [periodId, setPeriodId] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [periods, setPeriods] = useState<ReportPeriod[]>([]);
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState<ReportExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusKind, setStatusKind] = useState<
    'loading' | 'success' | 'error' | null
  >(null);
  const [lastFailedAction, setLastFailedAction] = useState<
    (() => Promise<void>) | null
  >(null);

  useEffect(() => {
    if (!workspaceId && workspaces[0]) {
      setWorkspaceId(workspaces[0].id);
    }
  }, [workspaceId, workspaces]);

  const loadOptions = useCallback(
    async (id: string) => {
      setStatusKind('loading');
      setError(null);
      try {
        const [nextPeriods, nextTemplates] = await Promise.all([
          services.report.listPeriods(id, auth),
          services.report.listTemplates(id, auth),
        ]);
        setPeriods(nextPeriods);
        setTemplates(nextTemplates);
        setPeriodId((current) => current ?? nextPeriods[0]?.id ?? null);
        setTemplateId((current) => current ?? nextTemplates[0]?.id ?? null);
        setStatusKind('success');
        window.setTimeout(() => setStatusKind(null), 2500);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : UI_COPY.reportsLoadError;
        setError(message);
        setStatusKind('error');
        setLastFailedAction(() => () => loadOptions(id));
      }
    },
    [auth],
  );

  useEffect(() => {
    if (!workspaceId) return;
    void loadOptions(workspaceId);
  }, [workspaceId, loadOptions]);

  const stepIndex = STEPS.indexOf(step);

  function goNext() {
    const next = STEPS[stepIndex + 1];
    if (next) setStep(next);
  }

  function goBack() {
    const prev = STEPS[stepIndex - 1];
    if (prev) setStep(prev);
  }

  async function handleGenerate() {
    if (!workspaceId || !periodId || !templateId) return;
    setBusy(true);
    setError(null);
    setStatusKind('loading');
    const action = async () => {
      setActiveWorkspaceId(workspaceId);
      const created = await services.report.generate(
        workspaceId,
        {
          templateId,
          periodId,
          title: title.trim() || undefined,
        },
        auth,
      );
      setReport(created);
      setStep('save');
      setStatusKind('success');
      window.setTimeout(() => setStatusKind(null), 2500);
    };
    try {
      await action();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : UI_COPY.reportsGenerateError,
      );
      setStatusKind('error');
      setLastFailedAction(() => action);
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    if (!workspaceId || !report) return;
    setBusy(true);
    setError(null);
    setStatusKind('loading');
    const action = async () => {
      const saved = await services.report.save(
        workspaceId,
        report.id,
        'ready',
        auth,
      );
      setReport(saved);
      setStep('export');
      setStatusKind('success');
      window.setTimeout(() => setStatusKind(null), 2500);
    };
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.reportsGenerateError);
      setStatusKind('error');
      setLastFailedAction(() => action);
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(format: ReportExportFormat) {
    if (!workspaceId || !report) return;
    setExporting(format);
    setError(null);
    setStatusKind('loading');
    const action = async () => {
      const blob = await services.report.export(
        workspaceId,
        report.id,
        format,
        auth,
      );
      const ext = format === 'pptx' ? 'pptx' : format;
      downloadBlob(blob, `${report.name}.${ext}`);
      setStatusKind('success');
      window.setTimeout(() => setStatusKind(null), 2500);
    };
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.reportsExportError);
      setStatusKind('error');
      setLastFailedAction(() => action);
    } finally {
      setExporting(null);
    }
  }

  if (workspaces.length === 0) {
    return (
      <EmptyState
        className="min-h-[50vh]"
        title={UI_COPY.reportsWizardTitle}
        description={UI_COPY.reportsNoWorkspace}
        actionLabel={UI_COPY.createWorkspace}
        actionHref={ROUTES.workspaces}
      />
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-16">
      <SectionHeader
        title={UI_COPY.reportsWizardTitle}
        description={UI_COPY.reportsWizardSubtitle}
        action={
          <Link
            to={ROUTES.reports}
            className="text-small font-medium text-brand-600 hover:text-brand-700"
          >
            {UI_COPY.reportsTitle}
          </Link>
        }
      />

      <ol className="flex flex-wrap gap-2">
        {STEPS.map((item, index) => {
          const active = item === step;
          const done = index < stepIndex;
          return (
            <li
              key={item}
              className={cn(
                'rounded-full px-3 py-1 text-caption font-medium',
                active
                  ? 'bg-brand-500 text-white'
                  : done
                    ? 'bg-brand-50 text-brand-700'
                    : 'bg-surface-alt text-ink-faint',
              )}
            >
              {index + 1}. {STEP_LABEL[item]}
            </li>
          );
        })}
      </ol>

      {statusKind ? (
        <InlineRequestStatus
          kind={statusKind}
          message={
            statusKind === 'error'
              ? error
              : statusKind === 'loading'
                ? UI_COPY.reportsGeneratingEstimate
                : UI_COPY.requestSuccess
          }
          onRetry={
            statusKind === 'error' && lastFailedAction
              ? () => {
                  void lastFailedAction();
                }
              : undefined
          }
        />
      ) : null}

      <div className="rounded-xl border border-surface-border bg-white p-5 shadow-sm">
        {step === 'workspace' ? (
          <div className="space-y-4">
            <p className="text-small text-ink-muted">
              {UI_COPY.reportsSelectWorkspaceHint}
            </p>
            <ul className="space-y-2">
              {workspaces.map((workspace) => (
                <li key={workspace.id}>
                  <button
                    type="button"
                    onClick={() => setWorkspaceId(workspace.id)}
                    className={cn(
                      'w-full rounded-lg border px-4 py-3 text-left',
                      workspaceId === workspace.id
                        ? 'border-brand-500 bg-brand-50/50'
                        : 'border-surface-border hover:bg-surface-alt/50',
                    )}
                  >
                    <span className="font-medium text-ink">{workspace.name}</span>
                    <span className="mt-1 block text-caption text-ink-muted">
                      {workspace.description || '—'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {step === 'period' ? (
          <div className="space-y-4">
            <p className="text-small text-ink-muted">
              {UI_COPY.reportsSelectPeriodHint}
            </p>
            <ul className="grid gap-2 sm:grid-cols-2">
              {periods.map((period) => (
                <li key={period.id}>
                  <button
                    type="button"
                    onClick={() => setPeriodId(period.id)}
                    className={cn(
                      'w-full rounded-lg border px-4 py-3 text-left font-medium',
                      periodId === period.id
                        ? 'border-brand-500 bg-brand-50/50 text-ink'
                        : 'border-surface-border text-ink-muted hover:bg-surface-alt/50',
                    )}
                  >
                    {period.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {step === 'template' ? (
          <div className="space-y-4">
            <p className="text-small text-ink-muted">
              {UI_COPY.reportsSelectTemplateHint}
            </p>
            <div>
              <label
                htmlFor="report-title"
                className="mb-1 block text-caption font-medium text-ink-muted"
              >
                {UI_COPY.reportsOptionalTitle}
              </label>
              <Input
                id="report-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder={UI_COPY.reportsTitlePlaceholder}
              />
            </div>
            <ul className="space-y-2">
              {templates.map((template) => (
                <li key={template.id}>
                  <button
                    type="button"
                    onClick={() => setTemplateId(template.id)}
                    className={cn(
                      'w-full rounded-lg border px-4 py-3 text-left',
                      templateId === template.id
                        ? 'border-brand-500 bg-brand-50/50'
                        : 'border-surface-border hover:bg-surface-alt/50',
                    )}
                  >
                    <span className="font-medium text-ink">{template.name}</span>
                    <span className="mt-1 block text-caption text-ink-muted">
                      {template.description}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {step === 'generate' ? (
          <div className="space-y-4">
            <p className="text-small text-ink-muted">
              Ready to generate from the selected workspace, period, and
              template.
            </p>
            <dl className="grid gap-2 text-small sm:grid-cols-2">
              <div>
                <dt className="text-ink-faint">{UI_COPY.reportsStepWorkspace}</dt>
                <dd className="font-medium text-ink">
                  {workspaces.find((item) => item.id === workspaceId)?.name}
                </dd>
              </div>
              <div>
                <dt className="text-ink-faint">{UI_COPY.reportsStepPeriod}</dt>
                <dd className="font-medium text-ink">
                  {periods.find((item) => item.id === periodId)?.name}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-ink-faint">{UI_COPY.reportsStepTemplate}</dt>
                <dd className="font-medium text-ink">
                  {templates.find((item) => item.id === templateId)?.name}
                </dd>
              </div>
            </dl>
            <Button
              onClick={() => void handleGenerate()}
              disabled={busy}
              leftIcon={busy ? <Spinner size={16} /> : undefined}
            >
              {busy ? UI_COPY.reportsGenerating : UI_COPY.reportsGenerateAction}
            </Button>
          </div>
        ) : null}

        {step === 'save' && report ? (
          <div className="space-y-4">
            <h3 className="text-section text-ink">{report.name}</h3>
            <div className="max-h-80 space-y-4 overflow-auto rounded-lg bg-surface-alt/60 p-3">
              {report.content ? (
                (() => {
                  const parsed = parseReportContent(report.content);
                  return (
                    <>
                      <ReportCharts visualizations={parsed.visualizations} />
                      <ReportMarkdown content={parsed.text} />
                    </>
                  );
                })()
              ) : null}
            </div>
            <Button onClick={() => void handleSave()} disabled={busy}>
              {busy ? UI_COPY.reportsSaving : UI_COPY.reportsSaveAction}
            </Button>
          </div>
        ) : null}

        {step === 'export' && report ? (
          <div className="space-y-4">
            <p className="text-small text-success">{UI_COPY.reportsSaved}</p>
            <h3 className="text-section text-ink">{report.name}</h3>
            <p className="text-caption text-ink-faint">{UI_COPY.aiDisclaimer}</p>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={Boolean(exporting)}
                onClick={() => void handleExport('docx')}
              >
                {exporting === 'docx'
                  ? UI_COPY.reportsExporting
                  : UI_COPY.reportsExportWord}
              </Button>
              <Button
                variant="secondary"
                disabled={Boolean(exporting)}
                onClick={() => void handleExport('pdf')}
              >
                {exporting === 'pdf'
                  ? UI_COPY.reportsExporting
                  : UI_COPY.reportsExportPdf}
              </Button>
              <Button
                variant="secondary"
                disabled={Boolean(exporting)}
                onClick={() => void handleExport('pptx')}
              >
                {exporting === 'pptx'
                  ? UI_COPY.reportsExporting
                  : UI_COPY.reportsExportPptx}
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate(`${ROUTES.reports}/${report.id}`)}
              >
                {UI_COPY.reportsOpen}
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex justify-between gap-3">
        <Button
          variant="ghost"
          onClick={goBack}
          disabled={stepIndex === 0 || busy || step === 'export'}
        >
          {UI_COPY.reportsBack}
        </Button>
        {step === 'workspace' || step === 'period' || step === 'template' ? (
          <Button
            onClick={goNext}
            disabled={
              (step === 'workspace' && !workspaceId) ||
              (step === 'period' && !periodId) ||
              (step === 'template' && !templateId)
            }
          >
            {UI_COPY.reportsNext}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
