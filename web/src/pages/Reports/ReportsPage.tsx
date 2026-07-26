import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { InlineRequestStatus } from '@/components/feedback';
import { EmptyState } from '@/components/ui/EmptyState';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { formatRelativeTime } from '@/lib/format';
import type { ReportDetail } from '@/types/reports';

export function ReportsPage() {
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const { activeWorkspaceId } = useWorkspace();
  const [reports, setReports] = useState<ReportDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!activeWorkspaceId) {
      setReports([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await services.report.listReportDetails(
        activeWorkspaceId,
        auth,
      );
      setReports(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.reportsLoadError);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [activeWorkspaceId, auth]);

  useEffect(() => {
    void reload();
  }, [reload]);

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
    <div className="space-y-8 pb-16">
      <SectionHeader
        title={UI_COPY.reportsTitle}
        description={UI_COPY.reportsSubtitle}
        action={
          <Link
            to={ROUTES.reportsNew}
            className="inline-flex h-10 items-center justify-center rounded-md bg-brand-500 px-4 text-body font-medium text-white shadow-sm hover:bg-brand-600"
          >
            {UI_COPY.reportsGenerate}
          </Link>
        }
      />

      {loading ? (
        <InlineRequestStatus
          kind="loading"
          message={UI_COPY.reportsLoading}
        />
      ) : null}

      {error ? (
        <InlineRequestStatus
          kind="error"
          message={error}
          onRetry={() => void reload()}
        />
      ) : null}

      {!loading && !error && reports.length === 0 ? (
        <EmptyState
          title={UI_COPY.reportsEmptyTitle}
          description={UI_COPY.reportsEmptyDescription}
          actionLabel={UI_COPY.reportsGenerate}
          actionHref={ROUTES.reportsNew}
        />
      ) : null}

      {!loading && !error && reports.length > 0 ? (
        <ul className="divide-y divide-surface-border overflow-hidden rounded-xl border border-surface-border bg-white shadow-sm">
          {reports.map((report) => (
            <li key={report.id}>
              <Link
                to={`${ROUTES.reports}/${report.id}`}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 hover:bg-surface-alt/50"
              >
                <div className="min-w-0">
                  <p className="truncate text-body font-medium text-ink">
                    {report.name}
                  </p>
                  <p className="mt-1 text-caption text-ink-muted">
                    {report.periodName || report.reportType || 'Report'} ·{' '}
                    {formatRelativeTime(report.createdAt)}
                  </p>
                </div>
                <Badge
                  tone={
                    report.status === 'ready'
                      ? 'success'
                      : report.status === 'awaiting_review'
                        ? 'warning'
                        : 'neutral'
                  }
                >
                  {report.status.replace('_', ' ')}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
