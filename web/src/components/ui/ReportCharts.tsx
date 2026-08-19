import { cn } from '@/lib/cn';
import {
  formatChartValue,
  normalizeSeries,
  normalizeTrends,
  type ChartPoint,
  type ChartTrendPoint,
  type ReportVisualization,
} from '@/lib/reportCharts';

function StatTiles({ items }: { items: ChartPoint[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-lg border border-surface-border bg-surface-alt px-4 py-3"
        >
          <p className="text-caption text-ink-muted">{item.label}</p>
          <p className="mt-1 text-section font-semibold text-ink">
            {formatChartValue(item.value)}
          </p>
        </div>
      ))}
    </div>
  );
}

function BarList({ items }: { items: ChartPoint[] }) {
  const max = Math.max(...items.map((item) => Math.abs(item.value)), 1);
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item.label} className="space-y-1">
          <div className="flex items-center justify-between gap-3 text-small">
            <span className="text-ink-muted">{item.label}</span>
            <span className="shrink-0 font-medium text-ink">
              {formatChartValue(item.value)}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-alt">
            <div
              className="h-full rounded-r-[4px] bg-brand-500"
              style={{
                width: `${Math.max((Math.abs(item.value) / max) * 100, 3)}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ComparisonBars({ trends }: { trends: ChartTrendPoint[] }) {
  const max = Math.max(
    ...trends.flatMap((t) => [Math.abs(t.prior), Math.abs(t.current)]),
    1,
  );
  const series: { key: 'prior' | 'current'; color: string }[] = [
    { key: 'prior', color: 'bg-ink-faint' },
    { key: 'current', color: 'bg-brand-500' },
  ];

  return (
    <div>
      <div className="mb-3 flex items-center gap-4 text-caption text-ink-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-ink-faint" />
          Previous
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-brand-500" />
          Current
        </span>
      </div>
      <div className="space-y-3">
        {trends.map((trend) => (
          <div key={trend.label} className="space-y-1">
            <p className="text-small text-ink-muted">{trend.label}</p>
            {series.map(({ key, color }) => (
              <div key={key} className="flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-alt">
                  <div
                    className={cn('h-full rounded-r-[4px]', color)}
                    style={{
                      width: `${Math.max((Math.abs(trend[key]) / max) * 100, 3)}%`,
                    }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-small font-medium text-ink">
                  {formatChartValue(trend[key])}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function chartBody(viz: ReportVisualization) {
  const data = viz.data || {};

  switch (viz.type) {
    case 'KPI_CARDS': {
      const items = normalizeSeries(data.items);
      return items.length ? <StatTiles items={items} /> : null;
    }
    case 'BAR_CHART':
    case 'PIE_CHART': {
      const items = normalizeSeries(data.series);
      return items.length ? <BarList items={items} /> : null;
    }
    case 'LINE_CHART': {
      const trends = normalizeTrends(data.trends);
      return trends.length ? <ComparisonBars trends={trends} /> : null;
    }
    default:
      return null;
  }
}

// Renders the report's machine-readable chart metadata (embedded by the
// backend as a REPORT_CHARTS comment, see lib/reportCharts.ts) as real
// visuals instead of raw JSON. Covers the chart types with a simple
// label/value shape; other visualization strategies (timelines, risk
// matrices, org flows, ...) still get a clean title/description card
// rather than being hidden entirely — the full-fidelity rendering for
// those stays in the exported PDF/DOCX/PPTX.
export function ReportCharts({
  visualizations,
}: {
  visualizations: ReportVisualization[];
}) {
  if (visualizations.length === 0) return null;

  const sorted = [...visualizations].sort(
    (a, b) => (a.priority ?? 1) - (b.priority ?? 1),
  );

  return (
    <div className="space-y-4">
      {sorted.map((viz, index) => {
        const body = chartBody(viz);
        return (
          <div
            key={`${viz.title}-${index}`}
            className="rounded-xl border border-surface-border bg-white p-4 shadow-sm"
          >
            <p className="text-card text-ink">{viz.title}</p>
            {viz.description ? (
              <p
                className={cn(
                  'mt-0.5 text-small text-ink-muted',
                  body ? 'mb-3' : '',
                )}
              >
                {viz.description}
              </p>
            ) : null}
            {body}
          </div>
        );
      })}
    </div>
  );
}
