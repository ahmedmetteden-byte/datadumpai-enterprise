import { useCallback, useEffect, useMemo, useState } from 'react';
import { InlineRequestStatus } from '@/components/feedback';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { formatRelativeTime } from '@/lib/format';
import type { ReportDetail } from '@/types/reports';

export function ReportsListPanel({
  workspaceId,
  refreshKey,
  onSelect,
}: {
  workspaceId: string | null;
  refreshKey?: number;
  onSelect: (reportId: string) => void;
}) {
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const [reports, setReports] = useState<ReportDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!workspaceId) {
      setReports([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await services.report.listReportDetails(workspaceId, auth);
      setReports(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.reportsLoadError);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, auth]);

  useEffect(() => {
    void reload();
  }, [reload, refreshKey]);

  if (loading) {
    return <InlineRequestStatus kind="loading" message={UI_COPY.reportsLoading} />;
  }

  if (error) {
    return (
      <InlineRequestStatus
        kind="error"
        message={error}
        onRetry={() => void reload()}
      />
    );
  }

  if (reports.length === 0) {
    return (
      <EmptyState
        title={UI_COPY.reportsEmptyTitle}
        description={UI_COPY.reportsEmptyDescription}
        actionLabel={UI_COPY.homeComposerGenerate}
        actionHref={ROUTES.home}
      />
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
      {reports.map((report) => (
        <button
          key={report.id}
          type="button"
          onClick={() => onSelect(report.id)}
          className="flex flex-col rounded-xl border border-surface-border bg-white p-4 text-left transition-shadow hover:border-brand-200 hover:shadow-sm"
        >
          <div className="mb-3 flex items-center gap-2.5">
            <span
              aria-hidden
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-chip-violet-soft text-base text-chip-violet"
            >
              📊
            </span>
            <span className="text-caption font-medium uppercase tracking-wide text-ink-faint">
              {report.reportType || 'Report'}
            </span>
            <Badge
              tone={
                report.status === 'ready'
                  ? 'success'
                  : report.status === 'awaiting_review'
                    ? 'warning'
                    : 'neutral'
              }
              className="ml-auto"
            >
              {report.status.replace('_', ' ')}
            </Badge>
          </div>
          <h3 className="text-body font-semibold text-ink line-clamp-2">
            {report.name}
          </h3>
          <p className="mt-auto pt-3 text-caption text-ink-muted">
            {report.periodName ? `${report.periodName} · ` : ''}
            {formatRelativeTime(report.createdAt)}
          </p>
        </button>
      ))}
    </div>
  );
}
