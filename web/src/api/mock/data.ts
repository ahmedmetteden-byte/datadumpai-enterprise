/**
 * Empty / generic fixtures for optional offline mock mode.
 * Live product data comes from the FastAPI + Supabase APIs.
 */

import type {
  ActivityLog,
  NotificationItem,
  Project,
  ReportSummary,
  User,
} from '@/types/api';
import type {
  AiRecommendation,
  ContinueWorkingItem,
  OrgIntelligenceSignal,
  QuickAction,
  TodaysBrief,
  UniversalSearchPayload,
  WorkspaceHealthSummary,
  WorkspaceInsight,
  WorkspaceInsightsOverview,
  TeamMember,
} from '@/types/home';
import type { PublishJob } from '@/api/services/contracts';

/** Placeholder identity used only when VITE_USE_MOCK_API=true */
export const mockUser: User = {
  id: 'usr_local',
  email: 'you@example.com',
  fullName: 'You',
  emailVerified: true,
};

export const mockGreeting = 'Welcome';

/** Start with no workspaces — create them via the UI / API */
export const mockWorkspaces: Project[] = [];

export const mockNotifications: NotificationItem[] = [];

export const mockSearchSuggestions: UniversalSearchPayload = {
  recentSearches: [],
  suggestedActions: [
    { id: 'sa1', label: 'Generate a report', href: '/reports/new' },
    { id: 'sa2', label: 'Open Intelligence Studio', href: '/copilot' },
    { id: 'sa3', label: 'Upload documents', href: '/knowledge?upload=1' },
  ],
  recentReports: [],
  recentWorkspaces: [],
};

export const mockQuickActions: QuickAction[] = [
  {
    id: 'qa_upload',
    label: 'Upload documents',
    description: 'Add files to the library',
    icon: 'upload',
    href: '/knowledge?upload=1',
  },
  {
    id: 'qa_report',
    label: 'Generate report',
    description: 'Create a workspace report',
    icon: 'report',
    href: '/reports/new',
  },
  {
    id: 'qa_studio',
    label: 'Ask Intelligence Studio',
    description: 'Question your corpus',
    icon: 'copilot',
    href: '/copilot',
  },
  {
    id: 'qa_export',
    label: 'Open reports',
    description: 'Export Word, PDF, or PowerPoint',
    icon: 'export',
    href: '/reports',
  },
];

export const mockContinueWorking: ContinueWorkingItem[] = [];

export const mockReports: ReportSummary[] = [];

export const mockTodaysBrief: TodaysBrief = {
  date: new Date().toISOString(),
  greeting: 'Here is what matters today',
  items: [],
};

export const mockRecommendations: AiRecommendation[] = [];

export const mockInsights: WorkspaceInsight[] = [];

export const mockActivity: ActivityLog[] = [];

export const mockHealth: WorkspaceHealthSummary = {
  overallPercent: 100,
  status: 'ready',
  indicators: [],
  lastUpdated: new Date().toISOString(),
};

export const mockTeam: TeamMember[] = [
  {
    id: mockUser.id,
    name: mockUser.fullName,
    role: 'owner',
    title: 'Owner',
    status: 'online',
  },
];

export const mockOrgIntelligence: OrgIntelligenceSignal[] = [];

export const mockInsightsOverview: WorkspaceInsightsOverview = {
  healthPercent: 100,
  newInsightCount: 0,
  reportsAwaitingReview: 0,
  lastUpdated: new Date().toISOString(),
};

export const mockPublishJobs: PublishJob[] = [];

export function resolveMockWorkspace(workspaceId: string): Project {
  const found = mockWorkspaces.find((workspace) => workspace.id === workspaceId);
  if (found) return found;
  throw new Error('No mock workspaces — create one or use the live API.');
}
