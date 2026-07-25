import type {
  ActivityLog,
  HealthStatus,
  IsoDateTime,
  NotificationItem,
  Project,
  ReportSummary,
  User,
  WorkspaceHealthIndicator,
} from './api';

/** Single AI insight surfaced on Home / Insights drawer. */
export interface WorkspaceInsight {
  id: string;
  title: string;
  confidence: number;
  summary: string;
  updatedAt: IsoDateTime;
  category?: string;
}

export interface TodaysBriefItem {
  id: string;
  headline: string;
  detail: string;
  priority: 'high' | 'medium' | 'low';
  href?: string;
}

export interface TodaysBrief {
  date: IsoDateTime;
  greeting: string;
  items: TodaysBriefItem[];
}

export interface AiRecommendation {
  id: string;
  title: string;
  rationale: string;
  actionLabel: string;
  actionHref: string;
  confidence: number;
}

export interface TeamMember {
  id: string;
  name: string;
  /** Permission role — map to capabilities via useWorkspacePermissions */
  role: import('./workspace').WorkspaceRole;
  /** Optional display title (e.g. Analyst) */
  title?: string;
  avatarUrl?: string;
  status: 'online' | 'away' | 'offline';
}

export interface OrgIntelligenceSignal {
  id: string;
  title: string;
  summary: string;
  trend: 'up' | 'down' | 'flat';
  valueLabel: string;
}

export interface WorkspaceHealthSummary {
  overallPercent: number;
  status: HealthStatus;
  indicators: WorkspaceHealthIndicator[];
  lastUpdated: IsoDateTime;
}

export interface ContinueWorkingItem {
  id: string;
  title: string;
  subtitle: string;
  kind: 'report' | 'document' | 'workspace' | 'draft';
  progressPercent?: number;
  updatedAt: IsoDateTime;
  href: string;
}

export interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: 'upload' | 'report' | 'copilot' | 'export' | 'search';
  href: string;
}

export interface SearchSuggestionGroup {
  id: string;
  title: string;
  items: Array<{
    id: string;
    label: string;
    meta?: string;
    href?: string;
  }>;
}

export interface UniversalSearchPayload {
  recentSearches: SearchSuggestionGroup['items'];
  suggestedActions: SearchSuggestionGroup['items'];
  recentReports: SearchSuggestionGroup['items'];
  recentWorkspaces: SearchSuggestionGroup['items'];
}

export interface WorkspaceInsightsOverview {
  healthPercent: number;
  newInsightCount: number;
  reportsAwaitingReview: number;
  lastUpdated: IsoDateTime;
}

/** Full Home page DTO — future GET /api/v1/home */
export interface HomePageData {
  user: User;
  activeWorkspace: Project;
  workspaces: Project[];
  notifications: NotificationItem[];
  unreadNotificationCount: number;
  greeting: string;
  search: UniversalSearchPayload;
  quickActions: QuickAction[];
  continueWorking: ContinueWorkingItem[];
  insightsOverview: WorkspaceInsightsOverview;
  insights: {
    brief: TodaysBrief;
    recommendations: AiRecommendation[];
    recentActivity: ActivityLog[];
    health: WorkspaceHealthSummary;
    team: TeamMember[];
    organizationalIntelligence: OrgIntelligenceSignal[];
    items: WorkspaceInsight[];
  };
  reportsAwaitingReview: ReportSummary[];
}
