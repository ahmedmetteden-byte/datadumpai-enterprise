// Mirrors services/report_chart_data.py's REPORT_CHARTS comment format —
// the backend appends `<!-- REPORT_CHARTS {json} -->` to report markdown so
// the export pipeline can re-parse chart data out of stored content. The
// web preview must strip this block before rendering as markdown (it isn't
// meant to be read as text) and use the same JSON to render a real chart.

const CHART_BLOCK_CAPTURE = /<!--\s*REPORT_?CHARTS\s*([\s\S]*?)-->/i;
const CHART_BLOCK_STRIP = /<!--\s*REPORT_?CHARTS\s*[\s\S]*?-->/gi;

export interface ReportVisualization {
  title: string;
  type: string;
  description: string;
  data: Record<string, unknown>;
  priority: number;
  decision_question?: string;
}

export interface ParsedReportContent {
  text: string;
  visualizations: ReportVisualization[];
}

export function parseReportContent(content: string): ParsedReportContent {
  const text = content.replace(CHART_BLOCK_STRIP, '').trim();

  const match = content.match(CHART_BLOCK_CAPTURE);
  if (!match) {
    return { text, visualizations: [] };
  }

  try {
    const payload = JSON.parse(match[1].trim()) as {
      visualizations?: ReportVisualization[];
    };
    return {
      text,
      visualizations: Array.isArray(payload.visualizations)
        ? payload.visualizations
        : [],
    };
  } catch {
    return { text, visualizations: [] };
  }
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface ChartTrendPoint {
  label: string;
  prior: number;
  current: number;
}

export function normalizeSeries(raw: unknown): ChartPoint[] {
  if (!Array.isArray(raw)) return [];
  const points: ChartPoint[] = [];
  for (const entry of raw) {
    if (!entry || typeof entry !== 'object') continue;
    const record = entry as Record<string, unknown>;
    const label = typeof record.label === 'string' ? record.label.trim() : '';
    const value = Number(record.value);
    if (!label || !Number.isFinite(value)) continue;
    points.push({ label, value });
  }
  return points;
}

export function normalizeTrends(raw: unknown): ChartTrendPoint[] {
  if (!Array.isArray(raw)) return [];
  const points: ChartTrendPoint[] = [];
  for (const entry of raw) {
    if (!entry || typeof entry !== 'object') continue;
    const record = entry as Record<string, unknown>;
    const label = typeof record.label === 'string' ? record.label.trim() : '';
    const prior = Number(record.prior);
    const current = Number(record.current);
    if (!label || !Number.isFinite(prior) || !Number.isFinite(current)) continue;
    points.push({ label, prior, current });
  }
  return points;
}

export function formatChartValue(value: number): string {
  // No K/M/B compaction: these values arrive with no unit attached (the
  // backend doesn't tell us whether 1558.7 means "1,558.7" or already
  // means "billions") — guessing a suffix risks stating the wrong
  // magnitude, so show the exact figure, same as the report text itself.
  return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}
